"""liquidctl driver for Seasonic PSUs.


Supported devices
-----------------

 - NZXT E500 (E650 and E850 missing device ids)


Supported features
------------------

 - […] general device monitoring
 - [✓] electrical output monitoring
 - [ ] fan control
 - [ ] 12V multirail configuration


liquidctl driver for Seasonic PSUs
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
import time

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.pmbus import CommandCode as CMD
from liquidctl.pmbus import linear_to_float


LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64
_MIN_DELAY = 0.0025

_RAILS = ['+12V #1', '+12V #2', '+12V #3', '+5V', '+3.3V']


class SeasonicEDriver(UsbHidDriver):
    """liquidctl driver for Seasonic E-series PSUs."""

    SUPPORTED_DEVICES = [
        (0x7793, 0x5911, None, 'NZXT E500 (experimental)', {}),
        # (0x7793, ???, None, 'NZXT E650 (experimental)', {}),
        # (0x7793, ???, None, 'NZXT E850 (experimental)', {}),
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
        status = [
            ('Temperature', self._get_float(CMD.READ_TEMPERATURE_2), '°C'),
            ('Fan speed', self._get_float(CMD.READ_FAN_SPEED_1), 'rpm'),
        ]
        for i, name in enumerate(_RAILS):
            status.append((f'{name} output voltage', self._get_vout(i), 'V'))
            status.append((f'{name} output current', self._get_float(CMD.READ_IOUT, page=i), 'I'))
            status.append((f'{name} output power', self._get_float(CMD.READ_POUT, page=i), 'W'))
        self._get_float(CMD.MFR_SPECIFIC_44) # generate debug info for later analysis
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

    def _wait(self):
        """Give the device some time and avoid error responses.

        Not well understood but probably related to the PIC16F1455
        microcontroller.  It is possible that it isn't just used for a "dumb"
        PMBus/HID bridge, requiring time to be left for other tasks.
        """
        time.sleep(_MIN_DELAY)

    def _exec_read(self, cmd, data_len):
        self._wait()
        self._write([0xad, 0, data_len + 1, 1, 0x60, cmd])
        ret = self._read()
        assert ret[0] == 0xaa
        assert ret[1] == data_len + 1
        return ret[2:(2 + data_len)]

    def _exec_page_plus_read(self, page, cmd, data_len):
        self._wait()
        self._write([0xad, 0, data_len + 2, 4, 0x60, CMD.PAGE_PLUS_READ, 2, page, cmd])
        ret = self._read()
        assert ret[0] == 0xaa
        assert ret[1] == data_len + 2
        assert ret[2] == data_len
        return ret[3:(3 + data_len)]

    def _get_float(self, cmd, page=None):
        if page is None:
            return linear_to_float(self._exec_read(cmd, 2))
        else:
            return linear_to_float(self._exec_page_plus_read(page, cmd, 2))

    def _get_vout(self, rail):
        mode = self._exec_page_plus_read(rail, CMD.VOUT_MODE, 1)[0]
        assert mode >> 5 == 0 # assume vout_mode is always ulinear16
        vout = self._exec_page_plus_read(rail, CMD.READ_VOUT, 2)
        return linear_to_float(vout, mode & 0x1f)
