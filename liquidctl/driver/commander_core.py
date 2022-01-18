"""liquidctl drivers for Corsair Commander Core.

Supported devices:

- Corsair Commander Core

Copyright (C) 2021–2022  ParkerMc and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
from contextlib import contextmanager

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet, NotSupportedByDriver
from liquidctl.util import clamp, u16le_from

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 1024
_RESPONSE_LENGTH = 1024

_INTERFACE_NUMBER = 0

_FAN_COUNT = 6

_CMD_WAKE = (0x01, 0x03, 0x00, 0x02)
_CMD_SLEEP = (0x01, 0x03, 0x00, 0x01)
_CMD_GET_FIRMWARE = (0x02, 0x13)
_CMD_RESET = (0x05, 0x01, 0x00)
_CMD_SET_MODE = (0x0d, 0x00)
_CMD_READ = (0x08, 0x00)
_CMD_WRITE = (0x06, 0x00)

_MODE_LED_COUNT = (0x20,)
_MODE_GET_SPEEDS = (0x17,)
_MODE_GET_TEMPS = (0x21,)
_MODE_CONNECTED_SPEEDS = (0x1a,)
_MODE_HW_SPEED_MODE = (0x60, 0x6d)
_MODE_HW_FIXED_PERCENT = (0x61, 0x6d)

_DATA_TYPE_SPEEDS = (0x06, 0x00)
_DATA_TYPE_LED_COUNT = (0x0f, 0x00)
_DATA_TYPE_TEMPS = (0x10, 0x00)
_DATA_TYPE_CONNECTED_SPEEDS = (0x09, 0x00)
_DATA_TYPE_HW_SPEED_MODE = (0x03, 0x00)
_DATA_TYPE_HW_FIXED_PERCENT = (0x04, 0x00)


class CommanderCore(UsbHidDriver):
    """Corsair Commander Core"""

    SUPPORTED_DEVICES = [
        (0x1b1c, 0x0c1c, None, 'Corsair Commander Core (experimental)', {})
    ]

    def initialize(self, **kwargs):
        """Initialize the device and get the fan modes."""

        with self._wake_device_context():
            # Get Firmware
            res = self._send_command(_CMD_GET_FIRMWARE)
            fw_version = (res[3], res[4], res[5])

            status = [('Firmware version', '{}.{}.{}'.format(*fw_version), '')]

            # Get LEDs per fan
            res = self._read_data(_MODE_LED_COUNT, _DATA_TYPE_LED_COUNT)
            num_devices = res[0]
            led_data = res[1:1 + num_devices * 4]
            for i in range(0, num_devices):
                connected = u16le_from(led_data, offset=i * 4) == 2
                num_leds = u16le_from(led_data, offset=i * 4 + 2)
                label = 'AIO LED count' if i == 0 else f'RGB port {i} LED count'
                status += [(label, num_leds if connected else None, '')]

            # Get what fans are connected
            res = self._read_data(_MODE_CONNECTED_SPEEDS, _DATA_TYPE_CONNECTED_SPEEDS)
            num_devices = res[0]
            for i in range(0, num_devices):
                label = 'AIO port connected' if i == 0 else f'Fan port {i} connected'
                status += [(label, res[i + 1] == 0x07, '')]

            # Get what temp sensors are connected
            for i, temp in enumerate(self._get_temps()):
                connected = temp is not None
                label = 'Water temperature sensor' if i == 0 else f'Temperature sensor {i}'
                status += [(label, connected, '')]

        return status

    def get_status(self, **kwargs):
        """Get all the fan speeds and temps"""
        status = []

        with self._wake_device_context():
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
        channels = CommanderCore._parse_channels(channel)

        with self._wake_device_context():
            # Set hardware speed mode
            res = self._read_data(_MODE_HW_SPEED_MODE, _DATA_TYPE_HW_SPEED_MODE)
            device_count = res[0]

            data = bytearray(res[0:device_count + 1])
            for chan in channels:
                data[chan + 1] = 0x00  # Set the device's hardware mode to fixed percent
            self._write_data(_MODE_HW_SPEED_MODE, _DATA_TYPE_HW_SPEED_MODE, data)

            # Set speed
            res = self._read_data(_MODE_HW_FIXED_PERCENT, _DATA_TYPE_HW_FIXED_PERCENT)
            device_count = res[0]
            data = bytearray(res[0:device_count * 2 + 1])
            duty_le = int.to_bytes(clamp(duty, 0, 100), length=2, byteorder="little", signed=False)
            for chan in channels:
                i = chan * 2 + 1
                data[i: i + 2] = duty_le  # Update the device speed
            self._write_data(_MODE_HW_FIXED_PERCENT, _DATA_TYPE_HW_FIXED_PERCENT, data)

    @classmethod
    def probe(cls, handle, **kwargs):
        """Ensure we get the right interface"""

        if handle.hidinfo['interface_number'] != _INTERFACE_NUMBER:
            return

        yield from super().probe(handle, **kwargs)

    def _get_speeds(self):
        speeds = []

        res = self._read_data(_MODE_GET_SPEEDS, _DATA_TYPE_SPEEDS)

        num_speeds = res[0]
        speeds_data = res[1:1 + num_speeds * 2]
        for i in range(0, num_speeds):
            speeds.append(u16le_from(speeds_data, offset=i * 2))

        return speeds

    def _get_temps(self):
        temps = []

        res = self._read_data(_MODE_GET_TEMPS, _DATA_TYPE_TEMPS)

        num_temps = res[0]
        temp_data = res[1:1 + num_temps * 3]
        for i in range(0, num_temps):
            connected = temp_data[i * 3] == 0x00
            if connected:
                temps.append(u16le_from(temp_data, offset=i * 3 + 1) / 10)
            else:
                temps.append(None)

        return temps

    def _read_data(self, mode, data_type):
        self._send_command(_CMD_RESET)
        self._send_command(_CMD_SET_MODE, mode)
        raw_data = self._send_command(_CMD_READ)

        if tuple(raw_data[3:5]) != data_type:
            raise ExpectationNotMet('device returned incorrect data type')

        return raw_data[5:]

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

    @contextmanager
    def _wake_device_context(self):
        try:
            self._send_command(_CMD_WAKE)
            yield
        finally:
            self._send_command(_CMD_SLEEP)

    def _write_data(self, mode, data_type, data):
        self._read_data(mode, data_type)  # Will ensure we are writing the correct data type to avoid breakage

        self._send_command(_CMD_RESET)
        self._send_command(_CMD_SET_MODE, mode)

        buf = bytearray(len(data) + len(data_type) + 4)
        buf[0: 2] = int.to_bytes(len(data) + 2, length=2, byteorder="little", signed=False)
        buf[4: 4 + len(data_type)] = data_type
        buf[4 + len(data_type):] = data

        self._send_command(_CMD_WRITE, buf)

    @staticmethod
    def _parse_channels(channel):
        if channel == 'pump':
            return [0]
        elif channel == "fans":
            return range(1, _FAN_COUNT + 1)
        elif channel.startswith("fan") and channel[3:].isnumeric() and 0 < int(channel[3:]) <= _FAN_COUNT:
            return [int(channel[3:])]
        else:
            fan_names = ['fan' + str(i) for i in range(1, _FAN_COUNT + 1)]
            fan_names_part = '", "'.join(fan_names)
            raise ValueError(f'unknown channel, should be one of: "pump", "{fan_names_part}" or "fans"')
