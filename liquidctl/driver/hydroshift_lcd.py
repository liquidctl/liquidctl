"""liquidctl drivers for Lian Li HydroShift LCD liquid coolers.

Supported devices:

- Lian Li HydroShift LCD 360S
- Lian Li HydroShift LCD RGB
- Lian Li HydroShift LCD TL

Copyright liquidctl contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import io
import logging
import math
import re

from PIL import Image, ImageSequence

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver

_LOGGER = logging.getLogger(__name__)

# LCD resolution
_LCD_WIDTH = 480
_LCD_HEIGHT = 480
_JPEG_QUALITY = 85

# HID report sizes
_REPORT_A_SIZE = 64
_REPORT_B_SIZE = 1024
_REPORT_C_SIZE = 512

# Report IDs
_REPORT_ID_A = 0x01
_REPORT_ID_B = 0x02
_REPORT_ID_C = 0x03

# A-command bytes
_CMD_HANDSHAKE = 0x81
_CMD_SET_PUMP_LIGHT = 0x83
_CMD_SET_FAN_LIGHT = 0x85
_CMD_GET_FIRMWARE = 0x86
_CMD_SET_PUMP_PWM = 0x8A
_CMD_SET_FAN_PWM = 0x8B
_CMD_RESET_DEVICE = 0x8E

# B/C-command bytes (LCD)
_CMD_LCD_CONTROL = 0x0C
_CMD_SEND_JPEG = 0x0E
_CMD_LCD_AVAILABLE = 0x17

# LCD modes
_LCD_MODE_LOCAL_UI = 0
_LCD_MODE_APPLICATION = 1
_LCD_MODE_LOCAL_H264 = 2
_LCD_MODE_LOCAL_AVI = 3
_LCD_MODE_LCD_SETTING = 4
_LCD_MODE_LCD_TEST = 5

# Max payload per B/C-command packet (after 11-byte header)
_B_CMD_MAX_PAYLOAD = 1013  # 1024 - 11
_C_CMD_MAX_PAYLOAD = 501   # 512 - 11

_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_FAN_SPEED = "Fan speed"
_STATUS_FAN_DUTY = "Fan duty"

_PUMP_RPM_MAX = 3600
_FAN_RPM_MAX = 2520

_SPEED_CHANNELS = {
    "fan": _CMD_SET_FAN_PWM,
    "pump": _CMD_SET_PUMP_PWM,
}

_FAN_LIGHTING_MODES = {
    "rainbow": 0x01,
    "rainbow-morph": 0x02,
    "static": 0x03,
    "breathing": 0x04,
    "runway": 0x05,
    "meteor": 0x06,
    "color-cycle": 0x07,
    "staggered": 0x08,
    "tide": 0x09,
    "mixing": 0x0A,
    "ripple": 0x0E,
    "reflect": 0x0F,
    "tail-chasing": 0x10,
    "paint": 0x11,
    "ping-pong": 0x12,
}

_LIGHTING_SPEEDS = {
    "slowest": 0x00,
    "slower": 0x01,
    "normal": 0x02,
    "faster": 0x03,
    "fastest": 0x04,
}

_LIGHTING_DIRECTIONS = {
    "forward": 0x00,
    "backward": 0x01,
}

_LCD_ROTATIONS = {
    0: 0,
    90: 1,
    180: 2,
    270: 3,
}


def _quoted(*names):
    return ", ".join(map(repr, names))


def _write_colors(buf, colors, offset, max_bytes):
    """Write up to 4 RGB color triplets into buf at offset."""
    for i in range(min(len(colors), max_bytes // 3)):
        buf[offset + i * 3] = colors[i][0]
        buf[offset + i * 3 + 1] = colors[i][1]
        buf[offset + i * 3 + 2] = colors[i][2]


class HydroShiftLCD(UsbHidDriver):
    """liquidctl driver for Lian Li HydroShift LCD coolers."""

    _MATCHES = [
        (
            0x0416,
            0x7398,
            "Lian Li HydroShift LCD 360S",
            {},
        ),
        (
            0x0416,
            0x7399,
            "Lian Li HydroShift LCD RGB",
            {},
        ),
        (
            0x0416,
            0x739A,
            "Lian Li HydroShift LCD TL",
            {},
        ),
    ]

    def initialize(self, direct_access=False, **kwargs):
        """Initialize the device and return firmware version and status.

        Returns a list of `[(<property>, <value>, <unit>)]` tuples with
        firmware version and initial sensor readings.
        """
        self.device.clear_enqueued_reports()
        self._rotation = 0

        fw_version = self._read_firmware_version()
        _LOGGER.info("firmware version: %s", fw_version)

        # Parse firmware version to determine C-command support.
        # The firmware string looks like "N9,01,HS,SQ,HydroShift,V3.0B.02C,0.7"
        # The actual version is the LAST "major.minor" numeric segment (e.g. "0.7").
        self._use_c_cmd = False
        matches = re.findall(r"(?:^|,)(\d+)\.(\d+)(?:$|,)", fw_version)
        if matches:
            major, minor = int(matches[-1][0]), int(matches[-1][1])
            _LOGGER.info("detected firmware version: %d.%d", major, minor)
            if major > 1 or (major == 1 and minor >= 2):
                self._use_c_cmd = True
                _LOGGER.info("firmware >= 1.2, using C-command (512-byte) LCD packets")

        status = [("Firmware version", fw_version, "")]

        try:
            handshake = self._get_handshake()
            status.extend([
                (_STATUS_TEMPERATURE, handshake["temperature"], "°C"),
                (_STATUS_FAN_SPEED, handshake["fan_rpm"], "rpm"),
                (_STATUS_PUMP_SPEED, handshake["pump_rpm"], "rpm"),
            ])
        except Exception as e:
            _LOGGER.warning("failed to read initial status: %s", e)

        return sorted(status)

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
            (_STATUS_PUMP_DUTY, min(handshake["pump_rpm"] / _PUMP_RPM_MAX * 100, 100), "%"),
        ]

    def set_fixed_speed(self, channel, duty, direct_access=False, **kwargs):
        """Set fan or pump to a fixed speed duty (0-100%)."""
        if channel not in _SPEED_CHANNELS:
            raise NotSupportedByDevice(
                f"fixed speed control for {channel} is not supported, "
                f"should be one of: {_quoted(*_SPEED_CHANNELS)}"
            )
        speed = max(0, min(100, duty))
        self._write_a_cmd_with_data(_SPEED_CHANNELS[channel], [0x00, speed])

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_color(self, channel, mode, colors, speed="normal", direction="forward", **kwargs):
        """Set the LED color mode for the fan channel.

        Valid channels: fan
        Valid modes: rainbow, rainbow-morph, static, breathing, runway, meteor,
            color-cycle, staggered, tide, mixing, ripple, reflect,
            tail-chasing, paint, ping-pong
        Speed: slowest, slower, normal, faster, fastest
        Direction: forward, backward
        Colors: up to 4 RGB colors depending on mode
        """
        if channel != "fan":
            raise NotSupportedByDevice(
                f"lighting control for {channel} is not supported, use 'fan'"
            )

        if mode not in _FAN_LIGHTING_MODES:
            raise ValueError(
                f"unknown lighting mode: {mode}, "
                f"should be one of: {_quoted(*_FAN_LIGHTING_MODES)}"
            )
        if speed not in _LIGHTING_SPEEDS:
            raise ValueError(
                f"unknown lighting speed: {speed}, "
                f"should be one of: {_quoted(*_LIGHTING_SPEEDS)}"
            )
        if direction not in _LIGHTING_DIRECTIONS:
            raise ValueError(
                f"unknown lighting direction: {direction}, "
                f"should be one of: {_quoted(*_LIGHTING_DIRECTIONS)}"
            )

        colors = list(colors)
        req = [0] * 20
        req[0] = _FAN_LIGHTING_MODES[mode]
        req[1] = 4  # brightness (max)
        req[2] = _LIGHTING_SPEEDS[speed]
        _write_colors(req, colors, 3, 12)
        req[15] = _LIGHTING_DIRECTIONS[direction]
        req[16] = 0  # off flag
        req[17] = 0  # source: MCU
        req[18] = 0  # sync_to_pump
        req[19] = 24  # LED count

        self._write_a_cmd_with_data(_CMD_SET_FAN_LIGHT, req)

    def set_screen(self, channel, mode, value, **kwargs):
        """Set the LCD screen mode.

        Valid channels: lcd
        Valid modes:
            static <path>   -- display a static image (JPEG/PNG/BMP)
            gif <path>      -- display an animated GIF (sends first frame as static)
            brightness <0-100> -- set LCD brightness
            orientation <0|90|180|270> -- set LCD rotation
            lcd -- switch to application (streaming) mode
        """
        if channel != "lcd":
            raise NotSupportedByDevice(
                f"screen control for {channel} is not supported, use 'lcd'"
            )

        if mode == "brightness":
            brightness = max(0, min(100, int(value)))
            self._send_lcd_control(
                lcd_mode=_LCD_MODE_APPLICATION,
                brightness=brightness,
            )

        elif mode == "orientation":
            rotation = int(value)
            if rotation not in _LCD_ROTATIONS:
                raise ValueError(
                    f"unsupported rotation: {rotation}, "
                    f"should be one of: {_quoted(*_LCD_ROTATIONS)}"
                )
            self._rotation = rotation
            _LOGGER.info("LCD rotation set to %d degrees (applied on next image send)", rotation)

        elif mode == "static":
            self._send_static_image(value)

        elif mode == "gif":
            self._send_gif(value)

        elif mode == "lcd":
            self._send_lcd_control(lcd_mode=_LCD_MODE_APPLICATION)

        else:
            raise ValueError(
                f"unknown screen mode: {mode}, "
                f"should be one of: 'static', 'gif', 'brightness', 'orientation', 'lcd'"
            )

    def disconnect(self, **kwargs):
        """Disconnect from the device."""
        return self.device.close()

    # -- internal: A-command helpers (64-byte HID reports) --

    def _build_a_cmd(self, cmd, data=None):
        """Build a 64-byte A-command packet."""
        pkt = [0] * _REPORT_A_SIZE
        pkt[0] = _REPORT_ID_A
        pkt[1] = cmd
        if data:
            pkt[5] = len(data)
            pkt[6:6 + len(data)] = data
        return pkt

    def _write_a_cmd(self, cmd):
        """Send an A-command with no data."""
        self.device.write(self._build_a_cmd(cmd))

    def _write_a_cmd_with_data(self, cmd, data):
        """Send an A-command with data payload (chunked if > 58 bytes)."""
        offset = 0
        num = 0
        while offset < len(data):
            chunk_len = min(len(data) - offset, 58)
            pkt = [0] * _REPORT_A_SIZE
            pkt[0] = _REPORT_ID_A
            pkt[1] = cmd
            num_bytes = num.to_bytes(2, byteorder="big")
            pkt[3] = num_bytes[0]
            pkt[4] = num_bytes[1]
            pkt[5] = chunk_len
            pkt[6:6 + chunk_len] = data[offset:offset + chunk_len]
            self.device.write(pkt)
            num += 1
            offset += chunk_len

    def _read_a_cmd(self):
        """Read an A-command response, handling multi-packet responses."""
        r = self.device.read(64)
        if not r or len(r) < 6:
            raise ValueError("no response from device")
        if r[0] != _REPORT_ID_A:
            raise ValueError(f"unexpected report ID: 0x{r[0]:02x}")

        command = r[1]
        length = r[5]
        current_len = min(length, 58)
        data = list(r[6:6 + current_len])

        packet_count = math.ceil(length / 58) if length > 0 else 1
        for i in range(1, packet_count):
            r = self.device.read(64)
            if r[0] != _REPORT_ID_A or r[1] != command:
                raise ValueError("unexpected continuation packet")
            remaining = length - len(data)
            chunk_len = min(remaining, 58)
            data.extend(r[6:6 + chunk_len])

        return {"command": command, "length": length, "data": data}

    # -- internal: B/C-command helpers (LCD packets) --

    def _build_lcd_packet(self, cmd, total_size, pkt_num, payload):
        """Build a B-command (1024-byte) or C-command (512-byte) LCD packet."""
        if self._use_c_cmd:
            report_id = _REPORT_ID_C
            pkt_size = _REPORT_C_SIZE
        else:
            report_id = _REPORT_ID_B
            pkt_size = _REPORT_B_SIZE

        pkt = [0] * pkt_size
        pkt[0] = report_id
        pkt[1] = cmd

        # total data size (big-endian u32)
        pkt[2] = (total_size >> 24) & 0xFF
        pkt[3] = (total_size >> 16) & 0xFF
        pkt[4] = (total_size >> 8) & 0xFF
        pkt[5] = total_size & 0xFF

        # packet number (big-endian u24)
        pkt[6] = (pkt_num >> 16) & 0xFF
        pkt[7] = (pkt_num >> 8) & 0xFF
        pkt[8] = pkt_num & 0xFF

        # payload length this packet (big-endian u16)
        pkt[9] = (len(payload) >> 8) & 0xFF
        pkt[10] = len(payload) & 0xFF

        # payload data
        pkt[11:11 + len(payload)] = payload

        return pkt

    def _write_lcd_cmd(self, cmd, payload):
        """Write a B/C-command with payload, splitting into appropriate chunks."""
        if self._use_c_cmd:
            max_payload = _C_CMD_MAX_PAYLOAD
        else:
            max_payload = _B_CMD_MAX_PAYLOAD

        total_size = len(payload)
        offset = 0
        pkt_num = 0

        while offset < total_size:
            chunk = payload[offset:offset + max_payload]
            pkt = self._build_lcd_packet(cmd, total_size, pkt_num, chunk)
            self.device.write(pkt)
            offset += len(chunk)
            pkt_num += 1

        # consume any response
        try:
            self.device.read(64, timeout=20)
        except Exception:
            pass

    def _write_lcd_control_cmd(self, data):
        """Write a B/C-command for LCD control (non-streaming)."""
        if self._use_c_cmd:
            report_id = _REPORT_ID_C
            pkt_size = _REPORT_C_SIZE
        else:
            report_id = _REPORT_ID_B
            pkt_size = _REPORT_B_SIZE

        pkt = [0] * pkt_size
        pkt[0] = report_id
        pkt[1] = _CMD_LCD_CONTROL
        # For control commands, total_size and pkt_num are 0
        # payload length
        pkt[9] = (len(data) >> 8) & 0xFF
        pkt[10] = len(data) & 0xFF
        pkt[11:11 + len(data)] = data
        self.device.write(pkt)

    # -- internal: device communication --

    def _read_firmware_version(self):
        """Read firmware version string from device."""
        self._write_a_cmd(_CMD_GET_FIRMWARE)

        # First response: version string
        p1 = self._read_a_cmd()
        p1_data = p1["data"][:p1["data"].index(0)] if 0 in p1["data"] else p1["data"]
        version_str = bytes(p1_data).decode("ascii", errors="ignore").strip()

        # Second response: date string (must be consumed)
        try:
            p2 = self._read_a_cmd()
            p2_data = p2["data"][:p2["data"].index(0)] if 0 in p2["data"] else p2["data"]
            date_str = bytes(p2_data).decode("ascii", errors="ignore").strip()
            _LOGGER.debug("firmware date: %s", date_str)
        except Exception:
            pass

        return version_str

    def _get_handshake(self):
        """Send handshake and parse RPM/temperature response."""
        # Drop any stale reports left in the HID input queue (e.g. an LCD
        # B/C-command response from a prior operation, or leftover bytes from
        # firmware-version reads) so _read_a_cmd does not pick them up.
        self.device.clear_enqueued_reports()
        self._write_a_cmd(_CMD_HANDSHAKE)
        r = self._read_a_cmd()

        if r["command"] != _CMD_HANDSHAKE:
            raise ValueError(f"unexpected handshake response: 0x{r['command']:02x}")

        data = r["data"]
        fan_rpm = int.from_bytes(data[0:2], byteorder="big")
        pump_rpm = int.from_bytes(data[2:4], byteorder="big")

        temperature = 0.0
        if r["length"] >= 7 and data[4] != 0:
            temperature = data[5] + (data[6] % 10) / 10.0

        return {
            "fan_rpm": fan_rpm,
            "pump_rpm": pump_rpm,
            "temperature": temperature,
        }

    # -- internal: LCD image sending --

    def _encode_jpeg(self, image):
        """Encode a PIL Image as JPEG bytes at the configured quality."""
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=_JPEG_QUALITY, subsampling="4:2:0")
        return buf.getvalue()

    def _prepare_image(self, image_path):
        """Load, resize, rotate, and encode an image as JPEG."""
        img = Image.open(image_path)
        img = img.convert("RGB")
        img = img.resize((_LCD_WIDTH, _LCD_HEIGHT), Image.LANCZOS)
        rotation = getattr(self, "_rotation", 0)
        if rotation:
            img = img.rotate(rotation, expand=False)
        return self._encode_jpeg(img)

    def _send_lcd_control(self, lcd_mode=_LCD_MODE_APPLICATION, brightness=50,
                          rotation=0, fps=24):
        """Send LCD control command to configure display mode."""
        data = [0] * 8
        data[0] = lcd_mode
        data[1] = brightness
        data[2] = rotation
        data[7] = fps
        self._write_lcd_control_cmd(data)

    def _send_jpeg_frame(self, jpeg_data):
        """Send a JPEG frame to the LCD."""
        self._write_lcd_cmd(_CMD_SEND_JPEG, list(jpeg_data))

    def _send_static_image(self, image_path):
        """Send a static image to the LCD screen."""
        _LOGGER.info("sending static image: %s", image_path)

        # Switch to application mode
        self._send_lcd_control(lcd_mode=_LCD_MODE_APPLICATION)

        jpeg_data = self._prepare_image(image_path)
        _LOGGER.debug("JPEG size: %d bytes", len(jpeg_data))

        self._send_jpeg_frame(jpeg_data)

    def _send_gif(self, gif_path):
        """Send GIF frames to the LCD screen.

        Sends the first frame as a static image. For continuous animation,
        a daemon process would be needed to loop frames at the target FPS.
        """
        _LOGGER.info("sending GIF: %s", gif_path)

        self._send_lcd_control(lcd_mode=_LCD_MODE_APPLICATION, fps=24)

        img = Image.open(gif_path)
        frame = img.convert("RGB").resize((_LCD_WIDTH, _LCD_HEIGHT), Image.LANCZOS)
        jpeg_data = self._encode_jpeg(frame)
        self._send_jpeg_frame(jpeg_data)

        n_frames = getattr(img, "n_frames", 1)
        if n_frames > 1:
            _LOGGER.info(
                "GIF has %d frames; only the first frame was sent. "
                "Use an external loop to animate.",
                n_frames,
            )
