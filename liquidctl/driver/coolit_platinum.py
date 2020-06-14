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
 - [·] pump speed control
 - [·] fan speed control
 - [✓] lighing control

Copyright (C) 2020–2020  Jonas Malaco
Copyright (C) 2020–2020  each contribution's author

SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.pmbus import compute_pec
from liquidctl.util import clamp


LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 64
_WRITE_PREFIX = 0x3F
_TRAILER_LENGTH = 1

_FEATURE_COOLING = 0x0
_CMD_GET_STATUS = 0xFF
_CMD_SET_COOLING = 0x14

_FEATURE_LIGHTING = None
_CMD_SET_LIGHTING1 = 0b100
_CMD_SET_LIGHTING2 = 0b100

_SET_COOLING_DATA_OFFSET = 3
_SET_COOLING_DATA_LENGTH = _REPORT_LENGTH - _SET_COOLING_DATA_OFFSET - _TRAILER_LENGTH
_FAN1_DATA_OFFSET = 0xB - _SET_COOLING_DATA_OFFSET
_FAN2_DATA_OFFSET = 0x11 - _SET_COOLING_DATA_OFFSET
_PUMP_DATA_OFFSET = 0x17 - _SET_COOLING_DATA_OFFSET

# TODO replace with enums and add modes
_FAN_MODE_FIXED_DUTY = 0x2
_PUMP_MODE_BALANCED = 0x1


def sequence(storage):
    """Return a generator that produces valid protocol sequence numbers.

    Unstable API.

    Sequence numbers increment across successful invocations of liquidctl, but
    are not atomic.  The sequence is: 1, 2, 3... 29, 30, 31, 1, 2, 3...

    In the protocol the sequence number is usually shifted left by 3 bits, and
    a shifted sequence will look like: 8, 16, 24... 232, 240, 248, 8, 16, 24...
    """
    while True:
        seq = storage.load_int('sequence', default=0) % 31 + 1
        storage.store_int('sequence', seq)
        yield seq


class CoolitPlatinumDriver(UsbHidDriver):
    """liquidctl driver for Corsair Platinum and PRO XT coolers."""

    SUPPORTED_DEVICES = [
        # (0x1B1C, ??, None, 'Corsair H100i Platinum SE (experimental)',
        #     {'fans': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C18, None, 'Corsair H100i Platinum (experimental)',
            {'fans': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C17, None, 'Corsair H115i Platinum (experimental)',
            {'fans': 2, 'rgb_fans': True}),
        (0x1B1C, 0x0C20, None, 'Corsair H100i PRO XT (experimental)',
            {'fans': 2, 'rgb_fans': False}),
        (0x1B1C, 0x0C21, None, 'Corsair H115i PRO XT (experimental)',
            {'fans': 2, 'rgb_fans': False}),
        # (0x1B1C, ??, None, 'Corsair H150i PRO XT (experimental)',
        #     {'fans': 3, 'rgb_fans': False}),  # check assertions
    ]

    def __init__(self, device, description, fans, rgb_fans, **kwargs):
        super().__init__(device, description, **kwargs)
        self._fans = fans
        self._rgb_fans = rgb_fans
        # the following fields are only initialized in connect()
        self._data = None
        self._sequence = None

    def connect(self, **kwargs):
        super().connect(**kwargs)
        ids = '{:04x}_{:04x}'.format(self.vendor_id, self.product_id)
        # FIXME uniquely identify specific units of the same model
        self._data = RuntimeStorage(key_prefixes=[ids])
        self._sequence = sequence(self._data)

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        assert self._fans == 2, f'Cannot yet handle {self._fans} fans'
        msg = self._send_command(_FEATURE_COOLING, _CMD_GET_STATUS)
        return [
            ('Liquid temperature', msg[8] + msg[7] / 255, '°C'),
            ('Fan 1 speed', int.from_bytes(msg[15:17], byteorder='little'), 'rpm'),
            ('Fan 2 speed', int.from_bytes(msg[22:24], byteorder='little'), 'rpm'),
            ('Pump speed', int.from_bytes(msg[29:31], byteorder='little'), 'rpm'),
            ('Firmware version', f'{msg[2] >> 4}.{msg[2] & 0xf}.{msg[3]}', ''),
        ]

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty.

        Work-in-progress; currently the pump mode will unconditionally be set
        to balanced.

        Channels that remain to be configured may default to 100% duty.
        """
        assert self._fans == 2, f'Cannot yet handle {self._fans} fans'
        channel = channel.lower()
        duty = clamp(duty, 0, 100)
        if channel == 'fan':
            # TODO revisit the name of this pseudo-channel
            keys = ['fan1_duty', 'fan2_duty']
        elif channel in ['fan1', 'fan2']:
            keys = [f'{channel}_duty']
        else:
            raise ValueError("Unknown channel, should be one of: 'fan', 'fan1' or 'fan2'")
        for key in keys:
            self._data.store_int(key, duty)
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
        component_count = 1 + self._fans * self._rgb_fans
        led_count = 8 * component_count
        if channel == 'led':
            if mode != 'super-fixed':
                LOGGER.warning("mode name not enforced but should be 'super-fixed'")
            warn_if_extra_colors(led_count)
            colors = colors[:led_count]
        elif channel == 'sync':
            if mode == 'fixed':
                warn_if_extra_colors(component_count)
                colors = [[color] * 8 for color in colors[:component_count]]
            elif mode == 'super-fixed':
                warn_if_extra_colors(8)
                colors = (colors[:8] + [[0, 0, 0]] * (8 - len(colors))) * component_count
            else:
                raise ValueError("Unknown mode, should be one of: 'fixed', 'super-fixed'")
        else:
            raise ValueError("Unknown channel, should be: 'address'")
        data1 = bytearray(itertools.chain(*((b, g, r) for r, g, b in colors[0:20])))
        data2 = bytearray(itertools.chain(*((b, g, r) for r, g, b in colors[20:])))
        if len(colors) > 0:
            self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING1, data=data1)
        if len(colors) > 20:
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
        data = bytearray(_SET_COOLING_DATA_LENGTH)
        data[_FAN1_DATA_OFFSET] = _FAN_MODE_FIXED_DUTY
        fan1_duty = clamp(self._data.load_int('fan1_duty', default=100), 0, 100)
        data[_FAN1_DATA_OFFSET + 5] = int(fan1_duty * 2.55)
        data[_FAN2_DATA_OFFSET] = _FAN_MODE_FIXED_DUTY
        fan2_duty = clamp(self._data.load_int('fan2_duty', default=100), 0, 100)
        data[_FAN2_DATA_OFFSET + 5] = int(fan2_duty * 2.55)
        data[_PUMP_DATA_OFFSET] = _PUMP_MODE_BALANCED
        self._send_command(_FEATURE_COOLING, _CMD_SET_COOLING, data=data)
        # TODO try to assert something specific on the response
