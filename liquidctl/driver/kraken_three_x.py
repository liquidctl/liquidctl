"""liquidctl driver for CoolIT Platinum coolers for Corsair.

 Supported devices
 -----------------

  - [ ] NZXT Kraken X53
  - [ ] NZXT Kraken X63
  - [✓] NZXT Kraken X73

 Supported features
 ------------------

  - [ ] general monitoring
  - [ ] pump speed control
  - [ ] lighting control

 ---

 liquidctl driver for Kraken X3 devices from NZXT.
 Copyright (C) 2020–2020  Jonas Malaco
 Copyright (C) 2020–2020  each contribution's author

 This file is part of liquidctl.

 liquidctl is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 liquidctl is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.
 """

import logging

from liquidctl.driver.usb import UsbHidDriver

LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64
_MAX_READ_ATTEMPTS = 12


class KrakenThreeX(UsbHidDriver):
    """liquidctl driver for Kraken X3 devices from NZXT."""

    SUPPORTED_DEVICES = [
        (0x1e71, 0x2007, None, 'NZXT Kraken X3 Pump (X53, X63 or X73) (experimental)', {})
    ]

    def initialize(self, **kwargs):
        """Initialize the device.

        Reports the current firmware of the device.

        Returns a list of (key, value, unit) tuples.
        """
        self.device.clear_enqueued_reports()
        # initialize (don't work currently - responds with a 0x71 0x01 message?)
        #self._write([0x70, 0x02, 0x01, 0xb8, 0x0b])
        #self._write([0x70, 0x01])

        # request static infos
        self._write([0x10, 0x01])  # firmware info
        status = []

        def parse_firm_info(msg):
            fw = '{}.{}.{}'.format(msg[0x11], msg[0x12], msg[0x13])
            status.append(('Firmware version', fw, ''))

        self._read_until({b'\x11\x01': parse_firm_info})
        self.device.release()
        return sorted(status)

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        msg = self._read()

        return [
            ('Liquid temperature', msg[15] + msg[14] / 10, '°C'),
            ('Pump speed', msg[18] << 8 | msg[17], 'rpm'),
            ('Pump duty', msg[19], '%'),
        ]

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        if channel != 'pump':
            assert False, 'kraken X3 devices only support changing pump speeds'
        if duty < 20 or duty > 100:
            assert False, f'invalid duty value: {duty}. must be between 20 and 100!'

        def parse_pump_speed(msg):
            if msg[19] == duty:
                LOGGER.debug(f'pump duty successfully changed to {msg[19]} % [{hex(msg[19])}]')
            else:
                assert False, f'pump duty did not update! currently at {msg[19]} % [{hex(msg[19])}]'

        self._write([0x72, 0x01, 0x00, 0x00] + [duty] * 40)
        self._read_until({b'\x75\x02': parse_pump_speed})
        self.device.release()

    def _read(self):
        data = self.device.read(_READ_LENGTH)
        self.device.release()
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in data))
        return data

    def _read_until(self, parsers):
        for _ in range(_MAX_READ_ATTEMPTS):
            msg = self.device.read(_READ_LENGTH)
            LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                func(msg)
            if not parsers:
                return
        assert False, f'missing messages (attempts={_MAX_READ_ATTEMPTS}, missing={len(parsers)})'

    def _write(self, data):
        padding = [0x0]*(_WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)', ' '.join(format(i, '02x') for i in data), len(padding))
        self.device.write(data + padding)