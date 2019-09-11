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


LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64

_OP_WRITE = 0x02
_OP_READ = 0x03

_REG_OUT_SEL = 0x00
_REG_POW_ON = 0xd1
_REG_UPTIME = 0xd2
_REG_TEMP1 = 0x8d
_REG_TEMP2 = 0x8e
_REG_FAN_RPM = 0x90
_REG_INP_VOLT = 0x88
_REG_INP_POWR = 0xee
_REG_OUT_VOLT = 0x8b
_REG_OUT_CURR = 0x8c
_REG_OUT_POWR = 0x96

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
        status = [
            ('Current uptime', timedelta(seconds=self._get_int(_REG_UPTIME, 32)), ''),
            ('Total uptime', timedelta(seconds=self._get_int(_REG_POW_ON, 32)), ''),
            ('Temperature 1', self._get_float(_REG_TEMP1), '°C'),
            ('Temperature 2', self._get_float(_REG_TEMP1), '°C'),
            ('Fan speed', self._get_float(_REG_FAN_RPM), 'rpm'),
            ('Input voltage', self._get_float(_REG_INP_VOLT), 'V'),
            ('Total power', self._get_float(_REG_INP_POWR), 'W')
        ]
        for rail in [_RAIL_12V, _RAIL_5V, _RAIL_3P3V]:
            key_prefix = '{} output'.format(_RAIL_NAMES[rail])
            self._write(_OP_WRITE, _REG_OUT_SEL, value=rail)
            status.append(('{} voltage'.format(key_prefix), self._get_float(_REG_OUT_VOLT), 'V'))
            status.append(('{} current'.format(key_prefix), self._get_float(_REG_OUT_CURR), 'A'))
            status.append(('{} power'.format(key_prefix), self._get_float(_REG_OUT_POWR), 'W'))
        self.device.release()
        return status

    def _write(self, opcode, register, value=0):
        msg = [0x0] * _WRITE_LENGTH
        msg[0], msg[1], msg[2] = (opcode, register, value)
        LOGGER.debug('write %s', ' '.join(format(i, '02x') for i in msg))
        self.device.write(msg)

    def _read(self):
        msg = self.device.read(_READ_LENGTH)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
        return msg

    def _get_int(self, register, size, byteorder='little'):
        """Read integer with `size` bits from `register`."""
        self._write(_OP_READ, register)
        msg = self._read()
        if (size >> 3) % 8:
            raise NotImplementedError('Cannot read partial bytes yet')
        ubound = 2 + (size >> 3)
        return int.from_bytes(msg[2:ubound], byteorder=byteorder)

    def _get_float(self, register):
        """Read 2-byte minifloat from `register`.

        A custom format is used by these devices which deviates from the IEEE
        754 binary16 half float in many ways: the fraction is stored in the
        lower 11 bits, in two's-complement; the exponent is is stored in the
        upper 5 bits, also in two's-complement.[1]

             15              11                                           0
           | E | E | E | E | E | F | F | F | F | F | F | F | F | F | F | F |

        [1] Both corsaiRMi and OpenCorsairLink (OCL) implement the convertion
        between this custom format and a double, but with slight differences.
        The git histories suggest that OCL's implementation was more thoroughly
        tested and revised, and thus that was the basis for this method (see:
        convert_bytes_double as of OCL commit 99e1d72fa5a0).
        """
        short = self._get_int(register, 16, byteorder='little')
        exp = short >> 11
        fra = short & 0x7ff
        if exp > 15:
            exp = exp - 32
        if fra > 1023:
            fra = fra - 2048
        # note: unlike OpenCorsairLink we don't round the last binary digit
        return fra * 2**exp
