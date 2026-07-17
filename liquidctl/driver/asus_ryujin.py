"""liquidctl driver for the ASUS Ryujin II and Ryujin III EXTREME / 360 liquid coolers.

Copyright Florian Freudiger and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import sys
import time
from itertools import chain
from typing import List

if sys.platform == "win32":
    from winusbcdc import WinUsbPy

from liquidctl.driver.usb import PyUsbDevice, UsbHidDriver
from liquidctl.driver.asus_ryujin_lcd import (
    _LCD_FRAME_SIZE,
    _iter_lcd_animation,
    _iter_lcd_background,
    _load_lcd_static_background,
    _load_lcd_stats_config,
    _prepare_lcd_frame,
    _read_lcd_custom_stats,
    _render_lcd_stats,
)
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

# Command headers that don't need a response
_CMD_SET_COOLER_SPEED = 0x1A
_CMD_SET_CONTROLLER_SPEED = 0x21

_STATUS_FIRMWARE = "Firmware version"
_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_COOLER_FAN_SPEED = "Pump fan speed"
_STATUS_COOLER_FAN_DUTY = "Pump fan duty"
_STATUS_CONTROLLER_FAN_SPEED = "External fan {} speed"
_STATUS_CONTROLLER_FAN_DUTY = "External fan duty"

_LCD_PRODUCT_ID = 0x1BCB
_LCD_RAW_FRAMEBUFFER_MODE = 0x20
_LCD_BULK_OUT_ENDPOINT = 0x02
_LCD_TRANSFER_TIMEOUT_MS = 10_000


class AsusRyujin(UsbHidDriver):
    """ASUS Ryujin II & Ryujin III Extreme / 360 / White Edition liquid coolers."""

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
        bulk_device=None,
        **kwargs,
    ):
        super().__init__(device, description, **kwargs)

        self._fan_count = fan_count
        self._pump_speed_offset = pump_speed_offset
        self._pump_fan_speed_offset = pump_fan_speed_offset
        self._temp_offset = temp_offset
        self._duty_channel = duty_channel
        self._bulk_device = bulk_device

    def initialize(self, **kwargs):
        msg = self._request(*_REQUEST_GET_FIRMWARE)
        return [(_STATUS_FIRMWARE, "".join(map(chr, msg[3:18])), "")]

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

    def set_screen(self, channel, mode, value, interval=None, **kwargs):
        """Set the Ryujin III Extreme LCD image.

        Supported channels, modes and values:

        | Channel | Mode | Value |
        | --- | --- | --- |
        | `lcd` | `static` | path to image |
        | `lcd` | `gif` | path to animated GIF (plays until interrupted) |
        | `lcd` | `stats` | path to JSON configuration, or RGB hex shorthand |
        """
        if self.product_id != _LCD_PRODUCT_ID:
            raise NotSupportedByDriver()
        if channel.lower() != "lcd":
            raise ValueError(f"invalid channel: {channel}")
        mode = mode.lower()
        if mode not in ("static", "gif", "stats"):
            raise ValueError(f"invalid mode: {mode}")

        content = self._prepare_lcd_content(mode, value, interval)
        bulk_device = self._open_bulk_device()
        try:
            self._switch_to_raw_framebuffer_mode()
            if mode == "static":
                self._send_lcd_frame(bulk_device, content)
            elif mode == "gif":
                self._play_lcd_animation(bulk_device, content)
            else:
                self._display_lcd_statistics(bulk_device, *content)
        finally:
            self._close_bulk_device(bulk_device)

    def _prepare_lcd_content(self, mode, value, interval):
        try:
            if mode == "static":
                return _prepare_lcd_frame(value)
            if mode == "gif":
                return self._load_lcd_animation(value)

            config = _load_lcd_stats_config(value, interval)
            static_background = (
                _load_lcd_static_background(config["background"])
                if config["background"]
                else None
            )
            if config["background"] and static_background is None:
                return config, None, self._load_lcd_background(value=config["background"])
            return config, static_background, None
        except (OSError, StopIteration, ValueError) as err:
            raise ValueError(f"invalid {mode} configuration: {err}") from err

    @staticmethod
    def _load_lcd_animation(path):
        frames = _iter_lcd_animation(path)
        first_frame = next(frames)
        return chain((first_frame,), frames)

    @staticmethod
    def _load_lcd_background(value):
        frames = _iter_lcd_background(value)
        first_frame = next(frames)
        return chain((first_frame,), frames)

    def _play_lcd_animation(self, bulk_device, frames):
        try:
            for frame, duration in frames:
                self._send_lcd_frame(bulk_device, frame)
                time.sleep(duration)
        except KeyboardInterrupt:
            _LOGGER.debug("stopped Ryujin III Extreme LCD GIF playback")

    def _display_lcd_statistics(self, bulk_device, config, static_background, background_frames):
        try:
            if background_frames is not None:
                self._display_lcd_statistics_with_animation(bulk_device, config, background_frames)
            else:
                self._display_lcd_statistics_with_static_background(
                    bulk_device, config, static_background
                )
        except KeyboardInterrupt:
            _LOGGER.debug("stopped Ryujin III Extreme LCD statistics display")

    def _display_lcd_statistics_with_animation(self, bulk_device, config, background_frames):
        page = 0
        status = self.get_status()
        custom_values = _read_lcd_custom_stats(config, page)
        next_page = time.monotonic() + config["interval"]

        for background, duration in background_frames:
            now = time.monotonic()
            if now >= next_page:
                page += 1
                status = self.get_status()
                custom_values = _read_lcd_custom_stats(config, page)
                next_page += config["interval"]
            self._send_lcd_frame(
                bulk_device,
                _render_lcd_stats(
                    status,
                    config,
                    page,
                    max(next_page - now, 0),
                    background,
                    custom_values,
                ),
            )
            time.sleep(duration)

    def _display_lcd_statistics_with_static_background(self, bulk_device, config, background):
        page = 0
        while True:
            custom_values = _read_lcd_custom_stats(config, page)
            next_page = time.monotonic() + config["interval"]
            while True:
                now = time.monotonic()
                if now >= next_page:
                    break
                status = self.get_status()
                self._send_lcd_frame(
                    bulk_device,
                    _render_lcd_stats(
                        status,
                        config,
                        page,
                        next_page - now,
                        background,
                        custom_values,
                    ),
                )
                time.sleep(min(1, next_page - now))
            page += 1

    def _open_bulk_device(self):
        if self._bulk_device is not None:
            bulk_device = self._bulk_device
        elif sys.platform == "win32":
            bulk_device = WinUsbPy()
            if not self._find_winusb_device(bulk_device):
                raise NotSupportedByDriver("could not find the LCD bulk interface")
        else:
            bulk_device = next(
                (
                    candidate
                    for candidate in PyUsbDevice.enumerate(self.vendor_id, self.product_id)
                    if candidate.serial_number == self.serial_number
                ),
                None,
            )
            if bulk_device is None:
                raise NotSupportedByDriver("could not find the LCD bulk interface")

        if sys.platform != "win32":
            bulk_device.open()
            bulk_device.claim()
        return bulk_device

    def _close_bulk_device(self, bulk_device):
        if sys.platform == "win32":
            bulk_device.close_winusb_device()
        else:
            bulk_device.close()

    def _find_winusb_device(self, bulk_device):
        for candidate in bulk_device.list_usb_devices(
            deviceinterface=True, present=True, findparent=True
        ):
            if (
                f"vid_{self.vendor_id:x}&pid_{self.product_id:x}" in candidate.path
                and candidate.parent
                and self.serial_number in candidate.parent
            ):
                bulk_device.init_winusb_device_with_path(candidate.path)
                return True
        return False

    def _switch_to_raw_framebuffer_mode(self):
        reply = self._request(0xD0, 0x50)
        # Reapply the mode even when it is already selected, avoiding display
        # state carried over from an earlier raw-frame session.
        time.sleep(0.1)
        self._write([_PREFIX, 0x51, _LCD_RAW_FRAMEBUFFER_MODE, reply[6], reply[7]])
        time.sleep(0.1)

    def _announce_framebuffer_length(self, length):
        self._write([_PREFIX, 0x7F, 0x03, *length.to_bytes(4, byteorder="little")])

    def _send_lcd_frame(self, bulk_device, frame):
        assert len(frame) == _LCD_FRAME_SIZE
        self._announce_framebuffer_length(len(frame))
        written = bulk_device.write(
            _LCD_BULK_OUT_ENDPOINT, frame, timeout=_LCD_TRANSFER_TIMEOUT_MS
        )
        if written is not None and written != len(frame):
            raise RuntimeError(f"short LCD bulk write: {written} of {len(frame)} bytes")

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
