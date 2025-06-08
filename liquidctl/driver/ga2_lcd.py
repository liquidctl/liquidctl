"""liquidctl drivers for Lian Li Gallahad II Vision liquid coolers.

Supported devices:

- GA II LCD

Copyright Tom Frey, Jonas Malaco, Shady Nawara and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import io
import math
import logging
import sys
import time

from PIL import Image, ImageSequence

if sys.platform == "win32":
    from winusbcdc import WinUsbPy

from liquidctl.driver.usb import PyUsbDevice, UsbHidDriver
from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver
from liquidctl.util import (
    LazyHexRepr,
    normalize_profile,
    interpolate_profile,
    clamp,
    Hue2Accessory,
    HUE2_MAX_ACCESSORIES_IN_CHANNEL,
    map_direction,
)

_LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 58
_WRITE_LENGTH = 58
_MAX_READ_ATTEMPTS = 12

_LCD_TOTAL_MEMORY = 24320
_PUMP_RPM_MAX = 3600

_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_FAN_SPEED = "Fan speed"
_STATUS_FAN_DUTY = "Fan duty"

_CRITICAL_TEMPERATURE = 59
_HWMON_CTRL_MAPPING = {"pump": 1, "fan": 2}

_LCD_SCREEN_WIDTH = 480
_LCD_SCREEN_HEIGHT = 480
_LCD_SCREEN_FPS = 24
_LCD_FRAMEBUFFER_SIZE = 921600

_LIGHTING_DIRECTIONS = {
    "default": 0x00,
    "down": 0x02,
    "up": 0x03,
}

_PUMP_LIGHTING_SPEEDS = {
    "slowest": 0x0,
    "slower": 0x1,
    "normal": 0x2,
    "faster": 0x3,
    "fastest": 0x4,
}

_PUMP_LIGHTING_MODES = {
    "bounce": 0x10,
    "color-morph": 0x0F,
    "burst": 0x0E,
    "big-bang": 0x0D,
    "static-starry-night": 0x0B,
    "colorful-starry-night": 0x0A,
    "transmit": 0x09,
    "fluctuation": 0x08,
    "ticker-tape": 0x07,
    "meteor": 0x06,
    "runway": 0x05,
    "breathing": 0x04,
    "static": 0x03,
    "rainbow-morph": 0x02,
    "rainbow": 0x01,
}

_FAN_LIGHTING_MODES = {
    "meteor": 0x00,
    "runway": 0x01,
    "breathing": 0x02,
    "static": 0x03,
    "rainbow-morph": 0x04,
    "rainbow": 0x05,
}


class GA2LCD(UsbHidDriver):
    _status = []
    _MATCHES = [
        (
            0x0416,  # Winbond Electronics Corp.
            0x7395,  # LianLi-GA_II-LCD_v1.4
            "Lian Li GA II LCD",
            {},
        )
    ]

    def initialize(self, direct_access=False, **kwargs):
        self.device.clear_enqueued_reports()
        version = self._read_firmware_version()
        # version must contain "CA_II-Vision" somewhere in middle. Yep it's a C.
        if not ("CA_II-Vision" in version):
            raise NotSupportedByDevice(
                "Device firmware version does not match expected GA_II format: " f"{version}"
            )

        self._status.append(("Firmware version", version, ""))

        self.supports_lighting = False
        self.supports_cooling = True

        return sorted(self._status)

    def _get_status_directly(self):
        self.device.clear_enqueued_reports()
        handshake = self._get_handshake()
        return [
            (_STATUS_TEMPERATURE, handshake["temperature"], "°C"),
            (_STATUS_FAN_SPEED, handshake["fan_rpm"], "rpm"),
            (_STATUS_PUMP_SPEED, handshake["pump_rpm"], "rpm"),
            (_STATUS_PUMP_DUTY, handshake["pump_rpm"] / _PUMP_RPM_MAX * 100, "%"),
        ]

    def get_status(self, direct_access=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        return self._get_status_directly()

    def set_color(self, channel, mode, colors, speed="normal", direction="default", **kwargs):
        """Set the color mode for a specific channel."""

        if channel == "pump":
            self._set_pump_lighting(mode, colors, speed, direction, **kwargs)
        elif channel == "fan":
            self._set_fan_lighting(mode, colors, speed, direction, **kwargs)
        else:
            raise NotSupportedByDriver(
                f"lighting control for {channel} is not supported by this driver"
            )

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def _set_fixed_speed_directly(self, channel, duty):
        self.set_speed_profile(channel, [(0, duty), (_CRITICAL_TEMPERATURE - 1, duty)], True)

    def set_fixed_speed(self, channel, duty, direct_access=False, **kwargs):
        """Set channel to a fixed speed duty."""

        if channel == "fan":
            self._set_fan_speed(duty)
        elif channel == "pump":
            self._set_pump_speed(duty)
        else:
            raise NotSupportedByDriver(
                f"fixed speed control for {channel} is not supported by this driver"
            )

    def set_screen(self, channel, mode, value, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def _get_a_cmd_bytes(self, cmd, data):
        # return empty list if data is empty
        if not data:
            return [
                [
                    1,  # report type
                    cmd,  # command
                    0,  # reserved
                    0,  # number_a (2 bytes)
                    0,  # number_b (2 bytes)
                    0,
                ]
            ]

        num = 0
        offset = 0

        cmd_pas = []

        while offset < len(data):
            data_len = min(len(data) - offset, 58)

            cmd_pa = [0] * 64
            cmd_pa[0] = 1
            cmd_pa[1] = cmd
            cmd_pa[2] = 0
            num_bytes = num.to_bytes(2, byteorder="big")
            cmd_pa[3] = num_bytes[0]
            cmd_pa[4] = num_bytes[1]
            cmd_pa[5] = data_len
            cmd_pa[6 : 6 + data_len] = data[offset : offset + data_len]

            dlog = f"Command: {cmd}, Num: {num}, Offset: {offset}, Data Length: {data_len}\n"
            for i in range(len(cmd_pa)):
                if i == 0:
                    dlog += f"{i:08X} "

                if i % 16 == 0:
                    dlog += "\n"

                dlog += f"{cmd_pa[i]:02X} "
            dlog += "\n"
            _LOGGER.info(dlog)

            num += 1
            offset += data_len
            cmd_pas.append(cmd_pa)

        return cmd_pas

    def _write_a_cmd(self, cmd):
        packets = self._get_a_cmd_bytes(cmd, [])
        self._write(packets[0])

    def _write_a_cmd_with_data(self, cmd, data):
        packets = self._get_a_cmd_bytes(cmd, data)
        _LOGGER.info(f"Writing command: {cmd}, data: {bytes}")
        for packet in packets:
            self._write(packet)

    def _write(self, bytes):
        self.device.write(bytes)

    def _read_a_cmd(self):
        r = self.device.read(64)
        _LOGGER.info(
            f"Read command: report type: ${r[0]:02X}, command: {r[1]:02X}, number_a: {r[3]:02X},  number_b: {r[4]:02X}, length: {r[5]:02X}"
        )

        if r[0] != 1:
            raise ValueError("Invalid response from device")

        command = r[1]
        number = int.from_bytes(r[3:5], byteorder="big")
        length = r[5]
        current_length = min(length, 58)
        packet_count = math.ceil(length / 58)
        data = r[6 : 6 + current_length]

        if packet_count > 1:
            for i in range(packet_count - 1):
                r = self.device.read(64)
                if r[0] != 1:
                    raise ValueError("Invalid response from device")
                if r[1] != command:
                    raise ValueError("Unexpected command in response")

                number = int.from_bytes(r[3:5], byteorder="big")
                if number != i + 1:
                    raise ValueError("Unexpected response number")

                length_remaining = length - len(data)
                current_length = min(length_remaining, 58)
                data += r[6 : 6 + current_length]

        dlog = ""
        for i in range(len(data)):
            if i == 0:
                dlog += f"{i:08X} "

            if i % 16 == 0:
                dlog += "\n"

            dlog += f"{data[i]:02X} "
        dlog += "\n"
        _LOGGER.info(dlog)

        return {"command": command, "number": number, "length": length, "data": data}

    def _read_firmware_version(self):
        """Read the firmware version from the device."""
        self._write_a_cmd(0x86)

        # firmware response is two packets
        p1 = self._read_a_cmd()

        # copy until first 0
        p1_data = p1["data"][: p1["data"].index(0)] if 0 in p1["data"] else p1["data"]
        string_data = bytes(p1_data)
        ascii_string_p1 = string_data.decode("ascii", errors="ignore")

        p2 = self._read_a_cmd()
        p2_data = p2["data"][: p2["data"].index(0)] if 0 in p2["data"] else p2["data"]
        string_data = bytes(p2_data)
        ascii_string_p2 = string_data.decode("ascii", errors="ignore")
        ascii_string = ascii_string_p1.strip() + ascii_string_p2.strip()

        return ascii_string

    def _get_handshake(self):
        self.device.clear_enqueued_reports()
        self._write_a_cmd(0x81)  # handshake command
        r = self._read_a_cmd()

        if r["command"] != 0x81:
            raise ValueError("Unexpected handshake response")

        if r["number"] != 0:
            raise ValueError("Unexpected handshake response number")

        if r["length"] != 0x07:
            raise ValueError("Unexpected handshake response length")

        fan_rpm = int.from_bytes(r["data"][0:2], byteorder="big")
        pump_rpm = int.from_bytes(r["data"][2:4], byteorder="big")
        temp_int = r["data"][5]
        temp_frac = r["data"][6]
        temperature = temp_int + temp_frac / 10.0

        _LOGGER.info(
            f"Handshake response: fan_rpm={fan_rpm}, pump_rpm={pump_rpm}, temperature={temperature}"
        )

        return {
            "fan_rpm": fan_rpm,
            "pump_rpm": pump_rpm,
            "temperature": temperature,
        }

    def _set_pump_speed(self, speed):
        """Set the pump speed in %."""
        # clip speed to 0-100%
        speed = max(0, min(100, speed))
        self._write_a_cmd_with_data(0x8A, [0, speed])

    def _set_fan_speed(self, speed):
        """Set the fan speed in %."""
        # clip speed to 0-100%
        speed = max(0, min(100, speed))
        self._write_a_cmd_with_data(0x8B, [0, speed])

    def _set_pump_lighting(self, mode, colors, speed, direction, **kwargs):
        req = [0] * 19

        if mode not in _PUMP_LIGHTING_MODES:
            raise ValueError(
                f"unknown pump lighting mode, should be one of: {_quoted(*_PUMP_LIGHTING_MODES)}"
            )

        if speed not in _PUMP_LIGHTING_SPEEDS:
            raise ValueError(
                f"unknown pump lighting speed, should be one of: {_quoted(*_PUMP_LIGHTING_SPEEDS)}"
            )

        if direction not in _LIGHTING_DIRECTIONS:
            raise ValueError(
                f"unknown lighting direction, should be one of: {_quoted(*_LIGHTING_DIRECTIONS)}"
            )

        pass_colors = [0] * (3 * 4)

        req[0] = 0
        req[1] = _PUMP_LIGHTING_MODES[mode]
        req[2] = 4  # brightness 0-4
        req[3] = _PUMP_LIGHTING_SPEEDS[speed]
        req[16] = _LIGHTING_DIRECTIONS[direction]
        req[17] = 0
        req[18] = 0

        colors = list(colors)
        if len(colors) > 0:
            req[4] = colors[0][0]
            req[5] = colors[0][1]
            req[6] = colors[0][2]
        if len(colors) > 1:
            req[7] = colors[1][0]
            req[8] = colors[1][1]
            req[9] = colors[1][2]
        if len(colors) > 2:
            req[10] = colors[2][0]
            req[11] = colors[2][1]
            req[12] = colors[2][2]
        if len(colors) > 3:
            req[13] = colors[3][0]
            req[14] = colors[3][1]
            req[15] = colors[3][2]

        self._write_a_cmd_with_data(0x83, req)

    def _set_fan_lighting(self, mode, colors, speed, direction, **kwargs):
        req = [8] * 20

        if mode not in _FAN_LIGHTING_MODES:
            raise ValueError(
                f"unknown fan lighting mode, should be one of: {_quoted(*_FAN_LIGHTING_MODES)}"
            )
        if speed not in _PUMP_LIGHTING_SPEEDS:
            raise ValueError(
                f"unknown fan lighting speed, should be one of: {_quoted(*_PUMP_LIGHTING_SPEEDS)}"
            )
        if direction not in _LIGHTING_DIRECTIONS:
            raise ValueError(
                f"unknown lighting direction, should be one of: {_quoted(*_LIGHTING_DIRECTIONS)}"
            )

        req[0] = _FAN_LIGHTING_MODES[mode]
        req[1] = 4
        req[2] = _PUMP_LIGHTING_SPEEDS[speed]
        req[15] = _LIGHTING_DIRECTIONS[direction]
        req[16] = 0
        req[17] = 0
        req[18] = 0
        req[19] = 24

        colors = list(colors)
        if len(colors) > 0:
            req[3] = colors[0][0]
            req[4] = colors[0][1]
            req[5] = colors[0][2]
        if len(colors) > 1:
            req[6] = colors[1][0]
            req[7] = colors[1][1]
            req[8] = colors[1][2]
        if len(colors) > 2:
            req[9] = colors[2][0]
            req[10] = colors[2][1]
            req[11] = colors[2][2]
        if len(colors) > 3:
            req[12] = colors[3][0]
            req[13] = colors[3][1]
            req[14] = colors[3][2]

        self._write_a_cmd_with_data(0x85, req)
