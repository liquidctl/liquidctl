"""liquidctl driver for Corsair Platinum and PRO XT coolers.

Supported devices
-----------------

 - [ ] Corsair H100i Platinum SE
 - [✓] Corsair H100i Platinum
 - [✓] Corsair H115i Platinum
 - [✓] Corsair H100i PRO XT
 - [✓] Corsair H115i PRO XT
 - [ ] Corsair H150i PRO XT

Supported features
------------------

 - [✓] general monitoring
 - [✓] pump speed control
 - [✓] fan speed control
 - [✓] lighing control

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
from liquidctl.util import clamp, normalize_profile


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
_FAN_MODE_PROFILE_OFFSETS = [(0x0B - 3, 0x1E - 3), (0x11 - 3, 0x2C - 3)]
_PUMP_MODE_OFFSET = 0x17 - 3

_PROFILE_LENGTH = 7
_CRITICAL_TEMPERATURE = 60


@unique
class FanMode(Enum):
    CUSTOM_PROFILE = 0x0
    CUSTOM_PROFILE_WITH_EXTERNAL_SENSOR = 0x1
    FIXED_DUTY = 0x2
    FIXED_RPM = 0x4

    @classmethod
    def _missing_(cls, value):
        LOGGER.debug("falling back to FIXED_DUTY for FanMode(%s)", value)
        return FanMode.FIXED_DUTY


@unique
class PumpMode(Enum):
    QUIET = 0x0
    BALANCED = 0x1
    EXTREME = 0x2

    @classmethod
    def _missing_(cls, value):
        LOGGER.debug("falling back to BALANCED for PumpMode(%s)", value)
        return PumpMode.BALANCED


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
    res = ((temp, clamp(duty, 0, 100)) for temp, duty in original)
    res = normalize_profile(res, _CRITICAL_TEMPERATURE)
    if len(res) < 1:
        raise ValueError('At least one point required')
    elif len(res) > _PROFILE_LENGTH:
        raise ValueError(f'Too many points ({len(res)}), only {_PROFILE_LENGTH} supported')
    missing = _PROFILE_LENGTH - len(res)
    if missing:
        LOGGER.info('filling missing %d points with (%d°C, 100%%)', missing, _CRITICAL_TEMPERATURE)
        res = res + [(_CRITICAL_TEMPERATURE, 100)] * missing
    return res


class CoolitPlatinumDriver(UsbHidDriver):
    """liquidctl driver for Corsair Platinum and PRO XT coolers."""

    SUPPORTED_DEVICES = [
        # (0x1B1C, ??, None, 'Corsair H100i Platinum SE (experimental)',
        #     {'fan_count': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C18, None, 'Corsair H100i Platinum (experimental)',
            {'fan_count': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C17, None, 'Corsair H115i Platinum (experimental)',
            {'fan_count': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C20, None, 'Corsair H100i PRO XT (experimental)',
            {'fan_count': 2, 'rgb_fans': False}),
        (0x1B1C, 0x0C21, None, 'Corsair H115i PRO XT (experimental)',
            {'fan_count': 2, 'rgb_fans': False}),
        # (0x1B1C, ??, None, 'Corsair H150i PRO XT (experimental)',
        #     {'fan_count': 3, 'rgb_fans': False}),  # check assertions
    ]

    def __init__(self, device, description, fan_count, rgb_fans, **kwargs):
        super().__init__(device, description, **kwargs)
        self._fans = [f'fan{i + 1}' for i in range(fan_count)]
        self._rgb_fans = rgb_fans
        # the following fields are only initialized in connect()
        self._data = None
        self._sequence = None

    def connect(self, **kwargs):
        super().connect(**kwargs)
        ids = '{:04x}_{:04x}'.format(self.vendor_id, self.product_id)
        # FIXME uniquely identify specific units of the same model
        self._data = RuntimeStorage(key_prefixes=[ids])
        self._sequence = _sequence(self._data)

    def initialize(self, pump_mode='balanced', **kwargs):
        """Initialize the device.

        This method should be called when the device settings have been cleared
        by power cycling or other reasons.

        The pump will be configured to use `pump_mode`.  Valid values are
        'quiet', 'balanced' and 'extreme'.  Unconfigured fan channels may
        default to 100% duty.

        Returns a list of `(property, value, unit)` tuples.
        """
        self._data.store('pump_mode', PumpMode[pump_mode.upper()].value)
        res = self._send_set_cooling()
        return [('Firmware version', f'{res[2] >> 4}.{res[2] & 0xf}.{res[3]}', '')]

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        assert len(self._fans) == 2, 'cannot handle {len(self._fans)} fans'
        res = self._send_command(_FEATURE_COOLING, _CMD_GET_STATUS)
        return [
            ('Liquid temperature', res[8] + res[7] / 255, '°C'),
            ('Fan 1 speed', int.from_bytes(res[15:17], byteorder='little'), 'rpm'),
            ('Fan 2 speed', int.from_bytes(res[22:24], byteorder='little'), 'rpm'),
            ('Pump speed', int.from_bytes(res[29:31], byteorder='little'), 'rpm'),
        ]

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty.

        Valid channel values are 'fanN', where N is the fan number (starting at
        1), and 'fan', to set all channels at once.  Unconfigured fan channels
        may default to 100% duty.
        """
        channel = channel.lower()
        duty = clamp(duty, 0, 100)
        if channel == 'fan':
            channels = self._fans
        elif channel in self._fans:
            channels = [channel]
        else:
            raise ValueError(f"Unknown channel, should be of: 'fan', {''.join(self._fans)}")
        for channel in channels:
            self._data.store(f'{channel}_mode', FanMode.FIXED_DUTY.value)
            self._data.store(f'{channel}_duty', duty)
        self._send_set_cooling()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to follow a speed duty profile.

        Valid channel values are 'fanN', where N is the fan number (starting at
        1), and 'fan', to set all channels at once.  Unconfigured fan channels
        may default to 100% duty.

        Up to 7 (temperature, duty) points can be supplied in `profile`.
        Temperatures should be in Celcius.  The last point should be set the
        duty to 100% or be omitted; in the latter case the duty will be set to
        100% at 60°C.
        """
        channel = channel.lower()
        if channel == 'fan':
            channels = self._fans
        elif channel in self._fans:
            channels = [channel]
        else:
            raise ValueError(f"Unknown channel, should be of: 'fan', {''.join(self._fans)}")
        for channel in channels:
            self._data.store(f'{channel}_mode', FanMode.CUSTOM_PROFILE.value)
            self._data.store(f'{channel}_profile', list(profile))
        self._send_set_cooling()

    def set_color(self, channel, mode, colors, **kwargs):
        """Set the color for each LED.

        In reality the device does not have the concept of different channels
        or modes, but a few are implemented for convenience.

        The 'led' channel is used to address the individual LEDs.  The only
        supported mode for this channel is 'super-fixed', and each color in
        `colors` is applied to one individual LED, successively.  This is
        closest to how the device works.

        The 'sync' channel considers that the individual LEDs are associated
        with components, and provides two distinct convenience modes: 'fixed'
        allows each component to be set to a different color, which is applied
        to all LEDs on that component; very differently, 'super-fixed' allows
        each individual LED to have a different color, but all components will
        repeat the same pattern.

        The table summarizes the (pseudo) channels and modes:

        | Channel | Mode        | LEDs         | Components   | Colors, max |
        | ------- | ----------- | ------------ | ------------ | ----------- |
        | led     | super-fixed | independent  | independent  |          24 |
        | sync    | fixed       | synchronized | independent  |           3 |
        | sync    | super-fixed | independent  | synchronized |           8 |

        Note: PRO XT colors do not feature RGB fans; only one component and 8
        LEDs are available.

        Animations always require successive calls to this API.
        """
        def warn_if_extra_colors(limit):
            if len(colors) > limit:
                LOGGER.warning('too many colors for channel=%s and mode=%s, dropping to %d',
                               channel, mode, limit)

        channel = channel.lower()
        mode = mode.lower()
        colors = list(colors)
        component_count = 1 + len(self._fans) * self._rgb_fans
        led_count = 8 * component_count
        if channel == 'led':
            if mode != 'super-fixed':
                LOGGER.warning("mode name not enforced but should be 'super-fixed'")
            warn_if_extra_colors(led_count)
            colors = colors[:led_count]
        elif channel == 'sync':
            if mode == 'fixed':
                warn_if_extra_colors(component_count)
                colors = list(itertools.chain(
                    *([color] * 8 for color in colors[:component_count])
                ))
            elif mode == 'super-fixed':
                warn_if_extra_colors(8)
                colors = (colors[:8] + [[0, 0, 0]] * (8 - len(colors))) * component_count
            else:
                raise ValueError("Unknown mode, should be one of: 'fixed', 'super-fixed'")
        else:
            raise ValueError("Unknown channel, should be one of: 'led', 'sync'")
        data1 = bytearray(itertools.chain(*((b, g, r) for r, g, b in colors[0:20])))
        data2 = bytearray(itertools.chain(*((b, g, r) for r, g, b in colors[20:])))
        self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING1, data=data1)
        self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING2, data=data2)
        # TODO try to assert something specific on each response
        # TODO alternatively, try to skip reading them altogether

    def _send_command(self, feature, command, data=None):
        # self.device.write expects buf[0] to be the report number (=0, not used)
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
        # TODO check response PEC
        return buf

    def _send_set_cooling(self):
        assert len(self._fans) <= 2, 'cannot fit all fan data'
        data = bytearray(_SET_COOLING_DATA_LENGTH)
        for fan, (mode_offset, profile_offset) in zip(self._fans, _FAN_MODE_PROFILE_OFFSETS):
            mode = FanMode(self._data.load(f'{fan}_mode', of_type=int))
            data[mode_offset] = mode.value
            if mode is FanMode.FIXED_DUTY:
                duty = self._data.load(f'{fan}_duty', of_type=int, default=100)
                data[mode_offset + 5] = round(clamp(duty, 0, 100) * 2.55)
                LOGGER.info('setting %s duty to %d%%', fan, duty)
            elif mode is FanMode.CUSTOM_PROFILE:
                profile = self._data.load(f'{fan}_profile', of_type=list)
                profile = _prepare_profile(profile)
                for i, (temp, duty) in enumerate(profile):
                    data[profile_offset + i * 2] = temp
                    data[profile_offset + i * 2 + 1] = round(duty * 2.55)
                    LOGGER.info('setting %s point (%d°C, %d%%), device interpolated',
                                fan, temp, duty)
            else:
                assert False, f'unexpected {mode}'
        pump_mode = PumpMode(self._data.load('pump_mode', of_type=int))
        data[_PUMP_MODE_OFFSET] = pump_mode.value
        LOGGER.info('setting pump mode to %s', pump_mode.name.lower())
        return self._send_command(_FEATURE_COOLING, _CMD_SET_COOLING, data=data)
