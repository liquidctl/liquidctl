"""liquidctl drivers for Lian Li Gallahad II Vision liquid coolers.

Supported devices:

- GA II LCD

Copyright Tom Frey, Jonas Malaco, Shady Nawara, Ilia Khubuluri and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import io
import math
import logging
import sys
import time

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

_PUMP_RPM_MAX = 3600
_FAN_RPM_MAX = 2520

_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_FAN_SPEED = "Fan speed"
_STATUS_FAN_DUTY = "Fan duty"

_CRITICAL_TEMPERATURE = 59

_LIGHTING_DIRECTIONS = {
    "forward": 0x00,
    "backward": 0x01,
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

_SPEED_CHANNELS = {
    "fan": 0x8B,
    "pump": 0x8A,
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
            raise NotSupportedByDriver(
                "Device firmware version does not match expected GA_II format: " f"{version}"
            )

        self._status.append(("Firmware version", version, ""))

        self.supports_lighting = False
        self.supports_cooling = True

        return sorted(self._status)

    def get_status(self, direct_access=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        self.device.clear_enqueued_reports()
        handshake = self._get_handshake()
        return [
            (_STATUS_TEMPERATURE, handshake["temperature"], "°C"),
            (_STATUS_FAN_SPEED, handshake["fan_rpm"], "rpm"),
            (_STATUS_FAN_DUTY, min(handshake["fan_rpm"] / _FAN_RPM_MAX * 100, 100), "%"),
            (_STATUS_PUMP_SPEED, handshake["pump_rpm"], "rpm"),
            (_STATUS_PUMP_DUTY, handshake["pump_rpm"] / _PUMP_RPM_MAX * 100, "%"),
        ]

    def set_color(self, channel, mode, colors, speed="normal", direction="forward", **kwargs):
        """Set the color mode for a specific channel."""

        if channel == "pump":
            self._set_pump_lighting(mode, colors, speed, direction, **kwargs)
        elif channel == "fan":
            self._set_fan_lighting(mode, colors, speed, direction, **kwargs)
        else:
            raise NotSupportedByDevice(
                f"lighting control for {channel} is not supported by this driver"
            )

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, direct_access=False, **kwargs):
        """Set channel to a fixed speed duty."""

        if channel not in _SPEED_CHANNELS:
            raise NotSupportedByDevice(
                f"fixed speed control for {channel} is not supported by this driver"
            )

        speed = max(0, min(100, duty))
        self._write_a_cmd_with_data(_SPEED_CHANNELS[channel], [0, speed])

    def set_screen(self, channel, mode, value, **kwargs):
        """Not supported by this device."""

        # This device has a screen but it appears that it does not
        # support sending images to it, instead if relies on a
        # computer software to stream H.264 video to it over USB.
        # Liquidctl does not currently support this functionality.
        raise NotSupportedByDriver()

    def _get_a_cmd_bytes(self, cmd, data):
        # return empty list if data is empty
        if not data:
            return [
                [
                    1,  # type
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

        # take chunks of data and send them in packets until all data is sent
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

            _LOGGER.debug(
                "Command: 0x%02x, PDU Number: %d, Offset: %d, Data Length: %d\n",
                cmd,
                num,
                offset,
                data_len,
            )

            num += 1
            offset += data_len
            cmd_pas.append(cmd_pa)

        return cmd_pas

    def _write_a_cmd(self, cmd):
        packets = self._get_a_cmd_bytes(cmd, [])
        self._write(packets[0])

    def _write_a_cmd_with_data(self, cmd, data):
        packets = self._get_a_cmd_bytes(cmd, data)
        _LOGGER.debug("Writing command: 0x%02x", cmd)
        for packet in packets:
            self._write(packet)

    def _write(self, bytes):
        self.device.write(bytes)

    def _read_a_cmd(self):
        r = self.device.read(64)

        if not r:
            raise ValueError("Device not responding")

        if len(r) < 6:
            raise ValueError("Unexpected response from device")

        _LOGGER.debug(
            "Read command: type: 0x%02X, command: 0x%02X, number_a: 0x%02X,  number_b: 0x%02X, length: 0x%02X",
            r[0],
            r[1],
            r[3],
            r[4],
            r[5],
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
        ascii_string = ascii_string_p1.strip() + " " + ascii_string_p2.strip()

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

        _LOGGER.debug(
            "Handshake response: fan_rpm=%d, pump_rpm=%d, temperature=%f",
            fan_rpm,
            pump_rpm,
            temperature,
        )

        return {
            "fan_rpm": fan_rpm,
            "pump_rpm": pump_rpm,
            "temperature": temperature,
        }

    def _write_colors(buffer, colors, offset, length):
        """Write variable length 3-byte RGB color arrays
        to a buffer at a specific offset."""
        buffer[offset:offset + length] = [0] * length

        if len(colors) > 0:
            buffer[offset] = colors[0][0]
            buffer[offset + 1] = colors[0][1]
            buffer[offset + 2] = colors[0][2]
        if len(colors) > 1:
            buffer[offset + 3] = colors[1][0]
            buffer[offset + 4] = colors[1][1]
            buffer[offset + 5] = colors[1][2]
        if len(colors) > 2:
            buffer[offset + 6] = colors[2][0]
            buffer[offset + 7] = colors[2][1]
            buffer[offset + 8] = colors[2][2]
        if len(colors) > 3:
            buffer[offset + 9] = colors[3][0]
            buffer[offset + 10] = colors[3][1]
            buffer[offset + 11] = colors[3][2]

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

        colors = list(colors)

        req[0] = 0
        req[1] = _PUMP_LIGHTING_MODES[mode]
        req[2] = 4  # brightness 0-4
        req[3] = _PUMP_LIGHTING_SPEEDS[speed]
        GA2LCD._write_colors(req, colors, 4, 12)
        req[16] = _LIGHTING_DIRECTIONS[direction]
        req[17] = 0
        req[18] = 0

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
        GA2LCD._write_colors(req, colors, 3, 12)
        req[15] = _LIGHTING_DIRECTIONS[direction]
        req[16] = 0
        req[17] = 0
        req[18] = 0
        req[19] = 24

        self._write_a_cmd_with_data(0x85, req)
