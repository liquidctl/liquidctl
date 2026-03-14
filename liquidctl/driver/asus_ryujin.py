"""liquidctl driver for the ASUS Ryujin II and Ryujin III liquid coolers.

Supports fan/pump control, sensor monitoring, and LCD screen control for
Ryujin III models (320x240 BGR display).

Copyright Florian Freudiger and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import sys
import time
from typing import List

from liquidctl.driver.usb import PyUsbDevice, UsbHidDriver
from liquidctl.error import ExpectationNotMet, NotSupportedByDriver
from liquidctl.util import clamp, u16le_from, rpadlist, fraction_of_byte

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 65
_PREFIX = 0xEC

# Requests and their response headers
_REQUEST_GET_FIRMWARE = (0x82, 0x02)
_REQUEST_GET_COOLER_STATUS = (0x99, 0x19)
_REQUEST_GET_COOLER_DUTY = (0x9A, 0x1A)
_REQUEST_GET_CONTROLLER_DUTY = (0xA1, 0x21)
_REQUEST_GET_CONTROLLER_SPEED = (0xA0, 0x20)
_REQUEST_GET_DISPLAY_OPTION = (0xDC, 0x5C)

# Command headers that don't need a response
_CMD_SET_COOLER_SPEED = 0x1A
_CMD_SET_CONTROLLER_SPEED = 0x21
_CMD_SWITCH_DISPLAY_MODE = 0x51
_CMD_SET_HW_MONITOR_LAYOUT = 0x52
_CMD_SET_HW_MONITOR_STRING = 0x53
_CMD_SET_DISPLAY_OPTION = 0x5C
_CMD_SET_CLOCK = 0x11
_CMD_FLUSH_FRAMEBUFFER = 0x7F

# Display mode bytes (wire encoding, from ryujin.py DisplayMode enum)
_DISPLAY_MODE_OFF = 0x00
_DISPLAY_MODE_ANIMATION = 0x04
_DISPLAY_MODE_CLOCK = 0x08
_DISPLAY_MODE_SINGLE_ANIM = 0x10
_DISPLAY_MODE_SLIDESHOW = 0x1F
_DISPLAY_MODE_FRAMEBUFFER = 0x20
_DISPLAY_MODE_HW_MONITOR = 0x21

# LCD parameters
_LCD_WIDTH = 320
_LCD_HEIGHT = 240
_LCD_BPP = 3  # BGR, 3 bytes/pixel
_LCD_FRAME_SIZE = _LCD_WIDTH * _LCD_HEIGHT * _LCD_BPP  # 230,400 bytes

# Endpoints
_EP_BULK_OUT = 0x01
_EP_HID_OUT = 0x02
_EP_HID_IN = 0x82

_STATUS_FIRMWARE = "Firmware version"
_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_COOLER_FAN_SPEED = "Pump fan speed"
_STATUS_COOLER_FAN_DUTY = "Pump fan duty"
_STATUS_CONTROLLER_FAN_SPEED = "External fan {} speed"
_STATUS_CONTROLLER_FAN_DUTY = "External fan duty"

# HW monitor background styles
_HW_MONITOR_STYLES = {
    "galactic": 0x00,
    "cyberpunk": 0x01,
    "custom": 0x02,
}


class AsusRyujin(UsbHidDriver):
    """ASUS Ryujin II & Ryujin III liquid coolers."""

    _MATCHES = [
        (
            0x0B05,
            0x1988,
            "ASUS Ryujin II 360",
            {
                "fan_count": 4,
                "pump_speed_offset": 5,
                "pump_fan_speed_offset": 7,
                "temp_offset": 3,
                "duty_channel": 0,
                "has_lcd": False,
            },
        ),
        (
            0x0B05,
            0x1BCB,
            "ASUS Ryujin III Extreme",
            {
                "fan_count": 0,
                "pump_speed_offset": 7,
                "pump_fan_speed_offset": 10,
                "temp_offset": 5,
                "duty_channel": 1,
                "has_lcd": True,
            },
        ),
        (
            0x0B05,
            0x1AA2,
            "ASUS Ryujin III 360",
            {
                "fan_count": 0,
                "pump_speed_offset": 7,
                "pump_fan_speed_offset": 10,
                "temp_offset": 5,
                "duty_channel": 1,
                "has_lcd": True,
            },
        ),
        (
            0x0B05,
            0x1ADE,
            "ASUS Ryujin III EVA",
            {
                "fan_count": 0,
                "pump_speed_offset": 7,
                "pump_fan_speed_offset": 10,
                "temp_offset": 5,
                "duty_channel": 1,
                "has_lcd": True,
            },
        ),
        (
            0x0B05,
            0x1ADA,
            "ASUS Ryujin III White",
            {
                "fan_count": 0,
                "pump_speed_offset": 7,
                "pump_fan_speed_offset": 10,
                "temp_offset": 5,
                "duty_channel": 1,
                "has_lcd": True,
            },
        ),
    ]

    def __init__(
        self,
        device,
        description,
        fan_count,
        pump_speed_offset,
        pump_fan_speed_offset,
        temp_offset,
        duty_channel,
        has_lcd=False,
        **kwargs,
    ):
        super().__init__(device, description, **kwargs)

        self._fan_count = fan_count
        self._pump_speed_offset = pump_speed_offset
        self._pump_fan_speed_offset = pump_fan_speed_offset
        self._temp_offset = temp_offset
        self._duty_channel = duty_channel
        self._has_lcd = has_lcd
        self._bulk_device = None

    def initialize(self, **kwargs):
        msg = self._request(*_REQUEST_GET_FIRMWARE)
        return [(_STATUS_FIRMWARE, "".join(map(chr, msg[3:18])), "")]

    def _get_raw_usb_device(self):
        """Get a raw pyusb device handle for bulk + HID access.

        Opens a pyusb handle alongside the existing hidapi handle.
        The hidapi handle is closed first to avoid conflicts.
        Must call _release_raw_usb_device() after.
        """
        if self._bulk_device is not None:
            return self._bulk_device

        import usb.core
        import usb.util

        # Close hidapi handle to release the HID interface
        try:
            self.device.close()
        except Exception:
            pass

        # Find and configure the raw USB device
        dev = usb.core.find(
            idVendor=self.vendor_id,
            idProduct=self.product_id,
        )
        if dev is None:
            raise ExpectationNotMet("could not find USB device for LCD")

        # Detach kernel drivers on both interfaces
        for i in range(2):
            try:
                if dev.is_kernel_driver_active(i):
                    dev.detach_kernel_driver(i)
            except Exception:
                pass

        try:
            dev.set_configuration()
        except usb.core.USBError:
            pass  # already configured

        # Claim both interfaces
        for i in range(2):
            try:
                usb.util.claim_interface(dev, i)
            except Exception:
                pass

        self._bulk_device = dev
        _LOGGER.debug("opened raw USB device for LCD")
        return dev

    def _release_raw_usb_device(self):
        """Release the raw USB device and reattach kernel drivers."""
        if self._bulk_device is not None:
            import usb.util

            for i in range(2):
                try:
                    usb.util.release_interface(self._bulk_device, i)
                except Exception:
                    pass
            # Reattach kernel HID driver so hidapi works on next invocation
            try:
                self._bulk_device.attach_kernel_driver(1)
            except Exception:
                pass
            try:
                usb.util.dispose_resources(self._bulk_device)
            except Exception:
                pass
            self._bulk_device = None

    def close(self, **kwargs):
        if self._bulk_device:
            self._release_raw_usb_device()
        super().close(**kwargs)

    def _get_cooler_duty(self) -> (int, int):
        """Get current pump and embedded fan duty in %."""
        msg = self._request(*_REQUEST_GET_COOLER_DUTY)
        return msg[4], msg[5]

    def _get_cooler_status(self) -> (int, int, int):
        """Get current liquid temperature, pump and embedded fan speed."""
        msg = self._request(*_REQUEST_GET_COOLER_STATUS)
        liquid_temp = msg[self._temp_offset] + msg[self._temp_offset + 1] / 10
        pump_speed = u16le_from(msg, self._pump_speed_offset)
        pump_fan_speed = u16le_from(msg, self._pump_fan_speed_offset)
        return liquid_temp, pump_speed, pump_fan_speed

    def _get_controller_speeds(self) -> List[int]:
        """Get AIO controller fan speeds in rpm."""
        msg = self._request(*_REQUEST_GET_CONTROLLER_SPEED)
        speed1 = u16le_from(msg, 5)
        speed2 = u16le_from(msg, 7)
        speed3 = u16le_from(msg, 9)
        speed4 = u16le_from(msg, 3)  # For some reason comes first in msg
        return [speed1, speed2, speed3, speed4]

    def _get_controller_duty(self) -> int:
        """Get AIO controller fan duty in %."""
        msg = self._request(*_REQUEST_GET_CONTROLLER_DUTY)
        return round(msg[4] / 0xFF * 100)

    def get_status(self, **kwargs):
        pump_duty, fan_duty = self._get_cooler_duty()
        liquid_temp, pump_speed, pump_fan_speed = self._get_cooler_status()

        status = [
            (_STATUS_TEMPERATURE, liquid_temp, "°C"),
            (_STATUS_PUMP_DUTY, pump_duty, "%"),
            (_STATUS_PUMP_SPEED, pump_speed, "rpm"),
            (_STATUS_COOLER_FAN_DUTY, fan_duty, "%"),
            (_STATUS_COOLER_FAN_SPEED, pump_fan_speed, "rpm"),
        ]

        if self._fan_count == 0:
            return status

        controller_duty = self._get_controller_duty()
        controller_speeds = self._get_controller_speeds()

        status.append((_STATUS_CONTROLLER_FAN_DUTY, controller_duty, "%"))

        for i, controller_speed in enumerate(controller_speeds):
            status.append((_STATUS_CONTROLLER_FAN_SPEED.format(i + 1), controller_speed, "rpm"))

        return status

    def _set_cooler_duties(self, pump_duty: int, fan_duty: int):
        self._write([_PREFIX, _CMD_SET_COOLER_SPEED, self._duty_channel, pump_duty, fan_duty])

    def _set_cooler_pump_duty(self, duty: int):
        pump_duty, fan_duty = self._get_cooler_duty()

        if duty == pump_duty:
            return

        self._set_cooler_duties(duty, fan_duty)

    def _set_cooler_fan_duty(self, duty: int):
        pump_duty, fan_duty = self._get_cooler_duty()

        if duty == fan_duty:
            return

        self._set_cooler_duties(pump_duty, duty)

    def _set_controller_duty(self, duty: int):
        # Controller duty is set between 0x00 and 0xFF
        duty = fraction_of_byte(percentage=duty)

        self._write([_PREFIX, _CMD_SET_CONTROLLER_SPEED, 0x00, 0x00, duty])

    def set_fixed_speed(self, channel, duty, **kwargs):
        duty = clamp(duty, 0, 100)
        channel_handlers = {
            "pump": [self._set_cooler_pump_duty],
            "pump-fan": [self._set_cooler_fan_duty],
        }

        if self._fan_count > 0:
            channel_handlers.update(
                {
                    "fans": [self._set_cooler_fan_duty, self._set_controller_duty],
                    "external-fans": [self._set_controller_duty],
                }
            )

        handlers = channel_handlers.get(channel)
        if handlers is None:
            raise ValueError(f"invalid channel: {channel}")

        for handler in handlers:
            handler(duty)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported — use set_fixed_speed or ryujin_fand for curves.

        To release back to the internal pump controller:

            liquidctl --match Ryujin set pump speed auto
        """
        raise NotSupportedByDriver(
            "speed profiles are host-driven on this device; "
            "use set_fixed_speed or the ryujin_fand daemon for fan curves"
        )

    def _release_cooler_control(self):
        """Release pump back to internal Asetek pump controller (ctrl_src=0).

        Only the pump has an internal controller. The embedded fan has no
        internal controller — it stays at whatever duty was last set (or 0 = off).
        The fan must always be driven by the host.
        """
        self._write([_PREFIX, _CMD_SET_COOLER_SPEED, 0x00, 0x00, 0x00])

    # ── LCD Screen Control ──────────────────────────────────────────────

    def set_screen(self, channel, mode, value, **kwargs):
        """Set the screen mode and content.

        Unstable.

        Supported channels, modes and values:

        | Channel | Mode | Value |
        | --- | --- | --- |
        | `lcd` | `static` | path to image file |
        | `lcd` | `liquid` | — (built-in ROG animation) |
        | `lcd` | `clock` | `24h` or `12h` (default: `24h`) |
        | `lcd` | `monitor` | — (HW monitor showing live stats) |
        | `lcd` | `off` | — |
        | `lcd` | `standby` | — (screen off for system sleep) |
        | `lcd` | `wake` | — (screen on, resume from standby) |
        | `lcd` | `release` | — (release pump to internal controller; fan stays at last duty) |
        | `lcd` | `brightness` | int between `0` and `100` (%) |
        | `lcd` | `orientation` | `0`, `1`, `2` or `3` (0°, 90°, 180°, 270°) |

        Requires Ryujin III (models with LCD display).
        """
        if not self._has_lcd:
            raise NotSupportedByDriver("this model does not have an LCD")

        if channel.lower() != "lcd":
            raise ValueError(f"invalid channel: {channel}, expected: lcd")

        if mode == "static":
            # Static image needs bulk EP — use pyusb
            if value is None:
                raise ValueError("static mode requires a path to an image file")
            self._set_screen_static(value)
            self._release_raw_usb_device()
        elif mode == "liquid":
            self._write([_PREFIX, _CMD_SWITCH_DISPLAY_MODE, _DISPLAY_MODE_ANIMATION])
        elif mode == "clock":
            fmt_24h = value != "12h"
            self._set_screen_clock_hid(fmt_24h)
        elif mode == "monitor":
            self._set_screen_hw_monitor_hid(**kwargs)
        elif mode == "off":
            self._write([_PREFIX, _CMD_SWITCH_DISPLAY_MODE, _DISPLAY_MODE_OFF])
        elif mode == "standby":
            self._write([_PREFIX, _CMD_SET_DISPLAY_OPTION, 0x20])
        elif mode == "wake":
            self._write([_PREFIX, _CMD_SET_DISPLAY_OPTION, 0x10])
        elif mode == "brightness":
            if value is None:
                raise ValueError("brightness mode requires a value (0-100)")
            brightness = clamp(int(value), 0, 100)
            self._write(
                [_PREFIX, _CMD_SET_DISPLAY_OPTION, 0x01, 0x00, 0x00, 0x00, 0x00, brightness]
            )
        elif mode == "orientation":
            if value is None:
                raise ValueError("orientation requires 0-3 (0°, 90°, 180°, 270°)")
            self._write([_PREFIX, _CMD_SET_DISPLAY_OPTION, 0x01, 0x00, 0x00, int(value)])
        elif mode == "release":
            self._release_cooler_control()
        else:
            raise ValueError(
                f"invalid mode: {mode}, valid: static, liquid, clock, monitor, off, "
                f"standby, wake, brightness, orientation, release"
            )

    def _raw_hid_write(self, cmd: list):
        """Write a HID command via raw pyusb (not hidapi).

        Used during LCD operations when we have the raw USB handle.
        """
        dev = self._get_raw_usb_device()
        payload = [_PREFIX] + (cmd + [0] * 64)[:64]
        dev.write(_EP_HID_OUT, payload)

    def _raw_hid_request(self, request_header: int, response_header: int) -> list:
        """Send a command and read response via raw pyusb."""
        dev = self._get_raw_usb_device()
        payload = [_PREFIX, request_header] + [0] * 63
        dev.write(_EP_HID_OUT, payload)
        msg = dev.read(_EP_HID_IN, _REPORT_LENGTH, timeout=1000)
        return list(msg)

    def _raw_get_cooler_status(self):
        """Read sensors via raw pyusb (used during LCD operations)."""
        msg = self._raw_hid_request(0x99, 0x19)
        liquid_temp = msg[self._temp_offset] + msg[self._temp_offset + 1] / 10
        pump_speed = u16le_from(msg, self._pump_speed_offset)
        pump_fan_speed = u16le_from(msg, self._pump_fan_speed_offset)
        return liquid_temp, pump_speed, pump_fan_speed

    def _switch_display_mode(self, mode_byte: int):
        """Send EC 51 to switch display mode."""
        self._raw_hid_write([_CMD_SWITCH_DISPLAY_MODE, mode_byte])
        _LOGGER.debug("switched display mode to 0x%02x", mode_byte)

    def _flush_framebuffer(self):
        """Send EC 7F 03 00 84 03 to flush framebuffer to LCD."""
        self._raw_hid_write([_CMD_FLUSH_FRAMEBUFFER, 0x03, 0x00, 0x84, 0x03])

    def _write_bulk(self, data: bytes):
        """Write raw data to bulk OUT endpoint."""
        dev = self._get_raw_usb_device()
        dev.write(_EP_BULK_OUT, data)

    def _set_screen_static(self, path: str):
        """Display a static image on the LCD.

        Loads the image, converts to 320x240 BGR, sends via bulk endpoint,
        then flushes. The image stays on screen until another mode is set.
        """
        try:
            from PIL import Image
        except ImportError:
            raise NotSupportedByDriver(
                "Pillow is required for static image mode: pip install Pillow"
            )

        img = Image.open(path)
        img = img.resize((_LCD_WIDTH, _LCD_HEIGHT), Image.LANCZOS)
        img = img.convert("RGB")

        # Convert RGB to BGR byte array
        pixels = img.tobytes()
        bgr = bytearray(_LCD_FRAME_SIZE)
        for i in range(0, len(pixels), 3):
            bgr[i] = pixels[i + 2]  # B
            bgr[i + 1] = pixels[i + 1]  # G
            bgr[i + 2] = pixels[i]  # R

        self._switch_display_mode(_DISPLAY_MODE_FRAMEBUFFER)
        time.sleep(0.1)
        self._write_bulk(bytes(bgr))
        self._flush_framebuffer()
        _LOGGER.info("displayed static image: %s", path)

    def _set_screen_clock_hid(self, fmt_24h: bool = True):
        """Switch to clock mode via hidapi (no pyusb needed)."""
        hr_fmt = 0x00 if fmt_24h else 0x01

        # Configure clock display (EC 5D)
        self._write([_PREFIX, 0x5D, 0x00, 0x01, 0x08, 0x00, hr_fmt, 0x05])
        time.sleep(0.05)

        # Sync RTC
        t = time.localtime()

        def bcd(val):
            return ((val // 10) << 4) | (val % 10)

        hour = t.tm_hour
        pm = 0x00
        if not fmt_24h:
            pm = 0x01 if hour >= 12 else 0x00
            hour = hour % 12 or 12
        self._write(
            [
                _PREFIX,
                _CMD_SET_CLOCK,
                0x00,
                0x00,
                0x08,
                0x00,
                hr_fmt,
                bcd(hour),
                bcd(t.tm_min),
                bcd(t.tm_sec),
                pm,
                0x01,
            ]
        )
        time.sleep(0.05)

        # Switch to clock mode
        self._write([_PREFIX, _CMD_SWITCH_DISPLAY_MODE, _DISPLAY_MODE_CLOCK, 0x00, hr_fmt])

    def _set_screen_hw_monitor_hid(self, **kwargs):
        """Switch to HW monitor mode via hidapi (no pyusb needed)."""
        # Read sensors while we have the HID handle
        try:
            liquid_temp, pump_speed, pump_fan_speed = self._get_cooler_status()
        except Exception:
            liquid_temp, pump_speed, pump_fan_speed = 0, 0, 0

        style = _HW_MONITOR_STYLES.get(kwargs.get("style", "custom"), 0x02)

        # Layout (EC 52)
        self._write(
            [
                _PREFIX,
                _CMD_SET_HW_MONITOR_LAYOUT,
                style,
                0x02,
                0x02,
                0x00,
                0,
                0,
                0,
                0xFF,
                255,
                255,
                255,
                0xFF,
                255,
                255,
                255,
                0xFF,
                255,
                255,
                255,
                0xFF,
                255,
                255,
                255,
                0xFF,
            ]
        )

        # Switch mode (EC 51)
        self._write([_PREFIX, _CMD_SWITCH_DISPLAY_MODE, _DISPLAY_MODE_HW_MONITOR])
        time.sleep(0.2)

        # Send sensor strings (EC 53)
        DEGC = bytes([0xE2, 0x84, 0x83]).decode("utf-8")
        RPM = bytes([0xE2, 0x86, 0x8C]).decode("utf-8")
        lines = [
            ("Liquid", f"{liquid_temp:.1f}{DEGC}"),
            ("Pump", f"{pump_speed}{RPM}"),
            ("Fan", f"{pump_fan_speed}{RPM}"),
        ]
        for i, (label, value) in enumerate(lines):
            lb = list(label.encode("utf-8")[:18]) + [0] * 18
            vb = list(value.encode("utf-8")[:12]) + [0] * 12
            self._write([_PREFIX, _CMD_SET_HW_MONITOR_STRING, i] + lb[:18] + vb[:12])

    def _set_screen_clock(self, fmt_24h: bool = True):
        """Switch to clock mode and sync the RTC.

        hr_fmt wire encoding: 0x00 = 24h, 0x01 = 12h (inverted from what you'd expect).
        Verified on live hardware (S750, PID 0x1ADA).
        """
        hr_fmt = 0x00 if fmt_24h else 0x01

        # Configure clock display (EC 5D)
        self._raw_hid_write([0x5D, 0x00, 0x01, 0x08, 0x00, hr_fmt, 0x05])
        time.sleep(0.05)

        # Sync RTC to system time
        self._sync_clock(fmt_24h)
        time.sleep(0.05)

        # Switch to clock mode (EC 51 08 00 HR_FMT)
        self._raw_hid_write([_CMD_SWITCH_DISPLAY_MODE, _DISPLAY_MODE_CLOCK, 0x00, hr_fmt])
        _LOGGER.info("switched to clock mode (%s)", "24h" if fmt_24h else "12h")

    def _sync_clock(self, fmt_24h: bool = True):
        """Set the device RTC to the current system time (BCD encoded).

        Packet format verified against live hardware (S750, PID 0x1ADA).
        Uses ryujin.py prefix layout + BCD time values.
        """
        t = time.localtime()
        hr_fmt = 0x00 if fmt_24h else 0x01
        pm = 0x00 if fmt_24h else (0x01 if t.tm_hour > 11 else 0x00)

        def bcd(val):
            return ((val // 10) << 4) | (val % 10)

        hour = t.tm_hour
        if not fmt_24h:
            hour = hour % 12
            if hour == 0:
                hour = 12

        self._raw_hid_write(
            [
                _CMD_SET_CLOCK,
                0x00,
                0x00,
                0x08,
                0x00,
                hr_fmt,
                bcd(hour),
                bcd(t.tm_min),
                bcd(t.tm_sec),
                pm,
                0x01,
            ]
        )
        _LOGGER.debug("synced RTC to %02d:%02d:%02d", t.tm_hour, t.tm_min, t.tm_sec)

    def _set_screen_hw_monitor(self, **kwargs):
        """Switch to hardware monitor mode showing live sensor data.

        Keyword arguments:
            style: 'galactic', 'cyberpunk', or 'custom' (default: 'custom')
            bg_color: (r, g, b) tuple for background (default: black)
            text_color: (r, g, b) tuple for text (default: white)
        """
        # Read sensors BEFORE switching to raw USB (while hidapi is still open)
        try:
            liquid_temp, pump_speed, pump_fan_speed = self._get_cooler_status()
        except Exception:
            liquid_temp, pump_speed, pump_fan_speed = 0, 0, 0

        style = kwargs.get("style", "custom")
        bg_r, bg_g, bg_b = kwargs.get("bg_color", (0, 0, 0))
        txt_r, txt_g, txt_b = kwargs.get("text_color", (255, 255, 255))

        style_byte = _HW_MONITOR_STYLES.get(style, 0x02)

        # Set HW monitor layout (EC 52)
        self._raw_hid_write(
            [
                _CMD_SET_HW_MONITOR_LAYOUT,
                style_byte,
                0x02,
                0x02,
                0x00,
                bg_r,
                bg_g,
                bg_b,
                0xFF,
                txt_r,
                txt_g,
                txt_b,
                0xFF,
                txt_r,
                txt_g,
                txt_b,
                0xFF,
                txt_r,
                txt_g,
                txt_b,
                0xFF,
                txt_r,
                txt_g,
                txt_b,
                0xFF,
            ]
        )

        # Switch to HW monitor mode
        self._switch_display_mode(_DISPLAY_MODE_HW_MONITOR)

        # Send sensor readings
        lines = [
            ("Liquid Temp", f"{liquid_temp:.1f}C"),
            ("Pump", f"{pump_speed}RPM"),
            ("Fan", f"{pump_fan_speed}RPM"),
        ]
        for i, (label, value) in enumerate(lines):
            self._set_hw_monitor_string(i, label, value)

        _LOGGER.info("switched to HW monitor mode (style=%s)", style)

    def _set_hw_monitor_string(self, index: int, label: str, value: str):
        """Send EC 53 to set a HW monitor line's label and value."""
        label_bytes = label.encode("utf-8", errors="replace")[:18]
        label_padded = list(label_bytes) + [0] * (18 - len(label_bytes))

        value_bytes = value.encode("utf-8", errors="replace")[:12]
        value_padded = list(value_bytes) + [0] * (12 - len(value_bytes))

        self._raw_hid_write([_CMD_SET_HW_MONITOR_STRING, index] + label_padded + value_padded)

    def _set_brightness(self, brightness: int):
        """Set LCD brightness (0-100%)."""
        brightness = clamp(brightness, 0, 100)
        self._set_display_option(brightness=brightness)
        _LOGGER.info("set brightness to %d%%", brightness)

    def _set_display_option(self, brightness=None, orientation=None):
        """Send EC 5C 01 to set display options.

        Verified from ITCM firmware handler at 0x00EC:
          payload[0] = 0x01 (set config sub-command)
          payload[1] = display_type
          payload[2] = mode_byte
          payload[3] = orientation
          payload[4] = (skipped)
          payload[5] = brightness
        """
        brt = brightness if brightness is not None else 30
        orient = orientation if orientation is not None else 0

        self._raw_hid_write(
            [
                _CMD_SET_DISPLAY_OPTION,
                0x01,
                0x00,
                0x00,
                orient,
                0x00,
                brt,
            ]
        )

    def _request(self, request_header: int, response_header: int) -> List[int]:
        self.device.clear_enqueued_reports()
        self._write([_PREFIX, request_header])
        return self._read(response_header)

    def _read(self, expected_header=None) -> List[int]:
        msg = self.device.read(_REPORT_LENGTH)

        if msg[0] != _PREFIX:
            raise ExpectationNotMet("Unexpected report prefix")
        if expected_header is not None and msg[1] != expected_header:
            raise ExpectationNotMet("Unexpected report header")

        return msg

    def _write(self, data: List[int]):
        self.device.write(rpadlist(data, _REPORT_LENGTH, 0))
