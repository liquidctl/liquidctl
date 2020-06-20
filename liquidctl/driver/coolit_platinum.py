"""liquidctl driver for Corsair Platinum and PRO XT coolers.

Supported devices
-----------------

 - Corsair H100i Platinum
 - Corsair H100i Platinum SE
 - Corsair H115i Platinum
 - Corsair H100i PRO XT
 - Corsair H115i PRO XT

Supported features
------------------

 - general monitoring
 - pump speed control
 - fan speed control
 - lighing control

Copyright (C) 2020–2020  Jonas Malaco
Copyright (C) 2020–2020  each contribution's author

SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from enum import Enum, unique

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.pmbus import compute_pec
from liquidctl.util import clamp, fraction_of_byte, u16le_from, normalize_profile


LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 64
_WRITE_PREFIX = 0x3F

_FEATURE_COOLING = 0b000
_CMD_GET_STATUS = 0xFF
_CMD_SET_COOLING = 0x14

_FEATURE_LIGHTING = None
_CMD_SET_LIGHTING1 = 0b100
_CMD_SET_LIGHTING2 = 0b101

# cooling data starts at offset 3 and ends just before the PEC byte
_SET_COOLING_DATA_LENGTH = _REPORT_LENGTH - 4
_SET_COOLING_DATA_PREFIX = [0x0, 0xFF, 0x5, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
_FAN_MODE_OFFSETS = [0x0B - 3, 0x11 - 3]
_FAN_DUTY_OFFSETS = [offset + 5 for offset in _FAN_MODE_OFFSETS]
_FAN_PROFILE_OFFSETS = [0x1E - 3, 0x2C - 3]
_FAN_OFFSETS = list(zip(_FAN_MODE_OFFSETS, _FAN_DUTY_OFFSETS, _FAN_PROFILE_OFFSETS))
_PUMP_MODE_OFFSET = 0x17 - 3
_PROFILE_LENGTH_OFFSET = 0x1D - 3
_PROFILE_LENGTH = 7
_CRITICAL_TEMPERATURE = 60


@unique
class _FanMode(Enum):
    CUSTOM_PROFILE = 0x0
    CUSTOM_PROFILE_WITH_EXTERNAL_SENSOR = 0x1
    FIXED_DUTY = 0x2
    FIXED_RPM = 0x4

    @classmethod
    def _missing_(cls, value):
        LOGGER.debug("falling back to FIXED_DUTY for _FanMode(%s)", value)
        return _FanMode.FIXED_DUTY


@unique
class _PumpMode(Enum):
    QUIET = 0x0
    BALANCED = 0x1
    EXTREME = 0x2

    @classmethod
    def _missing_(cls, value):
        LOGGER.debug("falling back to BALANCED for _PumpMode(%s)", value)
        return _PumpMode.BALANCED


def _sequence(storage):
    """Return a generator that produces valid protocol sequence numbers.

    Sequence numbers increment across successful invocations of liquidctl, but
    are not atomic.  The sequence is: 1, 2, 3... 29, 30, 31, 1, 2, 3...

    In the protocol the sequence number is usually shifted left by 3 bits, and
    a shifted sequence will look like: 8, 16, 24... 232, 240, 248, 8, 16, 24...
    """
    while True:
        seq = storage.load('sequence', of_type=int, default=0) % 31 + 1
        storage.store('sequence', seq)
        yield seq


def _prepare_profile(original):
    clamped = ((temp, clamp(duty, 0, 100)) for temp, duty in original)
    normal = normalize_profile(clamped, _CRITICAL_TEMPERATURE)
    missing = _PROFILE_LENGTH - len(normal)
    if missing < 0:
        raise ValueError(f'Too many points in profile (remove {-missing})')
    if missing > 0:
        normal += missing * [(_CRITICAL_TEMPERATURE, 100)]
    return normal


def _quoted(*names):
    return ', '.join(map(repr, names))


class CoolitPlatinumDriver(UsbHidDriver):
    """liquidctl driver for Corsair Platinum and PRO XT coolers."""

    SUPPORTED_DEVICES = [
        (0x1B1C, 0x0C18, None, 'Corsair H100i Platinum (experimental)',
            {'fan_count': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C19, None, 'Corsair H100i Platinum SE (experimental)',
            {'fan_count': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C17, None, 'Corsair H115i Platinum (experimental)',
            {'fan_count': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C20, None, 'Corsair H100i PRO XT (experimental)',
            {'fan_count': 2, 'rgb_fans': False}),
        (0x1B1C, 0x0C21, None, 'Corsair H115i PRO XT (experimental)',
            {'fan_count': 2, 'rgb_fans': False}),
    ]

    def __init__(self, device, description, fan_count, rgb_fans, **kwargs):
        super().__init__(device, description, **kwargs)
        self._component_count = 1 + fan_count * rgb_fans
        self._fan_names = [f'fan{i + 1}' for i in range(fan_count)]
        self._maxcolors = {
            ('led', 'super-fixed'): self._component_count * 8,
            ('led', 'off'): 0,
            ('sync', 'fixed'): self._component_count,
            ('sync', 'super-fixed'): 8,
            ('sync', 'off'): 0,
        }
        # the following fields are only initialized in connect()
        self._data = None
        self._sequence = None

    def connect(self, **kwargs):
        """Connect to the device."""
        super().connect(**kwargs)
        ids = f'{self.vendor_id:04x}_{self.product_id:04x}'
        self._data = RuntimeStorage(key_prefixes=[ids, self.address])
        self._sequence = _sequence(self._data)

    def initialize(self, pump_mode='balanced', **kwargs):
        """Initialize the device and set the pump mode.

        The device should be initialized every time it is powered on, including when
        the system resumes from suspending to memory.

        Valid values for `pump_mode` are 'quiet', 'balanced' and 'extreme'.
        Unconfigured fan channels may default to 100% duty.  Subsequent calls
        should leave the fan speeds unaffected.

        Returns a list of `(property, value, unit)` tuples.
        """
        self._data.store('pump_mode', _PumpMode[pump_mode.upper()].value)
        res = self._send_set_cooling()
        fw_version = (res[2] >> 4, res[2] & 0xf, res[3])
        return [('Firmware version', '%d.%d.%d' % fw_version, '')]

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        res = self._send_command(_FEATURE_COOLING, _CMD_GET_STATUS)
        assert len(self._fan_names) == 2, f'cannot yet parse with {len(self._fan_names)} fans'
        return [
            ('Liquid temperature', res[8] + res[7] / 255, '°C'),
            ('Fan 1 speed', u16le_from(res, offset=15), 'rpm'),
            ('Fan 2 speed', u16le_from(res, offset=22), 'rpm'),
            ('Pump speed', u16le_from(res, offset=29), 'rpm'),
        ]

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set fan or fans to a fixed speed duty.

        Valid channel values are 'fanN', where N >= 1 is the fan number, and
        'fan', to simultaneously configure all fans.  Unconfigured fan channels
        may default to 100% duty.
        """
        for hw_channel in self._get_hw_fan_channels(channel):
            self._data.store(f'{hw_channel}_mode', _FanMode.FIXED_DUTY.value)
            self._data.store(f'{hw_channel}_duty', duty)
        self._send_set_cooling()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set fan or fans to follow a speed duty profile.

        Valid channel values are 'fanN', where N >= 1 is the fan number, and
        'fan', to simultaneously configure all fans.  Unconfigured fan channels
        may default to 100% duty.

        Up to seven (temperature, duty) pairs can be supplied in `profile`,
        with temperatures in Celsius and duty values in percentage.  The last
        point should set the fan to 100% duty cycle, or be omitted; in the
        latter case the fan will be set to max out at 60°C.
        """
        profile = list(profile)
        for hw_channel in self._get_hw_fan_channels(channel):
            self._data.store(f'{hw_channel}_mode', _FanMode.CUSTOM_PROFILE.value)
            self._data.store(f'{hw_channel}_profile', profile)
        self._send_set_cooling()

    def set_color(self, channel, mode, colors, **kwargs):
        """Set the color of each LED.

        In reality the device does not have the concept of different channels
        or modes, but this driver provides a few for convenience.  Animations
        still require successive calls to this API.

        The 'led' channel can be used to address individual LEDs.  The only
        supported mode for this channel is 'super-fixed', and each color in
        `colors` is applied to one individual LED, successively.  This is
        closest to how the device works.

        The 'sync' channel considers that the individual LEDs are associated
        with components, and provides two distinct convenience modes: 'fixed'
        allows each component to be set to a different color, which is applied
        to all LEDs on that component; very differently, 'super-fixed' allows
        each individual LED to have a different color, but all components are
        made to repeat the same pattern.

        Both channels additionally support an 'off' mode, which is equivalent
        to setting all LEDs to off/solid black.

        `colors` should be an iterable of one or more `[red, blue, green]`
        triples, where each red/blue/green component is a value in the range
        0–255.  LEDs for which no color has been specified will default to
        off/solid black.

        The table bellow summarizes the available channels, modes, and their
        associated maximum number of colors.

        | Channel  | Mode        | LEDs         | Components   | Platinum | PRO XT |
        | -------- | ----------- | ------------ | ------------ | -------- | ------ |
        | sync/led | off         | all off      | all off      |        0 |      0 |
        | sync     | fixed       | synchronized | independent  |        3 |      1 |
        | sync     | super-fixed | independent  | synchronized |        8 |      8 |
        | led      | super-fixed | independent  | independent  |       24 |      8 |
        """
        channel, mode, colors = channel.lower(), mode.lower(), list(colors)
        maxcolors = self._check_color_args(channel, mode, colors)
        if mode == 'off':
            expanded = []
        elif (channel, mode) == ('led', 'super-fixed'):
            expanded = colors[:maxcolors]
        elif (channel, mode) == ('sync', 'fixed'):
            expanded = list(itertools.chain(*([color] * 8 for color in colors[:maxcolors])))
        elif (channel, mode) == ('sync', 'super-fixed'):
            expanded = (colors[:8] + [[0, 0, 0]] * (8 - len(colors))) * self._component_count
        else:
            assert False, 'assumed unreacheable'
        data1 = bytes(itertools.chain(*((b, g, r) for r, g, b in expanded[0:20])))
        data2 = bytes(itertools.chain(*((b, g, r) for r, g, b in expanded[20:])))
        self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING1, data=data1)
        self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING2, data=data2)

    def _check_color_args(self, channel, mode, colors):
        maxcolors = self._maxcolors.get((channel, mode))
        if maxcolors is None:
            raise ValueError('Unsupported (channel, mode), should be one of: {_quoted(*self._maxcolors)}')
        if len(colors) > maxcolors:
            LOGGER.warning('too many colors, dropping to %d', maxcolors)
        return maxcolors

    def _get_hw_fan_channels(self, channel):
        channel = channel.lower()
        if channel == 'fan':
            return self._fan_names
        if channel in self._fan_names:
            return [channel]
        raise ValueError(f'Unknown channel, should be one of: {_quoted("fan", *self._fan_names)}')

    def _send_command(self, feature, command, data=None):
        # self.device.write expects buf[0] to be the report number or 0 if not used
        buf = bytearray(_REPORT_LENGTH + 1)
        buf[1] = _WRITE_PREFIX
        buf[2] = next(self._sequence) << 3
        if feature is not None:
            buf[2] |= feature
            buf[3] = command
            start_at = 4
        else:
            buf[2] |= command
            start_at = 3
        if data:
            buf[start_at : start_at + len(data)] = data
        buf[-1] = compute_pec(buf[2:-1])
        LOGGER.debug('write %s', buf.hex())
        self.device.clear_enqueued_reports()
        self.device.write(buf)
        buf = bytes(self.device.read(_REPORT_LENGTH))
        self.device.release()
        LOGGER.debug('received %s', buf.hex())
        if compute_pec(buf[1:]):
            LOGGER.warning('response checksum does not match data')
        return buf

    def _send_set_cooling(self):
        assert len(self._fan_names) <= 2, 'cannot yet fit all fan data'
        data = bytearray(_SET_COOLING_DATA_LENGTH)
        data[0 : len(_SET_COOLING_DATA_PREFIX)] = _SET_COOLING_DATA_PREFIX
        data[_PROFILE_LENGTH_OFFSET] = _PROFILE_LENGTH
        for fan, (imode, iduty, iprofile) in zip(self._fan_names, _FAN_OFFSETS):
            mode = _FanMode(self._data.load(f'{fan}_mode', of_type=int))
            if mode is _FanMode.FIXED_DUTY:
                stored = self._data.load(f'{fan}_duty', of_type=int, default=100)
                duty = clamp(stored, 0, 100)
                data[iduty] = fraction_of_byte(percentage=duty)
                LOGGER.info('setting %s to %d%% duty cycle', fan, duty)
            elif mode is _FanMode.CUSTOM_PROFILE:
                stored = self._data.load(f'{fan}_profile', of_type=list, default=[])
                profile = _prepare_profile(stored)  # ensures correct len(profile)
                pairs = ((temp, fraction_of_byte(percentage=duty)) for temp, duty in profile)
                data[iprofile : iprofile + _PROFILE_LENGTH * 2] = itertools.chain(*pairs)
                LOGGER.info('setting %s to follow profile %r', fan, profile)
            else:
                raise ValueError(f'Unsupported fan {mode}')
            data[imode] = mode.value
        pump_mode = _PumpMode(self._data.load('pump_mode', of_type=int))
        data[_PUMP_MODE_OFFSET] = pump_mode.value
        LOGGER.info('setting pump mode to %s', pump_mode.name.lower())
        return self._send_command(_FEATURE_COOLING, _CMD_SET_COOLING, data=data)
