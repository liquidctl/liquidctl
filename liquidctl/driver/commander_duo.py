"""liquidctl driver for Corsair Commander DUO.

Supported devices:

- Corsair Commander DUO

Copyright liquidctl contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import time
from contextlib import contextmanager

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet, NotSupportedByDriver, Timeout
from liquidctl.util import clamp, u16le_from

_REPORT_LENGTH = 96
_RESPONSE_LENGTH = 96

_INTERFACE_NUMBER = 0

_CMD_WAKE = (0x01, 0x03, 0x00, 0x02)
_CMD_SLEEP = (0x01, 0x03, 0x00, 0x01)
_CMD_GET_FIRMWARE = (0x02, 0x13)
_CMD_CLOSE_ENDPOINT = (0x05, 0x01, 0x00)
_CMD_CLOSE_WRITE_ENDPOINT = (0x05, 0x01, 0x01)
_CMD_OPEN_ENDPOINT = (0x0D, 0x00)
_CMD_OPEN_WRITE_ENDPOINT = (0x0D, 0x01)
_CMD_OPEN_COLOR_ENDPOINT = (0x0D, 0x00)
_CMD_READ_INITIAL = (0x08, 0x00, 0x01)
_CMD_READ_MORE = (0x08, 0x00, 0x02)
_CMD_READ_FINAL = (0x08, 0x00, 0x03)
_CMD_READ_METADATA = (0x09, 0x01)
_CMD_WRITE_ENDPOINT = (0x06, 0x01)
_CMD_WRITE_COLOR = (0x06, 0x00)
_CMD_WRITE_COLOR_MORE = (0x07, 0x00)
_CMD_RESET_LED_POWER = (0x15, 0x01)

_MODE_LED_COUNT = (0x20,)
_MODE_GET_SPEEDS = (0x17,)
_MODE_GET_TEMPS = (0x21,)
_MODE_CONNECTED_SPEEDS = (0x1A,)
_MODE_SET_SPEED = (0x18,)
_MODE_SET_COLOR = (0x22,)
_MODE_SET_LED_PORTS = (0x1E,)
_MODE_SET_LED_DATA = (0x1D,)
_MODE_DEVICE_MEMORY_COLOR = (0x65, 0x6D)

_DATA_TYPE_LED_COUNT = (0x0F, 0x00)
_DATA_TYPE_SPEEDS = (0x06, 0x00)
_DATA_TYPE_TEMPS = (0x10, 0x00)
_DATA_TYPE_CONNECTED_SPEEDS = (0x09, 0x00)
_DATA_TYPE_SET_SPEED = (0x07, 0x00)
_DATA_TYPE_SET_COLOR = (0x12, 0x00)
_DATA_TYPE_DEVICE_MEMORY_COLOR = (0x7E, 0x20)
_DATA_TYPE_DEVICE_MEMORY_EFFECT = (0x02, 0xA4)

_LED_PORT_COUNT = 2
_MAX_LEDS = 204
_MAX_COLOR_WRITE_CHUNK = 61

_MODES = {
    "off": 0x04,
    "fixed": 0x04,
}

_DEVICE_MEMORY_EFFECTS = {
    "rainbow": bytes([0x08, 0x04, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01]),
}


class CommanderDuo(UsbHidDriver):
    """Corsair Commander DUO."""

    _MATCHES = [
        (0x1B1C, 0x0C56, "Corsair Commander DUO", {}),
    ]

    def __init__(self, device, description, **kwargs):
        super().__init__(device, description, **kwargs)
        self._fan_count = 2
        self._temp_sensor_count = 2
        self._led_count = [0] * _LED_PORT_COUNT

    def initialize(self, **kwargs):
        res = self._send_command(_CMD_GET_FIRMWARE)
        fw_version = (res[3], res[4], u16le_from(res, offset=5))
        status = [("Firmware version", "{}.{}.{}".format(*fw_version), "")]

        with self._software_mode_context(restore_hardware_mode=True):
            connected = self._get_connected_fans()
            for i in range(self._fan_count):
                status += [(f"Fan port {i + 1} connected", connected[i], "")]

            temps = self._get_temps()
            for i in range(self._temp_sensor_count):
                status += [(f"Temperature sensor {i + 1} connected", temps[i] is not None, "")]

            led_counts = self._get_led_counts()
            for i in range(_LED_PORT_COUNT):
                status += [(f"ARGB port {i + 1} LED count", led_counts[i], "")]

        return status

    def get_status(self, **kwargs):
        status = []
        with self._software_mode_context(restore_hardware_mode=True):
            speeds = self._get_speeds()
            for i, speed in enumerate(speeds):
                status += [(f"Fan speed {i + 1}", speed, "rpm")]

            temps = self._get_temps()
            for i, temp in enumerate(temps):
                if temp is not None:
                    status += [(f"Temperature {i + 1}", temp, "°C")]

        return status

    def set_color(self, channel, mode, colors, non_volatile=False, **kwargs):
        if mode not in _MODES and not (non_volatile and mode in _DEVICE_MEMORY_EFFECTS):
            raise ValueError(f'mode "{mode}" is not valid')

        led_channels = self._parse_led_channels(channel)
        colors = list(colors)

        if non_volatile:
            try:
                self._send_command(_CMD_WAKE)
                time.sleep(0.05)
                self._send_device_memory_color(mode, colors)
            finally:
                self._send_command(_CMD_SLEEP, allow_timeout=True)
            return

        start_led = clamp(kwargs.get("start_led", 1), 1, _MAX_LEDS) - 1

        with self._software_mode_context():
            led_counts = self._get_led_counts()
            requested_leds = kwargs.get("maximum_leds")
            configured_counts = self._configured_led_counts(
                led_channels, led_counts, requested_leds, start_led
            )
            self._setup_led_ports(configured_counts)
            self._set_color_endpoint()
            self._send_color_data(
                self._make_color_buffer(led_channels, configured_counts, start_led, mode, colors)
            )

    def set_speed_profile(self, channel, profile, **kwargs):
        raise NotSupportedByDriver

    def set_fixed_speed(self, channel, duty, **kwargs):
        fan = self._parse_fan_channel(channel)
        percent = clamp(int(duty), 0, 100)

        with self._software_mode_context():
            self._send_write(
                _MODE_SET_SPEED, _DATA_TYPE_SET_SPEED, bytes([0x01, fan, 0x00, percent, 0x00])
            )

    def _parse_fan_channel(self, channel):
        if isinstance(channel, int):
            if channel < 0 or channel >= self._fan_count:
                raise ValueError(f"fan channel index must be 0-{self._fan_count - 1}")
            return channel
        if isinstance(channel, str):
            if channel.lower() in ["fan1", "fan 1", "1"]:
                return 0
            if channel.lower() in ["fan2", "fan 2", "2"]:
                return 1
        raise ValueError(f"invalid fan channel: {channel!r}")

    @classmethod
    def probe(
        cls, handle, vendor=None, product=None, release=None, serial=None, match=None, **kwargs
    ):
        if handle.hidinfo["interface_number"] != _INTERFACE_NUMBER:
            return
        yield from super().probe(
            handle,
            vendor=vendor,
            product=product,
            release=release,
            serial=serial,
            match=match,
            **kwargs,
        )

    def _get_led_counts(self):
        res = self._read_data(_MODE_LED_COUNT, _DATA_TYPE_LED_COUNT)
        num_devices = min(res[0], _LED_PORT_COUNT)
        led_counts = []
        for i in range(num_devices):
            offset = 1 + i * 4
            connected = u16le_from(res, offset=offset) == 0x0002
            num_leds = u16le_from(res, offset=offset + 2)
            led_counts.append(num_leds if connected else 0)
        while len(led_counts) < _LED_PORT_COUNT:
            led_counts.append(0)
        self._led_count = led_counts
        return led_counts

    def _parse_led_channels(self, channel):
        if channel in ["argb", "argb1", "led1"]:
            return [0]
        if channel in ["argb2", "led2"]:
            return [1]
        if channel in ["led", "sync"]:
            return [0, 1]
        raise ValueError(
            'unknown channel, should be one of: "argb", "argb1", "argb2", "led", '
            '"led1", "led2", or "sync"'
        )

    def _configured_led_counts(self, led_channels, led_counts, requested_leds, start_led):
        configured_counts = list(led_counts)
        for led_channel in led_channels:
            discovered_leds = led_counts[led_channel]
            if requested_leds is None and discovered_leds == 0:
                configured_counts[led_channel] = 0
                continue
            num_leds = requested_leds if requested_leds is not None else discovered_leds
            configured_counts[led_channel] = clamp(num_leds, 1, _MAX_LEDS - start_led)
        return configured_counts

    def _make_color_buffer(self, led_channels, led_counts, start_led, mode, colors):
        color = (0, 0, 0)
        if mode != "off" and colors:
            color = tuple(colors[0])

        color_data = bytearray()
        for led_channel, led_count in enumerate(led_counts):
            for led_index in range(led_count):
                if led_channel in led_channels and led_index >= start_led:
                    color_data.extend(color)
                else:
                    color_data.extend([0x00, 0x00, 0x00])
        return bytes(color_data)

    def _send_device_memory_color(self, mode, colors):
        if mode in _DEVICE_MEMORY_EFFECTS:
            self._send_device_memory_write(
                _MODE_DEVICE_MEMORY_COLOR,
                _DATA_TYPE_DEVICE_MEMORY_EFFECT,
                _DEVICE_MEMORY_EFFECTS[mode],
            )
            return

        self._send_device_memory_write(
            _MODE_DEVICE_MEMORY_COLOR,
            _DATA_TYPE_DEVICE_MEMORY_COLOR,
            self._make_device_memory_color_payload(mode, colors),
        )

    def _make_device_memory_color_payload(self, mode, colors):
        red = green = blue = 0x00
        brightness = 0x00
        if mode != "off" and colors:
            red, green, blue = tuple(colors[0])
            brightness = 0xFF

        return bytes(
            [
                0x09,
                0x00,
                0x00,
                0x00,
                0x01,
                brightness,
                blue,
                green,
                red,
                0x02,
                0x00,
                0x01,
            ]
        )

    def _send_device_memory_write(self, endpoint, data_type, data):
        """Send a Device Memory endpoint write matching observed iCUE transactions."""
        payload = bytearray()
        payload.extend((len(data) + len(data_type)).to_bytes(2, "little"))
        payload.extend([0x00, 0x00])
        payload.extend(data_type)
        payload.extend(data)

        self._send_command(_CMD_OPEN_WRITE_ENDPOINT, endpoint, allow_timeout=True)
        self._send_command(_CMD_READ_METADATA, allow_timeout=True)
        self._send_command(_CMD_WRITE_ENDPOINT, bytes(payload), allow_timeout=True)
        time.sleep(0.02)
        self._send_command(_CMD_CLOSE_WRITE_ENDPOINT, allow_timeout=True)

    def _setup_led_ports(self, led_counts):
        port_payload = bytearray([0x0D, 0x00, _LED_PORT_COUNT])
        for led_count in led_counts:
            port_payload.extend([0x01, 0x01 if led_count else 0x00])
        self._send_write(_MODE_SET_LED_PORTS, (), bytes(port_payload), extra=0)

        led_payload = bytearray([0x0C, 0x00, _LED_PORT_COUNT])
        for led_count in led_counts:
            led_payload.extend([led_count, 0x00])
        self._send_write(_MODE_SET_LED_DATA, (), bytes(led_payload), extra=0)
        time.sleep(0.1)
        self._send_command(_CMD_RESET_LED_POWER, allow_timeout=True)

    def _set_color_endpoint(self):
        self._send_command(_CMD_CLOSE_WRITE_ENDPOINT, _MODE_SET_COLOR, allow_timeout=True)
        time.sleep(0.02)
        self._send_command(_CMD_OPEN_COLOR_ENDPOINT, _MODE_SET_COLOR, allow_timeout=True)
        time.sleep(0.02)

    def _send_color_data(self, data):
        payload = bytearray()
        payload.extend((len(data) + 2).to_bytes(2, "little"))
        payload.extend([0x00, 0x00])
        payload.extend(_DATA_TYPE_SET_COLOR)
        payload.extend(data)

        for offset in range(0, len(payload), _MAX_COLOR_WRITE_CHUNK):
            command = _CMD_WRITE_COLOR if offset == 0 else _CMD_WRITE_COLOR_MORE
            self._send_command(
                command, payload[offset : offset + _MAX_COLOR_WRITE_CHUNK], allow_timeout=True
            )
        self._send_command(_CMD_CLOSE_WRITE_ENDPOINT, _MODE_SET_COLOR, allow_timeout=True)

    def _get_connected_fans(self):
        res = self._read_data(_MODE_CONNECTED_SPEEDS, _DATA_TYPE_CONNECTED_SPEEDS)
        num_devices = res[0]
        connected = []
        for i in range(min(num_devices, self._fan_count)):
            connected.append(res[i + 1] == 0x03)
        while len(connected) < self._fan_count:
            connected.append(False)
        return connected

    def _get_speeds(self):
        res = self._read_data(_MODE_GET_SPEEDS, _DATA_TYPE_SPEEDS)
        speeds = []
        num_speeds = res[0]
        for i in range(min(num_speeds, self._fan_count)):
            speed = u16le_from(res, offset=1 + i * 2)
            speeds.append(speed)
        while len(speeds) < self._fan_count:
            speeds.append(0)
        return speeds

    def _get_temps(self):
        res = self._read_data(_MODE_GET_TEMPS, _DATA_TYPE_TEMPS)
        num_temps = res[0]
        temps = []
        for i in range(min(num_temps, self._temp_sensor_count)):
            connected = res[1 + i * 3] == 0x00
            if connected:
                temp_raw = u16le_from(res, offset=1 + i * 3 + 1)
                temps.append(temp_raw / 10)
            else:
                temps.append(None)
        while len(temps) < self._temp_sensor_count:
            temps.append(None)
        return temps

    def _read_data(self, mode, data_type):
        last_dtype = None
        for _ in range(3):
            responses = [self._send_command(_CMD_CLOSE_ENDPOINT, allow_timeout=True)]
            time.sleep(0.02)
            responses.append(self._send_command(_CMD_OPEN_ENDPOINT, mode, allow_timeout=True))
            time.sleep(0.02)

            responses.append(self._send_command(_CMD_READ_INITIAL, allow_timeout=True))
            responses.append(self._send_command(_CMD_READ_MORE, allow_timeout=True))
            responses.append(self._send_command(_CMD_READ_FINAL, allow_timeout=True))
            responses.append(self._send_command(_CMD_CLOSE_ENDPOINT, allow_timeout=True))

            for response in responses:
                if len(response) >= 5:
                    last_dtype = tuple(response[3:5])
                    if last_dtype == data_type:
                        return response[5:]

            time.sleep(0.05)

        raise ExpectationNotMet(f"device returned incorrect data type: {last_dtype!r}")

    def _send_command(self, command, data=(), allow_timeout=False):
        buf = bytearray(_REPORT_LENGTH + 1)
        buf[1] = 0x08

        cmd_start = 2
        data_start = cmd_start + len(command)
        data_end = data_start + len(data)

        buf[cmd_start:data_start] = command
        buf[data_start:data_end] = data

        self.device.clear_enqueued_reports()
        self.device.write(buf)
        time.sleep(0.02)

        try:
            res = self.device.read(_RESPONSE_LENGTH)
        except Timeout:
            if allow_timeout:
                return b""
            raise

        while res[0] != 0x00:
            try:
                res = self.device.read(_RESPONSE_LENGTH)
            except Timeout:
                if allow_timeout:
                    return b""
                raise

        return bytes(res)

    def _send_write(self, endpoint, data_type, data, extra=2):
        """Send a write transaction to an endpoint."""
        payload = bytearray()
        payload.extend((len(data) + extra).to_bytes(2, "little"))
        payload.extend([0x00, 0x00])
        payload.extend(data_type)
        payload.extend(data)

        self._send_command(_CMD_CLOSE_WRITE_ENDPOINT, endpoint, allow_timeout=True)
        time.sleep(0.02)
        self._send_command(_CMD_OPEN_WRITE_ENDPOINT, endpoint, allow_timeout=True)
        time.sleep(0.02)
        self._send_command(_CMD_WRITE_ENDPOINT, bytes(payload), allow_timeout=True)
        self._send_command(_CMD_CLOSE_WRITE_ENDPOINT, endpoint, allow_timeout=True)

    @contextmanager
    def _software_mode_context(self, restore_hardware_mode=False):
        """Enter software mode and optionally restore hardware mode afterwards.

        The Commander DUO ignores fixed-speed writes if hardware mode is
        restored immediately afterwards, so public operations keep software mode
        active by default.
        """
        try:
            self._send_command(_CMD_WAKE)
            time.sleep(0.05)
            yield
        finally:
            if restore_hardware_mode:
                self._send_command(_CMD_SLEEP)
