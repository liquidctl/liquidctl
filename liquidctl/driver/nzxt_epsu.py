"""liquidctl driver for NZXT E-series PSUs.

Supported devices: NZXT E500, E650 and E850.

Features:

- electrical output monitoring: complete
- general device monitoring: partial
- fan control: missing
- 12V multiple rail configuration: missing

Copyright (C) 2019–2022  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import time

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.pmbus import CommandCode as CMD
from liquidctl.pmbus import linear_to_float

_REPORT_LENGTH = 64
_MIN_DELAY = 0.0025
_ATTEMPTS = 3

_SEASONIC_READ_FIRMWARE_VERSION = CMD.MFR_SPECIFIC_FC
_RAILS = ['+12V peripherals', '+12V EPS/ATX12V', '+12V motherboard/PCI-e', '+5V combined', '+3.3V combined']


class NzxtEPsu(UsbHidDriver):
    """NZXT E-series power supply unit."""

    SUPPORTED_DEVICES = [
        (0x7793, 0x5911, None, 'NZXT E500', {}),
        (0x7793, 0x5912, None, 'NZXT E650', {}),
        (0x7793, 0x2500, None, 'NZXT E850', {}),
    ]

    def initialize(self, **kwargs):
        """Initialize the device.

        Apparently not required.
        """

        pass

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        self.device.clear_enqueued_reports()
        fw_human, fw_cam = self._get_fw_versions()
        status = [
            ('Temperature', self._get_float(CMD.READ_TEMPERATURE_2), '°C'),
            ('Fan speed', self._get_float(CMD.READ_FAN_SPEED_1), 'rpm'),
            ('Firmware version', f'{fw_human}/{fw_cam}', ''),
        ]
        for i, name in enumerate(_RAILS):
            status.append((f'{name} output voltage', self._get_vout(i), 'V'))
            status.append((f'{name} output current', self._get_float(CMD.READ_IOUT, page=i), 'A'))
            status.append((f'{name} output power', self._get_float(CMD.READ_POUT, page=i), 'W'))
        return status

    def set_color(self, channel, mode, colors, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def _write(self, data):
        assert len(data) <= _REPORT_LENGTH
        packet = bytearray(1 + _REPORT_LENGTH)
        packet[1: 1 + len(data)] = data  # device doesn't use numbered reports
        self.device.write(packet)

    def _read(self):
        return self.device.read(_REPORT_LENGTH)

    def _wait(self):
        """Give the device some time and avoid error responses.

        Not well understood but probably related to the PIC16F1455
        microcontroller.  It is possible that it isn't just used for a "dumb"
        PMBus/HID bridge, requiring time to be left for other tasks.
        """

        time.sleep(_MIN_DELAY)

    def _exec_read(self, cmd, data_len):
        data = None
        msg = [0xad, 0, data_len + 1, 1, 0x60, cmd]
        for _ in range(_ATTEMPTS):
            self._wait()
            self._write(msg)
            res = self._read()
            # see comment in _exec_page_plus_read, but res[1] == 0xff has not
            # been seen in the wild yet
            # TODO replace with PEC byte check
            if res[0] == 0xaa and res[1] == data_len + 1:
                data = res
                break
        assert data, f'invalid response (attempts={_ATTEMPTS})'
        return data[2:(2 + data_len)]

    def _exec_page_plus_read(self, page, cmd, data_len):
        data = None
        msg = [0xad, 0, data_len + 2, 4, 0x60, CMD.PAGE_PLUS_READ, 2, page, cmd]
        for _ in range(_ATTEMPTS):
            self._wait()
            self._write(msg)
            res = self._read()
            # in captured traffic res[2] == 0xff appears to signal invalid data
            # (possibly due to the device being busy, see PMBus spec)
            # TODO replace with PEC byte check
            if res[0] == 0xaa and res[1] == data_len + 2 and res[2] == data_len:
                data = res
                break
        assert data, f'invalid response (attempts={_ATTEMPTS})'
        return data[3:(3 + data_len)]

    def _get_float(self, cmd, page=None):
        if page is None:
            return linear_to_float(self._exec_read(cmd, 2))
        else:
            return linear_to_float(self._exec_page_plus_read(page, cmd, 2))

    def _get_vout(self, rail):
        mode = self._exec_page_plus_read(rail, CMD.VOUT_MODE, 1)[0]
        assert mode >> 5 == 0  # assume vout_mode is always ulinear16
        vout = self._exec_page_plus_read(rail, CMD.READ_VOUT, 2)
        return linear_to_float(vout, mode & 0x1f)

    def _get_fw_versions(self):
        minor, major = self._exec_read(_SEASONIC_READ_FIRMWARE_VERSION, 2)
        human_ver = f'{bytes([major]).decode()}{minor:03}'
        ascam_ver = int.from_bytes(bytes.fromhex(human_ver), byteorder='big')
        return (human_ver, ascam_ver)


# deprecated aliases
SeasonicEDriver = NzxtEPsu
