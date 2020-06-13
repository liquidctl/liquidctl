"""liquidctl driver for CoolIT Platinum coolers for Corsair.

Supported devices
-----------------

 - [ ] Corsair H100i Platinum SE
 - [✓] Corsair H100i Platinum
 - [✓] Corsair H115i Platinum

Supported features
------------------

 - [ ] general monitoring
 - [ ] pump speed control
 - [ ] fan speed control
 - [ ] lighing control

Copyright (C) 2020–2020  Jonas Malaco
Copyright (C) 2020–2020  each contribution's author

SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.pmbus import compute_pec


LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64
_WRITE_PREFIX = b'\x3f'


class CoolitPlatinumDriver(UsbHidDriver):
    """liquidctl driver for CoolIT Platinum coolers for Corsair."""

    SUPPORTED_DEVICES = [
        # (0x1b1c, ??, None, 'Corsair H100i Platinum SE (experimental)', {}),
        (0x1b1c, 0x0c18, None, 'Corsair H100i Platinum (experimental)', {}),
        (0x1b1c, 0x0c17, None, 'Corsair H115i Platinum (experimental)', {}),
    ]

    def initialize(self, **kwargs):
        """Initialize the device.

        Aparently not required.
        """
        pass

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        msg = self._call([0x78, 0xff])
        return [
            ('Liquid temperature', msg[7] / 256 + msg[8], '°C'),
            ('Fan 1 speed', msg[16] << 8 | msg[15], 'rpm'),
            ('Fan 2 speed', msg[23] << 8 | msg[22], 'rpm'),
            ('Pump speed', msg[30] << 8 | msg[29], 'rpm'),
            ('Firmware version', f'{msg[2] >> 4}.{msg[2] & 0xf}.{msg[3]}', '')
        ]

    def _call(self, data):
        buf = bytearray(_WRITE_PREFIX)
        buf.extend(data)
        buf.zfill(_WRITE_LENGTH)
        buf[-1] = compute_pec(buf[1:-1])
        LOGGER.debug('write %s', buf.hex())  # FIXME lazily call buf.hex()
        self.device.write(buf)

        buf = bytes(self.device.read(_READ_LENGTH))
        self.device.release()
        LOGGER.debug('received %s', buf.hex())  # FIXME lazily call buf.hex()
        return buf
