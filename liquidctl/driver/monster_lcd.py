"""liquidctl driver for the Monster/AIC AIO LCD controller.

Copyright Orçun Ulutaş and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

from __future__ import annotations

import json
import logging
import time

import hid as _libusb_hidapi

import liquidctl.driver.usb as _usb
from liquidctl.driver.base import BaseBus
from liquidctl.driver.usb import HidapiDevice, UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_PROTOCOL_VERSION = 1
_FRAME_DELIMITER = 0x5A
_ESCAPE_MARKER = 0x5B
_ESCAPED_DELIMITER = 0x01
_ESCAPED_ESCAPE = 0x02
_HID_REPORT_ID = 0x00
_MAX_FRAME_LENGTH = 0xFFFF
_MAX_SEQUENCE = 0x7FFFFFFF
_VENDOR_ID = 0x1D6B
_PRODUCT_ID = 0x0130

_PREFERRED_HIDAPI = _usb.hid
_LIBUSB_HIDAPI = _libusb_hidapi

_NO_BODY = object()
_METHODS = {"GET", "POST", "STATE", "DELETE"}
_ORIENTATIONS = {0, 90, 180, 270}


def _frame_checksum(payload: bytes) -> int:
    total_length = len(payload) + 5
    if total_length > _MAX_FRAME_LENGTH:
        raise ValueError(f"payload is too large: {len(payload)} bytes")
    length_bytes = total_length.to_bytes(2, "big")
    return (sum(length_bytes) + sum(payload)) & 0xFF


def _escape_frame(data: bytes) -> bytes:
    escaped = bytearray()
    for value in data:
        if value == _FRAME_DELIMITER:
            escaped.extend((_ESCAPE_MARKER, _ESCAPED_DELIMITER))
        elif value == _ESCAPE_MARKER:
            escaped.extend((_ESCAPE_MARKER, _ESCAPED_ESCAPE))
        else:
            escaped.append(value)
    return bytes(escaped)


def _pack_frame(payload: bytes) -> bytes:
    total_length = len(payload) + 5
    if total_length > _MAX_FRAME_LENGTH:
        raise ValueError(f"payload is too large: {len(payload)} bytes")
    length_bytes = total_length.to_bytes(2, "big")
    inner = length_bytes + payload + bytes((_frame_checksum(payload),))
    return bytes((_FRAME_DELIMITER,)) + _escape_frame(inner) + bytes((_FRAME_DELIMITER,))


def _build_request(method: str, command: str, sequence: int, date_ms: int, body=_NO_BODY) -> bytes:
    method = method.upper()
    if method not in _METHODS:
        raise ValueError(f"unsupported method: {method}")
    if not command or any(character.isspace() for character in command):
        raise ValueError("command cannot be empty or contain whitespace")

    headers = [("SeqNumber", str(sequence)), ("Date", str(date_ms))]
    body_bytes = b""
    if body is not _NO_BODY:
        body_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers.extend((("ContentType", "json"), ("ContentLength", str(len(body_bytes)))))

    head = f"{method} {command} {_PROTOCOL_VERSION}\r\n"
    head += "".join(f"{key}={value}\r\n" for key, value in headers)
    head += "\r\n"
    return head.encode("utf-8") + body_bytes


def _brightness_to_device(value: int) -> int:
    """Map 0–100% to the observed firmware range 10–100."""

    value = clamp(value, 0, 100)
    return (9 * value + 105) // 10


class MonsterLcd(UsbHidDriver):
    """Driver for the LCD controller in the Monster Tulpar TD3 AIO."""

    _MATCHES = [
        (_VENDOR_ID, _PRODUCT_ID, "Monster Tulpar TD3 AIO LCD", {}),
    ]

    def __init__(self, device, description, **kwargs):
        self._time = kwargs.pop("_time", time.time)
        self._sleep = kwargs.pop("_sleep", time.sleep)
        super().__init__(device, description, **kwargs)
        self._sequence = 0

    def initialize(self, startup_gap=0.05, **kwargs):
        """Synchronize with the controller and request that the LCD wake."""

        if startup_gap < 0:
            raise ValueError("startup gap cannot be negative")

        self.device.clear_enqueued_reports()
        commands = (
            ("POST", "conn", _NO_BODY),
            ("POST", "power", {}),
            ("STATE", "all", _NO_BODY),
            ("POST", "power", {"event": "resume"}),
        )
        for index, (method, command, body) in enumerate(commands):
            self._send(method, command, body)
            if startup_gap and index + 1 < len(commands):
                self._sleep(startup_gap)
        return []

    def get_status(self, **kwargs):
        """Return no status; controller responses are optional and not yet decoded."""

        _LOGGER.info("no status available")
        return []

    def keep_alive(self):
        """Send one keep-alive cycle and return the allocated sequence numbers."""

        self.device.clear_enqueued_reports()
        return [
            self._send("POST", "power", {"event": "resume"}),
            self._send("STATE", "all"),
        ]

    def set_screen(self, channel, mode, value, **kwargs):
        """Set LCD power state, brightness, or orientation.

        Supported modes are ``wake``, ``keep-alive``, ``brightness`` and
        ``orientation``.  The controller needs a keep-alive cycle about once
        per second while the host is awake.
        """

        if channel.lower() != "lcd":
            raise ValueError("only the 'lcd' channel is supported")

        mode = mode.lower()
        if mode == "wake":
            self._require_no_value(mode, value)
            return self._send("POST", "power", {"event": "resume"})
        if mode in ("keep-alive", "keepalive"):
            self._require_no_value(mode, value)
            return self.keep_alive()
        if mode == "brightness":
            brightness = self._parse_int(mode, value)
            return self._send("POST", "brightness", {"value": _brightness_to_device(brightness)})
        if mode == "orientation":
            orientation = self._parse_int(mode, value)
            if orientation not in _ORIENTATIONS:
                raise ValueError("orientation must be one of 0, 90, 180 or 270")
            return self._send("POST", "rotate", {"degree": orientation})

        raise ValueError(
            "unsupported screen mode; expected wake, keep-alive, brightness or orientation"
        )

    def set_color(self, channel, mode, colors, **kwargs):
        raise NotSupportedByDevice()

    def set_speed_profile(self, channel, profile, **kwargs):
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        raise NotSupportedByDevice()

    @staticmethod
    def _parse_int(mode, value):
        if value is None:
            raise ValueError(f"screen mode '{mode}' requires a value")
        try:
            return int(value)
        except (TypeError, ValueError) as err:
            raise ValueError(f"screen mode '{mode}' requires an integer value") from err

    @staticmethod
    def _require_no_value(mode, value):
        if value is not None:
            raise ValueError(f"screen mode '{mode}' does not accept a value")

    def _next_sequence(self):
        sequence = self._sequence
        self._sequence = 1 if sequence >= _MAX_SEQUENCE else sequence + 1
        return sequence

    def _send(self, method, command, body=_NO_BODY):
        sequence = self._next_sequence()
        payload = _build_request(
            method,
            command,
            sequence,
            int(self._time() * 1000),
            body,
        )
        report = bytes((_HID_REPORT_ID,)) + _pack_frame(payload)
        self.device.write(report)
        return sequence


class _MonsterLcdLibusbHidapiBus(BaseBus):
    """Find the controller when Linux hidraw does not expose its HID interface."""

    def find_devices(
        self,
        vendor=None,
        product=None,
        bus=None,
        address=None,
        usb_port=None,
        **kwargs,
    ):
        if _PREFERRED_HIDAPI is _LIBUSB_HIDAPI:
            return
        if (vendor and vendor != _VENDOR_ID) or (product and product != _PRODUCT_ID):
            return

        # Avoid yielding a duplicate when the preferred hidraw backend can
        # already enumerate this controller.
        if next(HidapiDevice.enumerate(_PREFERRED_HIDAPI, _VENDOR_ID, _PRODUCT_ID), None):
            return

        _LOGGER.debug("probing Monster LCD through the libusb hidapi fallback")
        for handle in HidapiDevice.enumerate(_LIBUSB_HIDAPI, _VENDOR_ID, _PRODUCT_ID):
            if bus and handle.bus != bus:
                continue
            if address and handle.address != address:
                continue
            if usb_port and handle.port != usb_port:
                continue
            yield from MonsterLcd.probe(
                handle,
                vendor=vendor,
                product=product,
                **kwargs,
            )
