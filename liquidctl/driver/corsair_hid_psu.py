"""liquidctl driver for Corsair HID PSUs.


Supported devices
-----------------

 - Corsair HXi (HX750i, HX850i, HX1000i and HX1200i)
 - Corsair RMi (RM650i, RM750i, RM850i and RM1000i)


Supported features
------------------

 - [✓] general device monitoring
 - [✓] electrical input monitoring
 - [✓] electrical output monitoring
 - [ ] fan control
 - [ ] 12V multirail configuration


Port of corsaiRMi: incorporates or uses as reference work by notaz and realies,
under the terms of the BSD 3-Clause license.

Incorporates or uses as reference work by Sean Nelson, under the terms of the
GNU General Public License.

corsaiRMi
Copyright (c) notaz, 2016

liquidctl driver for Corsair HID PSUs
Copyright (C) 2019  Jonas Malaco
Copyright (C) 2019  each contribution's author

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

import logging

from datetime import timedelta

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.pmbus import CommandCode as CMD
from liquidctl.pmbus import WriteBit, linear_to_float


LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64
_SLAVE_ADDRESS = 0x02
_CORSAIR_READ_TOTAL_UPTIME = CMD.MFR_SPECIFIC_01
_CORSAIR_READ_UPTIME = CMD.MFR_SPECIFIC_02
_CORSAIR_READ_INPUT_POWER = CMD.MFR_SPECIFIC_30

_RAIL_12V = 0x0
_RAIL_5V = 0x1
_RAIL_3P3V = 0x2
_RAIL_NAMES = {_RAIL_12V : '+12V', _RAIL_5V : '+5V', _RAIL_3P3V : '+3.3V'}


class CorsairHidPsuDriver(UsbHidDriver):
    """liquidctl driver for Corsair HID PSUs."""

    SUPPORTED_DEVICES = [
        (0x1b1c, 0x1c05, None, 'Corsair HX750i (experimental)', {}),
        (0x1b1c, 0x1c06, None, 'Corsair HX850i (experimental)', {}),
        (0x1b1c, 0x1c07, None, 'Corsair HX1000i (experimental)', {}),
        (0x1b1c, 0x1c08, None, 'Corsair HX1200i (experimental)', {}),
        (0x1b1c, 0x1c0a, None, 'Corsair RM650i (experimental)', {}),
        (0x1b1c, 0x1c0b, None, 'Corsair RM750i (experimental)', {}),
        (0x1b1c, 0x1c0c, None, 'Corsair RM850i (experimental)', {}),
        (0x1b1c, 0x1c0d, None, 'Corsair RM1000i (experimental)', {}),
    ]

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        self._exec(WriteBit.WRITE, CMD.PAGE, [0])
        status = [
            ('Current uptime', timedelta(seconds=self._get_int(_CORSAIR_READ_UPTIME, 32)), ''),
            ('Total uptime', timedelta(seconds=self._get_int(_CORSAIR_READ_TOTAL_UPTIME, 32)), ''),
            ('Temperature 1', self._get_float(CMD.READ_TEMPERATURE_1), '°C'),
            ('Temperature 2', self._get_float(CMD.READ_TEMPERATURE_2), '°C'),
            ('Fan speed', self._get_float(CMD.READ_FAN_SPEED_1), 'rpm'),
            ('Input voltage', self._get_float(CMD.READ_VIN), 'V'),
            ('Total power', self._get_float(_CORSAIR_READ_INPUT_POWER), 'W')
        ]
        for rail in [_RAIL_12V, _RAIL_5V, _RAIL_3P3V]:
            key_prefix = '{} output'.format(_RAIL_NAMES[rail])
            self._exec(WriteBit.WRITE, CMD.PAGE, [rail])
            self._read()
            status.append(('{} voltage'.format(key_prefix), self._get_float(CMD.READ_VOUT), 'V'))
            status.append(('{} current'.format(key_prefix), self._get_float(CMD.READ_IOUT), 'A'))
            status.append(('{} power'.format(key_prefix), self._get_float(CMD.READ_POUT), 'W'))
        self._exec(WriteBit.WRITE, CMD.PAGE, [0])
        self.device.release()
        return status

    def _write(self, data):
        padding = [0x0]*(_WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        self.device.write(data + padding)

    def _read(self):
        msg = self.device.read(_READ_LENGTH)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
        return msg

    def _exec(self, writebit, command, data=None):
        if not writebit in WriteBit:
            raise ValueError('Unknown value bit: {}'.format(writebit))
        if not command in CMD:
            raise ValueError('Unknown command code: {}'.format(command))
        self._write([_SLAVE_ADDRESS | writebit, command] + (data or []))
        return self._read()

    def _get_int(self, command, size):
        """Get `size`-bit integer value and `command`."""
        msg = self._exec(WriteBit.WRITE, command)
        if (size >> 3) % 8:
            raise NotImplementedError('Cannot read partial bytes yet')
        ubound = 2 + (size >> 3)
        return int.from_bytes(msg[2:ubound], byteorder='little')

    def _get_float(self, command):
        """Get float value with `command`."""
        return linear_to_float(self._exec(WriteBit.READ, command)[2:])
