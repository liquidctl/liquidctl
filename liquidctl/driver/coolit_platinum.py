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
 - [ ] lighing control

Copyright (C) 2020–2020  Jonas Malaco
Copyright (C) 2020–2020  each contribution's author

SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import itertools

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.pmbus import compute_pec
from liquidctl.util import clamp


LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 64
_TRAILER_LENGTH = 1

_WRITE_PREFIX = 0x3F
_FEATURE_COOLING = 0x0
_CMD_GET_STATUS = 0xFF
_CMD_SET_COOLING = 0x14
_CMD_SET_LIGHTING1 = 0b100
_CMD_SET_LIGHTING2 = 0b100

_SET_COOLING_DATA_OFFSET = 3
_SET_COOLING_DATA_LENGTH = _REPORT_LENGTH - _SET_COOLING_DATA_OFFSET - _TRAILER_LENGTH
_FAN1_DATA_OFFSET = 0xB - _SET_COOLING_DATA_OFFSET
_FAN2_DATA_OFFSET = 0x11 - _SET_COOLING_DATA_OFFSET
_PUMP_DATA_OFFSET = 0x14 - _SET_COOLING_DATA_OFFSET

# TODO replace with enums and add modes
_FAN_MODE_FIXED_DUTY = 0x2
_PUMP_MODE_BALANCED = 0x1


class CoolitPlatinumDriver(UsbHidDriver):
    """liquidctl driver for Corsair Platinum and PRO XT coolers."""

    SUPPORTED_DEVICES = [
        # (0x1B1C, ??, None, 'Corsair H100i Platinum SE (experimental)', {}),
        (0x1B1C, 0x0C18, None, 'Corsair H100i Platinum (experimental)', {}),
        (0x1B1C, 0x0C17, None, 'Corsair H115i Platinum (experimental)', {}),
        (0x1B1C, 0x0C20, None, 'Corsair H100i PRO XT (experimental)', {}),
        (0x1B1C, 0x0C21, None, 'Corsair H115i PRO XT (experimental)', {}),
        # Note: unknown adjustments needed to support three fans (H150i PRO XT)
    ]

    def __init__(self, device, description, **kwargs):
        super().__init__(device, description, **kwargs)
        self._sequence = itertools.count()
        self._data = None  # only initialize in connect

    def connect(self, **kwargs):
        super().connect(**kwargs)
        ids = '{:04x}_{:04x}'.format(self.vendor_id, self.product_id)
        # FIXME uniquely identify specific units of the same model
        self._data = RuntimeStorage(key_prefixes=[ids])

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        msg = self._call(_CMD_GET_STATUS, feature=_FEATURE_COOLING)
        return [
            ('Liquid temperature', msg[8] + msg[7] / 255, '°C'),
            ('Fan 1 speed', int.from_bytes(msg[15:18], byteorder='little'), 'rpm'),
            ('Fan 2 speed', int.from_bytes(msg[22:24], byteorder='little'), 'rpm'),
            ('Pump speed', int.from_bytes(msg[29:31], byteorder='little'), 'rpm'),
            ('Firmware version', f'{msg[2] >> 4}.{msg[2] & 0xf}.{msg[3]}', ''),
        ]

    def set_fixed_speed(self, channel, duty, **kwargs):
        channel = channel.lower()
        if channel not in ['fan1', 'fan2']:
            raise ValueError("Only channels supported channels are fan1 and fan2")
        self._data.store_int(f'{channel}_duty', clamp(duty, 0, 100))
        self._send_set_cooling()

    def _call(self, command, feature=None, data=None):
        # self.device.write expects buf[0] to be the report number (=0, not used)
        buf = bytearray(_REPORT_LENGTH + 1)
        buf[1] = _WRITE_PREFIX
        buf[2] = (next(self._sequence) % 31 + 1) << 3
        if feature is not None:
            buf[2] |= feature
            buf[3] = command
            start_at = 4
        else:
            buf[2] |= command
            start_at = 3
        if data:
            buf[start_at:-1] = data
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
        self._call(_CMD_SET_COOLING, feature=_FEATURE_COOLING, data=data)
        # TODO try to assert something on the response
