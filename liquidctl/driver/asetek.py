"""USB driver for fifth generation Asetek coolers.


Supported devices
-----------------

 - [⋯] Kraken X (X31, X41 and X61)
 - [ ] Corsair Hydro (H80i GTX/v2, H100i GTX/v2, H110 GTX and H115i)
 - [ ] EVGA CLC 120, 240 and 280 (except CLC 120 CL11)


Driver features
---------------

 - [⋯] initialization
 - [⋯] connection and transaction life cycle
 - [⋯] reporting of firmware version
 - [⋯] monitoring of pump and fan speeds, and of liquid temperature
 - [⋯] control of pump and fan speeds
 - [ ] control of lighting modes and colors


Copyright (C) 2018  Jonas Malaco
Copyright (C) 2018  each contribution's author

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import itertools
import logging

import usb.util

from liquidctl.driver.base_usb import BaseUsbDriver


LOGGER = logging.getLogger(__name__)

_SPEED_CHANNELS = {  # (message type, minimum duty, maximum duty)
    'fan':   (0x12, 0, 100),  # TODO adjust min duty
    'pump':  (0x13, 0, 100),  # TODO adjust min duty
}
_READ_ENDPOINT = 0x82
_READ_LENGTH = 64  # TODO test if 32 is sufficient
_READ_TIMEOUT = 2000
_WRITE_ENDPOINT = 0x2
_WRITE_LENGTH = 32  # FIXME
_WRITE_TIMEOUT = 2000


class AsetekDriver(BaseUsbDriver):
    """USB driver for fifth generation Asetek coolers."""

    SUPPORTED_DEVICES = [
        (0x2433, 0xb200, None, 'NZXT Kraken X (X31, X41 or X61; experimental)', {}),  # FIXME differentiate from EVGA CLCs
        (0x1b1c, 0x0c02, None, 'Possibly supported device (experimental)', {}),  # Corsair Hydro H80i GT
        (0x1b1c, 0x0c03, None, 'Possibly supported device (experimental)', {}),  # Corsair Hydro H100i GTX
        (0x1b1c, 0x0c07, None, 'Possibly supported device (experimental)', {}),  # Corsair Hydro H110i GTX
        (0x1b1c, 0x0c08, None, 'Possibly supported device (experimental)', {}),  # Corsair Hydro H80i v2
        (0x1b1c, 0x0c09, None, 'Possibly supported device (experimental)', {}),  # Corsair Hydro H100i v2
        (0x1b1c, 0x0c0a, None, 'Possibly supported device (experimental)', {}),  # Corsair Hydro H115i
    ]

    def __init__(self, device, description, speed_channel_count, color_channel_count):
        """Instantiate a driver with a device handle."""
        super().__init__(device, description)

    def initialize(self):
        """Initialize the device."""
        self.device.ctrl_transfer(0x40, 0x2, 0x0002)
        usb.util.dispose_resources(self.device)

    def get_status(self):
        """Get a status report.

        Returns a list of (key, value, unit) tuples.
        """
        self._begin_transaction()
        msg = self._end_transaction_and_read()
        firmware = '{}.{}.{}'.format(msg[0x17], msg[0x18] << 8 | msg[0x19], msg[0x1a])
        return [
            ('Liquid temperature', msg[10] + msg[14]/10, '°C'),  # TODO sensible?
            ('Fan speed', msg[0] << 8 | msg[1], 'rpm'),  # TODO sensible?
            ('Pump speed', msg[8] << 8 | msg[9], 'rpm'),  # TODO sensible?
            ('Firmware version', firmware, '')  # TODO sensible?
        ]

    def set_fixed_speed(self, channel, speed):
        """Set channel to a fixed speed."""
        mtype, smin, smax = _SPEED_CHANNELS[channel]
        if speed < smin:
            speed = smin
        elif speed > smax:
            speed = smax
        LOGGER.info('setting %s PWM duty to %i%%', channel, speed)
        self._begin_transaction()
        self._write([mtype, speed])
        self._end_transaction_and_read()

    def _begin_transaction(self):
        # TODO test if this can be moved to connect()
        self.device.ctrl_transfer(0x40, 0x2, 0x0001)

    def _end_transaction_and_read(self):
        # TODO test if this is unnecessary (unless we actually want the status)
        msg = self.device.read(_READ_ENDPOINT, _READ_LENGTH, _READ_TIMEOUT)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
        usb.util.dispose_resources(self.device)
        return msg

    def _write(self, data):
        padding = [0x0]*(_WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        if self.dry_run:
            return
        self.device.write(_WRITE_ENDPOINT, data + padding, _WRITE_TIMEOUT)

