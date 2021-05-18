"""liquidctl drivers for Corsair Commander Core.

Supported devices:

- Corsair Commander Core


Copyright (C)2021  ParkerMc and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDriver
from liquidctl.util import u16le_from

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 1024
_RESPONSE_LENGTH = 1024

_INTERFACE_NUMBER = 0

_CMD_GET_FIRMWARE = (0x02, 0x13)
_CMD_INIT = (0x01, 0x03, 0x00, 0x02)
_CMD_RESET = (0x05, 0x01, 0x00)
_CMD_SET_MODE = (0x0d, 0x00)
_CMD_GET = (0x08, 0x00)

_MODE_DETECT_RGB = 0x20
_MODE_GET_SPEEDS = 0x17
_MODE_GET_TEMPS = 0x21


class CommanderCore(UsbHidDriver):
    """Corsair Commander Core"""

    SUPPORTED_DEVICES = [
        (0x1b1c, 0x0c1c, None, 'Corsair Commander Core (experimental)', {})
    ]

    def initialize(self, **kwargs):
        """Initialize the device and get the fan modes."""

        # INIT
        self._send_command(_CMD_INIT)

        # Get Firmware
        res = self._send_command(_CMD_GET_FIRMWARE)
        fw_version = (res[3], res[4], res[5])

        status = [('Firmware version', '{}.{}.{}'.format(*fw_version), '')]

        # Get LEDs per fan
        self._send_command(_CMD_RESET)
        self._send_command(_CMD_SET_MODE, [_MODE_DETECT_RGB])
        res = self._send_command(_CMD_GET)
        num_rgb = res[5]
        for i in range(0, num_rgb):
            connected = u16le_from(res, offset=6+i*4) == 2
            num_leds = u16le_from(res, offset=8+i*4)
            label = 'AIO LED count' if i == 0 else f'RGB port {i} LED count'
            status += [(label, num_leds if connected else None, '')]

        # Get what temp sensors are connected
        for i, temp in enumerate(self._get_temps()):
            connected = temp is not None
            label = 'Water temperature sensor' if i == 0 else f'Temperature sensor {i}'
            status += [(label, connected, '')]

        return status

    def get_status(self, **kwargs):
        """Get all the fan speeds and temps"""
        status = []

        # INIT in case it hasn't been accesses in a while
        self._send_command(_CMD_INIT)

        for i, speed in enumerate(self._get_speeds()):
            label = 'Pump speed' if i == 0 else f'Fan speed {i}'
            status += [(label, speed, 'rpm')]

        for i, temp in enumerate(self._get_temps()):
            if temp is None:
                continue
            label = 'Water temperature' if i == 0 else f'Temperature {i}'
            status += [(label, temp, '°C')]

        return status

    def set_color(self, channel, mode, colors, **kwargs):
        raise NotSupportedByDriver

    def set_speed_profile(self, channel, profile, **kwargs):
        raise NotSupportedByDriver

    def set_fixed_speed(self, channel, duty, **kwargs):
        raise NotSupportedByDriver

    @classmethod
    def probe(cls, handle, **kwargs):
        """Ensure we get the right interface"""

        if handle.hidinfo['interface_number'] != _INTERFACE_NUMBER:
            return

        yield from super().probe(handle, **kwargs)

    def _get_speeds(self):
        speeds = []

        self._send_command(_CMD_RESET)
        self._send_command(_CMD_SET_MODE, [_MODE_GET_SPEEDS])
        res = self._send_command(_CMD_GET)

        num_speeds = res[5]
        speeds_data = res[6:6 + num_speeds*2]
        for i in range(0, num_speeds):
            speeds.append(u16le_from(speeds_data, offset=i*2))

        return speeds

    def _get_temps(self):
        temps = []

        self._send_command(_CMD_RESET)
        self._send_command(_CMD_SET_MODE, [_MODE_GET_TEMPS])
        res = self._send_command(_CMD_GET)

        num_temps = res[5]
        temp_data = res[6:6 + num_temps*3]
        for i in range(0, num_temps):
            connected = temp_data[i*3] == 0x00
            if connected:
                temps.append(u16le_from(temp_data, offset=i*3+1)/10)
            else:
                temps.append(None)

        return temps

    def _send_command(self, command, data=()):
        # self.device.write expects buf[0] to be the report number or 0 if not used
        buf = bytearray(_REPORT_LENGTH + 1)

        # buf[1] when going out is always 08
        buf[1] = 0x08

        # Indexes for the buffer
        cmd_start = 2
        data_start = cmd_start + len(command)
        data_end = data_start + len(data)

        # Fill in the buffer
        buf[cmd_start:data_start] = command
        buf[data_start:data_end] = data

        self.device.clear_enqueued_reports()
        self.device.write(buf)

        buf = bytes(self.device.read(_RESPONSE_LENGTH))
        assert buf[1] == command[0], 'response does not match command'
        return buf
