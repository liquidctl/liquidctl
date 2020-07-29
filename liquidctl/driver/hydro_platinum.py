"""liquidctl drivers for Corsair Hydro Platinum and PRO XT liquid coolers.

Supported devices:

- Corsair H100i Platinum
- Corsair H100i Platinum SE
- Corsair H115i Platinum
- Corsair H100i PRO XT
- Corsair H115i PRO XT

Copyright (C) 2020–2020  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging
import re

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


class HydroPlatinum(UsbHidDriver):
    """Corsair Hydro Platinum or PRO XT liquid cooler."""

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
        self._led_count = 16 + 4 * fan_count * rgb_fans
        self._fan_names = [f'fan{i + 1}' for i in range(fan_count)]
        self._mincolors = {
            ('led', 'super-fixed'): 1,
            ('led', 'fixed'): 1,
            ('led', 'off'): 0,
        }
        # the following fields are only initialized in connect()
        self._data = None
        self._sequence = None

    def connect(self, **kwargs):
        """Connect to the device."""
        super().connect(**kwargs)
        ids = f'vid{self.vendor_id:04x}_pid{self.product_id:04x}'
        # must use the HID path because there is no serial number; however,
        # these can be quite long on Windows and macOS, so only take the
        # numbers, since they are likely the only parts that vary between two
        # devices of the same model
        loc = 'loc' + '_'.join(re.findall(r'\d+', self.address))
        self._data = RuntimeStorage(key_prefixes=[ids, loc])
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

    def set_color(self, channel, mode, colors, unsafe=None, **kwargs):
        """Set the color of each LED.

        In reality the device does not have the concept of different channels
        or modes, but this driver provides a few for convenience.  Animations
        still require successive calls to this API.

        The 'led' channel can be used to address individual LEDs, and supports
        the 'super-fixed', 'fixed' and 'off' modes.

        In 'super-fixed' mode, each color in `colors` is applied to one
        individual LED, successively.  LEDs for which no color has been
        specified default to off/solid black.  This is closest to how the
        device works.

        In 'fixed' mode, all LEDs are set to the first color taken from
        `colors`.  The `off` mode is equivalent to calling this function with
        'fixed' and a single solid black color in `colors`.

        The `colors` argument should be an iterable of one or more `[red, blue,
        green]` triples, where each red/blue/green component is a value in the
        range 0–255.

        The table bellow summarizes the available channels, modes, and their
        associated maximum number of colors for each device family.

        | Channel  | Mode        | LEDs         | Platinum | PRO XT |
        | -------- | ----------- | ------------ | -------- | ------ |
        | led      | off         | synchronized |        0 |      0 |
        | led      | fixed       | synchronized |        1 |      1 |
        | led      | super-fixed | independent  |       24 |     16 |

        Note: lighting control of PRO XT devices is experimental and requires
        the `pro_xt_lighting` constant to be supplied in the `unsafe` iterable.
        """

        if 'PRO XT' in self.description and not (unsafe and 'pro_xt_lighting' in unsafe):
            LOGGER.warning('Lighting control of PRO XT devices is experimental and only enabled with the `pro_xt_lighting` unsafe flag')

        channel, mode, colors = channel.lower(), mode.lower(), list(colors)
        self._check_color_args(channel, mode, colors)
        if mode == 'off':
            expanded = []
        elif (channel, mode) == ('led', 'super-fixed'):
            expanded = colors[:self._led_count]
        elif (channel, mode) == ('led', 'fixed'):
            expanded = list(itertools.chain(*([color] * self._led_count for color in colors[:1])))
        else:
            assert False, 'assumed unreacheable'
        data1 = bytes(itertools.chain(*((b, g, r) for r, g, b in expanded[0:20])))
        data2 = bytes(itertools.chain(*((b, g, r) for r, g, b in expanded[20:])))
        self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING1, data=data1)
        self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING2, data=data2)

    def _check_color_args(self, channel, mode, colors):
        try:
            mincolors = self._mincolors[(channel, mode)]
        except KeyError:
            raise ValueError(f'Unsupported (channel, mode) pair, should be one of: {_quoted(*self._mincolors)}')
        if len(colors) < mincolors:
            raise ValueError(f'At least {mincolors} required for {_quoted((channel, mode))}')
        if len(colors) > mincolors:
            LOGGER.warning('too many colors, dropping to %d', mincolors)
        return mincolors

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
        self.device.clear_enqueued_reports()
        self.device.write(buf)
        buf = bytes(self.device.read(_REPORT_LENGTH))
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
