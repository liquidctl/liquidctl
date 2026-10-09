"""Support for the Cooler Master HAF 700 EVO IRIS LCD.

The LCD is accessed through a TCP connection forwarded over Android Debug
Bridge (ADB).  It supports native telemetry pages and image or video
presentation through the display's command interface.

Copyright Daniel Clark and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import socket
import struct
import subprocess
import time
from dataclasses import asdict, dataclass, replace
from numbers import Real
from pathlib import Path
from typing import Any, Mapping

from liquidctl.driver.usb import UsbDriver
from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver
from liquidctl.util import LazyHexRepr

_LOGGER = logging.getLogger(__name__)

_SYNC = b"\x80\x00\x01"

_CMD_SELECT_PAGE = 0x12
_CMD_UPDATE_PAGE = 0x15
_CMD_STORAGE_INFO = 0xF0
_CMD_DELETE_FILE = 0xF2
_CMD_FILE_EXISTS = 0xF3
_CMD_BEGIN_UPLOAD = 0xF5
_CMD_FINISH_UPLOAD = 0xF6
_CMD_UPLOAD_CHUNK = 0xF7

_MAGICBOX_PORT = 9900
_SOCKET_TIMEOUT = 3.0
_RECONNECT_ATTEMPTS = 6
_RECONNECT_DELAY = 0.5
_UPLOAD_CHUNK_SIZE = 16 * 1024
_MEDIA_MODE_ID = 17
_MEDIA_MODE_NAMES = {
    "image",
    "media",
    "video",
    "custom-image",
    "custom_image",
    "custom-media",
    "custom_media",
    "custom-video",
    "custom_video",
}
_MEDIA_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".mp4"}
_MEDIA_RAM_DIR = "/data/data/com.magic.box/files/liquidctl"
_MEDIA_RAM_PREFIX = "liquidctl/"
_MEDIA_MAX_FILE_SIZE = 16 * 1024 * 1024
_MEDIA_TMPFS_SIZE_MIB = 32
_MEDIA_TMPFS_SIZE_BYTES = _MEDIA_TMPFS_SIZE_MIB * 1024 * 1024
_MEDIA_TMPFS_SIZE = f"{_MEDIA_TMPFS_SIZE_MIB}m"
_MEDIA_TMPFS_OPTIONS = f"size={_MEDIA_TMPFS_SIZE},mode=700,uid=1000,gid=1000"


@dataclass(frozen=True)
class IrisTelemetryMode:
    """Description of a built-in hardware-monitoring page."""

    id: int
    name: str
    unit: str
    minimum: int
    maximum: int
    description: str
    aliases: tuple[str, ...] = ()


# Each mode selects a built-in page, including its labels and artwork.
_TELEMETRY_MODES = (
    IrisTelemetryMode(
        1,
        "cpu-frequency",
        "MHz",
        0,
        9999,
        "CPU frequency; MagicBox renders the native CPU-frequency page",
        ("cpu-freq", "cpu_freq", "cpu_frequency"),
    ),
    IrisTelemetryMode(
        2,
        "gpu-frequency",
        "MHz",
        0,
        9999,
        "GPU frequency; MagicBox renders the native GPU-frequency page",
        ("gpu-freq", "gpu_freq", "gpu_frequency"),
    ),
    IrisTelemetryMode(
        3,
        "cpu-temperature",
        "°C",
        0,
        100,
        "CPU temperature; MagicBox renders the native CPU-temperature page",
        ("cpu-temp", "cpu_temp", "cpu_temperature"),
    ),
    IrisTelemetryMode(
        4,
        "gpu-temperature",
        "°C",
        0,
        100,
        "GPU temperature; MagicBox renders the native GPU-temperature page",
        ("gpu-temp", "gpu_temp", "gpu_temperature"),
    ),
    IrisTelemetryMode(
        5,
        "cpu-usage",
        "%",
        0,
        100,
        "CPU utilization",
        ("cpu_usage",),
    ),
    IrisTelemetryMode(
        6,
        "gpu-usage",
        "%",
        0,
        100,
        "GPU utilization",
        ("gpu_usage",),
    ),
    IrisTelemetryMode(
        7,
        "memory-usage",
        "%",
        0,
        100,
        "System memory utilization",
        ("memory_usage", "ram-usage", "ram_usage"),
    ),
    IrisTelemetryMode(
        8,
        "cpu-fan",
        "rpm",
        0,
        9999,
        "CPU Fan native page",
        ("cpu_fan",),
    ),
    IrisTelemetryMode(
        9,
        "case-fan-1",
        "rpm",
        0,
        9999,
        "Case Fan 1 native page",
        ("case-fan1", "case_fan1", "case_fan_1"),
    ),
    IrisTelemetryMode(
        10,
        "case-fan-2",
        "rpm",
        0,
        9999,
        "Case Fan 2 native page",
        ("case-fan2", "case_fan2", "case_fan_2"),
    ),
    IrisTelemetryMode(
        11,
        "case-fan-3",
        "rpm",
        0,
        9999,
        "Case Fan 3 native page",
        ("case-fan3", "case_fan3", "case_fan_3"),
    ),
    IrisTelemetryMode(
        12,
        "case-fan-4",
        "rpm",
        0,
        9999,
        "Case Fan 4 native page",
        ("case-fan4", "case_fan4", "case_fan_4"),
    ),
    IrisTelemetryMode(
        13,
        "case-fan-5",
        "rpm",
        0,
        9999,
        "Case Fan 5 native page",
        ("case-fan5", "case_fan5", "case_fan_5"),
    ),
)

_MODE_BY_NAME: dict[str, IrisTelemetryMode] = {}
for _mode in _TELEMETRY_MODES:
    _MODE_BY_NAME[_mode.name] = _mode
    for _alias in _mode.aliases:
        _MODE_BY_NAME[_alias] = _mode


@dataclass(frozen=True)
class IrisPageSettings:
    """Settings serialized for LCD page selection and updates."""

    mode: int
    value: int
    minimum: int
    maximum: int
    scroll: int = 0
    reserved: bytes = b"\x00\x00\x00"
    round_speed: int = 0
    text_color: int = 0xFFFFFFFF
    text: str = ""
    background_state: int = 0
    background_color: int = 0xFF000000
    image_name: str = ""
    media_name: str = ""

    def encode(self) -> bytes:
        _check_u8("mode", self.mode)
        _check_u16("value", self.value)
        _check_u16("minimum", self.minimum)
        _check_u16("maximum", self.maximum)
        _check_u8("scroll", self.scroll)
        _check_u8("round_speed", self.round_speed)
        _check_u8("background_state", self.background_state)

        if len(self.reserved) != 3:
            raise ValueError("reserved must contain exactly 3 bytes")

        _check_u32("text_color", self.text_color)
        _check_u32("background_color", self.background_color)

        text = _encode_short_string("text", self.text)
        image_name = _encode_short_string("image_name", self.image_name)
        media_name = _encode_short_string("media_name", self.media_name)

        payload = bytearray()
        payload.append(self.mode)
        payload += self.value.to_bytes(2, "big")
        payload += self.minimum.to_bytes(2, "big")
        payload += self.maximum.to_bytes(2, "big")
        payload.append(self.scroll)
        payload += self.reserved
        payload.append(self.round_speed)
        payload += self.text_color.to_bytes(4, "big")
        payload.append(len(text))
        payload += text
        payload.append(self.background_state)
        payload += self.background_color.to_bytes(4, "big")
        payload.append(len(image_name))
        payload += image_name
        payload.append(len(media_name))
        payload += media_name

        return bytes(payload)


def _check_u8(name: str, value: int) -> None:
    if not 0 <= value <= 0xFF:
        raise ValueError(f"{name} must be in range 0..255")


def _check_u16(name: str, value: int) -> None:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"{name} must be in range 0..65535")


def _check_u32(name: str, value: int) -> None:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"{name} must be in range 0..0xffffffff")


def _encode_short_string(name: str, value: str) -> bytes:
    encoded = value.encode("utf-8")
    if len(encoded) > 0xFF:
        raise ValueError(f"{name} must be <=255 encoded bytes")
    return encoded


def _packet(command: int, payload: bytes = b"") -> bytes:
    _check_u8("command", command)
    if len(payload) > 0xFFFF:
        raise ValueError("payload must be <=65535 bytes")
    return bytes([command]) + _SYNC + len(payload).to_bytes(2, "big") + payload


def _recvn(sock: socket.socket, length: int) -> bytes:
    data = bytearray()
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("connection to MagicBox was closed by the IRIS panel")
        data += chunk
    return bytes(data)


def _recv_packet(sock: socket.socket) -> tuple[int, bytes]:
    header = _recvn(sock, 6)
    if header[1:4] != _SYNC:
        raise RuntimeError(f"invalid MagicBox sync: {header.hex(' ')}")
    payload_length = int.from_bytes(header[4:6], "big")
    return header[0], _recvn(sock, payload_length) if payload_length else b""


def _normalise_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


_FIELD_ALIASES = {
    "min": "minimum",
    "max": "maximum",
    "roundspeed": "round_speed",
    "textcolor": "text_color",
    "backgroundstate": "background_state",
    "backgroundcolor": "background_color",
    "imagename": "image_name",
    "medianame": "media_name",
}

_POSITIONAL_FIELDS = (
    "value",
    "minimum",
    "maximum",
    "scroll",
    "reserved",
    "round_speed",
    "text_color",
    "text",
    "background_state",
    "background_color",
    "image_name",
    "media_name",
    "action",
)

_ALLOWED_FIELDS = set(_POSITIONAL_FIELDS)


def _parse_color(value: Any) -> int:
    if isinstance(value, int):
        _check_u32("color", value)
        return value

    text = str(value).strip().lower()
    if text.startswith("#"):
        text = text[1:]
    if text.startswith("0x"):
        text = text[2:]
    if len(text) == 6:
        text = "ff" + text
    if len(text) != 8:
        raise ValueError("color must be RRGGBB or AARRGGBB")
    try:
        parsed = int(text, 16)
    except ValueError as err:
        raise ValueError(f"invalid color {value!r}") from err
    _check_u32("color", parsed)
    return parsed


def _parse_reserved(value: Any) -> bytes:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, bytearray):
        data = bytes(value)
    else:
        text = str(value).strip().replace(" ", "").replace(":", "")
        if text.startswith("0x"):
            text = text[2:]
        if len(text) != 6:
            raise ValueError("reserved must be exactly three bytes, e.g. 000000")
        try:
            data = bytes.fromhex(text)
        except ValueError as err:
            raise ValueError("reserved must be hexadecimal") from err

    if len(data) != 3:
        raise ValueError("reserved must contain exactly three bytes")
    return data


def _coerce_integer(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    if isinstance(value, Real):
        return int(round(value))
    text = str(value).strip()
    try:
        return int(text, 0)
    except ValueError:
        try:
            return int(round(float(text)))
        except ValueError as err:
            raise ValueError(f"{name} must be numeric, got {value!r}") from err


def _coerce_bool(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"{name} must be boolean, got {value!r}")


def _parse_value_spec(value: Any) -> dict[str, Any]:
    """Parse a set_screen value into a normalised option dictionary.

    Accepted forms:

      42

      "42"

      "42;minimum=0;maximum=100;text-color=ffffffff;action=auto"

      Positional:
      "42;0;100;0;000000;0;ffffffff;;0;ff000000;;;auto"

      JSON:
      '{"value":42,"minimum":0,"maximum":100,"action":"auto"}'

      Python mapping (best for programmatic callers such as CoolerControl):
      {"value": 42, "minimum": 0, "maximum": 100, "action": "auto"}
    """

    if isinstance(value, Mapping):
        raw = dict(value)
    elif isinstance(value, Real) and not isinstance(value, bool):
        raw = {"value": value}
    elif value is None:
        raise ValueError("a telemetry value is required")
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("a telemetry value is required")

        if text.startswith("{"):
            try:
                raw = json.loads(text)
            except json.JSONDecodeError as err:
                raise ValueError(f"invalid JSON screen value: {err}") from err
            if not isinstance(raw, dict):
                raise ValueError("screen JSON value must be an object")
        elif ";" not in text and "=" not in text:
            raw = {"value": text}
        else:
            parts = text.split(";")
            raw = {}

            # Key/value form; an optional first bare token is the current value.
            has_key_values = any("=" in part for part in parts)
            if has_key_values:
                for index, part in enumerate(parts):
                    if part == "":
                        continue
                    if "=" not in part:
                        if index == 0:
                            raw["value"] = part
                            continue
                        raise ValueError(
                            "bare tokens are only allowed as the first value in key/value syntax"
                        )
                    key, item = part.split("=", 1)
                    raw[key] = item
            else:
                if len(parts) > len(_POSITIONAL_FIELDS):
                    raise ValueError(
                        f"too many positional LCD fields; maximum is {len(_POSITIONAL_FIELDS)}"
                    )
                raw = {field: item for field, item in zip(_POSITIONAL_FIELDS, parts) if item != ""}

    normalised: dict[str, Any] = {}
    for key, item in raw.items():
        norm = _normalise_key(str(key))
        norm = _FIELD_ALIASES.get(norm, norm)
        if norm not in _ALLOWED_FIELDS:
            raise ValueError(f"unknown HAF700 LCD field {key!r}")
        normalised[norm] = item

    if "value" not in normalised:
        raise ValueError("screen value must include 'value'")

    return normalised


def _parse_media_spec(value: Any) -> dict[str, Any]:
    """Parse a custom-media request.

    ``value`` can be a local path or a mapping with ``path`` and optional
    ``cleanup`` (default true).
    """

    if isinstance(value, Mapping):
        raw = dict(value)
    elif value is None:
        raise ValueError("a media path is required")
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("a media path is required")
        raw = {"path": text}

    if "path" not in raw:
        raise ValueError("media value must include 'path'")

    return {
        "path": Path(str(raw["path"])).expanduser(),
        "cleanup": _coerce_bool("cleanup", raw.get("cleanup", True)),
    }


def _normalise_media_extension(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in _MEDIA_SUPPORTED_EXTENSIONS:
        expected = ", ".join(sorted(_MEDIA_SUPPORTED_EXTENSIONS))
        raise ValueError(f"unsupported HAF700 media type {suffix!r}; expected one of: {expected}")
    return ".jpg" if suffix == ".jpeg" else suffix


class Haf700Iris(UsbDriver):
    """Cooler Master HAF 700 EVO IRIS LCD."""

    _MATCHES = [
        (
            0x2516,
            0x01C1,
            "Cooler Master HAF 700 EVO IRIS",
            {},
        ),
    ]

    # Public metadata intended to make integrations such as CoolerControl able
    # to build a complete native-mode UI without duplicating protocol IDs.
    SCREEN_CHANNEL = "lcd"
    SCREEN_RESOLUTION = (480, 480)
    TELEMETRY_MODES = _TELEMETRY_MODES
    SCREEN_FIELDS = {
        "value": "u16 current value",
        "minimum": "u16 scale/range minimum",
        "maximum": "u16 scale/range maximum",
        "scroll": "u8 MagicBox scroll field",
        "reserved": "3-byte raw reserved field; default 000000",
        "round_speed": "u8 MagicBox round-speed field",
        "text_color": "AARRGGBB color",
        "text": "UTF-8 text, <=255 encoded bytes",
        "background_state": "u8 background state",
        "background_color": "AARRGGBB color",
        "image_name": "UTF-8 image name, <=255 encoded bytes",
        "media_name": "UTF-8 media name, <=255 encoded bytes",
        "action": "auto, select (0x12), or update (0x15)",
    }

    def __init__(
        self,
        device,
        description,
        adb="adb",
        socket_timeout=_SOCKET_TIMEOUT,
        reconnect_attempts=_RECONNECT_ATTEMPTS,
        reconnect_delay=_RECONNECT_DELAY,
        **kwargs,
    ):
        super().__init__(device, description, **kwargs)
        self._adb_executable = adb
        self._socket_timeout = float(socket_timeout)
        self._reconnect_attempts = int(reconnect_attempts)
        self._reconnect_delay = float(reconnect_delay)

        self._sock: socket.socket | None = None
        self._forward_port: int | None = None
        self._selected_instruction: IrisPageSettings | None = None

    @classmethod
    def get_screen_capabilities(cls) -> dict[str, Any]:
        """Return LCD capability metadata for native pages and custom media.

        This is a driver extension, not currently a standard liquidctl method.
        It is intentionally structured for persistent integrations such as
        CoolerControl.
        """

        return {
            "channel": cls.SCREEN_CHANNEL,
            "resolution": list(cls.SCREEN_RESOLUTION),
            "native_telemetry": True,
            "supports_live_update": True,
            "select_command": _CMD_SELECT_PAGE,
            "update_command": _CMD_UPDATE_PAGE,
            "modes": [asdict(mode) for mode in cls.TELEMETRY_MODES],
            "fields": dict(cls.SCREEN_FIELDS),
            "custom_media": {
                "supported": True,
                "mode": _MEDIA_MODE_ID,
                "aliases": sorted(_MEDIA_MODE_NAMES),
                "formats": ["png", "jpg", "mp4"],
                "max_file_size": _MEDIA_MAX_FILE_SIZE,
                "ram_directory": _MEDIA_RAM_DIR,
                "ram_filename_prefix": _MEDIA_RAM_PREFIX,
                "ram_size": _MEDIA_TMPFS_SIZE_BYTES,
            },
        }

    def connect(self, **kwargs):
        """Connect to the display service through the ADB TCP forward."""

        self._connect_magicbox()
        return self

    def disconnect(self, **kwargs):
        """Close TCP and remove only the ADB forward created by this instance."""

        self._close_socket()
        self._remove_forward()

    def initialize(self, **kwargs):
        block_size, block_count = self._query_space()
        return [
            ("Native telemetry modes", len(self.TELEMETRY_MODES), ""),
            ("LCD width", self.SCREEN_RESOLUTION[0], "px"),
            ("LCD height", self.SCREEN_RESOLUTION[1], "px"),
            ("Storage block size", block_size, "B"),
            ("Storage block count", block_count, ""),
            ("Custom media mode", _MEDIA_MODE_ID, ""),
        ]

    def get_status(self, **kwargs):
        block_size, block_count = self._query_space()
        return [
            ("MagicBox connection", "connected", ""),
            ("Native telemetry modes", len(self.TELEMETRY_MODES), ""),
            ("Storage block size", block_size, "B"),
            ("Storage block count", block_count, ""),
        ]

    def set_screen(self, channel, mode, value, **kwargs):
        """Set a native telemetry page or custom media on the IRIS.

        Native telemetry modes use names such as ``cpu-temperature`` or
        ``case-fan-3``. Their value can be a scalar, a semicolon-delimited CLI
        value, a JSON object string, or a Python mapping. ``action`` controls
        whether the driver selects with 0x12 or updates in place with 0x15.

        Custom media modes (``image``, ``video`` and aliases) accept a local
        PNG/JPEG/MP4 path or a mapping with ``path`` and optional ``cleanup``.
        Media is uploaded to a content-addressed file in the driver's RAM-backed
        media subdirectory, then selected using LCD media mode 17.
        """

        if channel.lower() != self.SCREEN_CHANNEL:
            raise NotSupportedByDevice()

        mode_key = str(mode).strip().lower()
        if mode_key in _MEDIA_MODE_NAMES:
            self._set_media(value)
            return

        mode_info = self._resolve_mode(mode)
        options = _parse_value_spec(value)

        action = str(options.pop("action", "auto")).strip().lower()
        if action not in ("auto", "select", "update"):
            raise ValueError("action must be one of: auto, select, update")

        instruction = self._make_instruction(mode_info, options)

        if action == "select":
            self._select(instruction)
        elif action == "update":
            self._update(instruction)
        elif (
            self._selected_instruction is not None
            and self._selected_instruction.mode == instruction.mode
        ):
            self._update(instruction)
        else:
            self._select(instruction)

    def set_color(self, channel, mode, colors, **kwargs):
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        raise NotSupportedByDevice()

    def set_speed_profile(self, channel, profile, **kwargs):
        raise NotSupportedByDevice()

    @staticmethod
    def _resolve_mode(mode: str) -> IrisTelemetryMode:
        key = str(mode).strip().lower()
        try:
            return _MODE_BY_NAME[key]
        except KeyError as err:
            canonical = ", ".join(item.name for item in _TELEMETRY_MODES)
            raise ValueError(
                f"unknown HAF700 LCD mode {mode!r}; expected one of: {canonical}"
            ) from err

    def _make_instruction(
        self,
        mode_info: IrisTelemetryMode,
        options: Mapping[str, Any],
    ) -> IrisPageSettings:
        # Preserve all presentation/configuration fields when a persistent
        # caller supplies only the changing numeric value for the same page.
        if (
            self._selected_instruction is not None
            and self._selected_instruction.mode == mode_info.id
        ):
            base = self._selected_instruction
        else:
            base = IrisPageSettings(
                mode=mode_info.id,
                value=0,
                minimum=mode_info.minimum,
                maximum=mode_info.maximum,
            )

        updates: dict[str, Any] = {}
        for field, item in options.items():
            if field in (
                "value",
                "minimum",
                "maximum",
                "scroll",
                "round_speed",
                "background_state",
            ):
                updates[field] = _coerce_integer(field, item)
            elif field in ("text_color", "background_color"):
                updates[field] = _parse_color(item)
            elif field == "reserved":
                updates[field] = _parse_reserved(item)
            elif field in ("text", "image_name", "media_name"):
                updates[field] = str(item)
            else:
                raise AssertionError(f"unhandled screen field {field!r}")

        instruction = replace(base, **updates)

        # Validate now, before touching the device.
        instruction.encode()
        return instruction

    def _set_media(self, value: Any) -> None:
        spec = _parse_media_spec(value)
        path = spec["path"]
        cleanup = spec["cleanup"]

        if not path.is_file():
            raise ValueError(f"media path for HAF700 does not exist: {path}")

        extension = _normalise_media_extension(path)
        file_size = path.stat().st_size
        if file_size > _MEDIA_MAX_FILE_SIZE:
            raise ValueError(
                f"media file for HAF700 is too large: {file_size} bytes; "
                f"maximum is {_MEDIA_MAX_FILE_SIZE} bytes"
            )

        data = path.read_bytes()
        if len(data) > _MEDIA_MAX_FILE_SIZE:
            raise ValueError(
                f"media file for HAF700 is too large: {len(data)} bytes; "
                f"maximum is {_MEDIA_MAX_FILE_SIZE} bytes"
            )

        remote_name = f"{_MEDIA_RAM_PREFIX}{hashlib.sha256(data).hexdigest()}{extension}"

        self._ensure_media_tmpfs()
        if not self._file_exists(remote_name):
            self._upload_media(remote_name, data)

        instruction = IrisPageSettings(
            mode=_MEDIA_MODE_ID,
            value=0,
            minimum=0,
            maximum=100,
            media_name=remote_name,
        )
        self._select(instruction)

        if cleanup:
            self._cleanup_liquidctl_media(remote_name)

    def _adb_serial(self) -> str | None:
        # Use the USB serial to select the corresponding ADB device.
        return self.serial_number

    def _adb_command(self, *args: str) -> list[str]:
        command = [self._adb_executable]
        serial = self._adb_serial()
        if serial:
            command += ["-s", serial]
        command += list(args)
        return command

    def _run_adb(
        self,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if shutil.which(self._adb_executable) is None:
            raise NotSupportedByDriver(
                "support for HAF700 IRIS requires the system 'adb' executable"
            )

        command = self._adb_command(*args)
        _LOGGER.debug("running ADB command: %r", command)

        try:
            return subprocess.run(
                command,
                check=check,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as err:
            stderr = (err.stderr or "").strip()
            raise ConnectionError(
                f"ADB command failed ({' '.join(command)}): {stderr or err}"
            ) from err

    def _check_adb_state(self) -> None:
        state = self._run_adb("get-state").stdout.strip()
        if state != "device":
            raise ConnectionError(f"device ADB state is {state!r}, expected 'device'")

    def _create_forward(self) -> None:
        self._remove_forward()
        self._check_adb_state()

        # Modern adb supports tcp:0 and prints the selected local port.  This
        # avoids collisions and supports multiple IRIS devices.
        result = self._run_adb(
            "forward",
            "tcp:0",
            f"tcp:{_MAGICBOX_PORT}",
        )
        selected = result.stdout.strip()
        try:
            port = int(selected, 10)
        except ValueError as err:
            raise ConnectionError(f"could not obtain local ADB tcp:0 port: {selected!r}") from err

        if not 1 <= port <= 65535:
            raise ConnectionError(f"invalid ADB forwarding port {port}")

        self._forward_port = port
        _LOGGER.debug(
            "forwarded HAF700 MagicBox tcp:%d -> tcp:%d",
            port,
            _MAGICBOX_PORT,
        )

    def _remove_forward(self) -> None:
        if self._forward_port is None:
            return

        port = self._forward_port
        self._forward_port = None

        try:
            self._run_adb("forward", "--remove", f"tcp:{port}", check=False)
        except Exception as err:
            _LOGGER.debug("failed to remove HAF700 ADB forward: %s", err)

    def _close_socket(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def _connect_magicbox(self) -> None:
        self._close_socket()

        last_error: Exception | None = None
        for attempt in range(1, self._reconnect_attempts + 1):
            try:
                self._create_forward()
                assert self._forward_port is not None
                sock = socket.create_connection(
                    ("127.0.0.1", self._forward_port),
                    timeout=self._socket_timeout,
                )
                sock.settimeout(self._socket_timeout)
                self._sock = sock
                _LOGGER.debug(
                    "connected to HAF700 MagicBox through localhost:%d",
                    self._forward_port,
                )
                return
            except Exception as err:
                last_error = err
                self._close_socket()
                self._remove_forward()
                if attempt < self._reconnect_attempts:
                    time.sleep(self._reconnect_delay)

        raise ConnectionError(
            f"could not connect to HAF700 MagicBox after "
            f"{self._reconnect_attempts} attempts: {last_error}"
        )

    def _send_once(
        self,
        command: int,
        payload: bytes = b"",
        expect_response: bool = False,
    ) -> tuple[int, bytes] | None:
        if self._sock is None:
            raise ConnectionError("transport socket for MagicBox is not connected")

        packet = _packet(command, payload)
        if command == _CMD_UPLOAD_CHUNK and len(payload) > 64:
            _LOGGER.debug(
                "sending HAF700 command=0x%02x payload=%d bytes",
                command,
                len(payload),
            )
        else:
            _LOGGER.debug("sending HAF700 packet: %r", LazyHexRepr(packet, sep=" "))
        self._sock.sendall(packet)

        if not expect_response:
            return None

        response = _recv_packet(self._sock)
        _LOGGER.debug(
            "received HAF700 packet: %r",
            LazyHexRepr(_packet(response[0], response[1]), sep=" "),
        )
        return response

    def _restore_selected_page(self) -> None:
        if self._selected_instruction is None:
            return

        response = self._send_once(
            _CMD_SELECT_PAGE,
            self._selected_instruction.encode(),
            expect_response=True,
        )
        self._validate_select_ack(response)

    def _send_resilient(
        self,
        command: int,
        payload: bytes = b"",
        expect_response: bool = False,
        restore_before_retry: bool = False,
    ) -> tuple[int, bytes] | None:
        try:
            return self._send_once(command, payload, expect_response)
        except (OSError, ConnectionError, TimeoutError) as first_error:
            _LOGGER.warning("transport reset for HAF700: %s; reconnecting", first_error)

        self._connect_magicbox()

        if restore_before_retry:
            self._restore_selected_page()

        return self._send_once(command, payload, expect_response)

    @staticmethod
    def _validate_select_ack(response: tuple[int, bytes] | None) -> None:
        if response is None:
            raise RuntimeError("missing SELECT_PAGE acknowledgement")

        command, payload = response
        if command != _CMD_SELECT_PAGE or payload:
            raise RuntimeError(
                "unexpected SELECT_PAGE acknowledgement: "
                f"command=0x{command:02x}, payload={payload.hex(' ')}"
            )

    def _select(self, instruction: IrisPageSettings) -> None:
        response = self._send_resilient(
            _CMD_SELECT_PAGE,
            instruction.encode(),
            expect_response=True,
            # We are replacing the page; don't restore the old one first.
            restore_before_retry=False,
        )
        self._validate_select_ack(response)
        self._selected_instruction = instruction

    def _update(self, instruction: IrisPageSettings) -> None:
        self._send_resilient(
            _CMD_UPDATE_PAGE,
            instruction.encode(),
            expect_response=False,
            # Restore the selected page after reconnecting, then retry the update.
            restore_before_retry=True,
        )
        self._selected_instruction = instruction

    def _query_space(self) -> tuple[int, int]:
        response = self._send_resilient(
            _CMD_STORAGE_INFO,
            expect_response=True,
            restore_before_retry=False,
        )
        if response is None:
            raise RuntimeError("missing STORAGE_INFO response")

        command, payload = response
        if command != _CMD_STORAGE_INFO:
            raise RuntimeError(f"unexpected STORAGE_INFO response command 0x{command:02x}")
        if len(payload) != 8:
            raise RuntimeError(f"unexpected STORAGE_INFO response length {len(payload)}")

        return struct.unpack(">II", payload)

    def _ensure_media_tmpfs(self) -> None:
        """Ensure the dedicated media directory is RAM-backed."""

        script = (
            f"if grep -q '^tmpfs {_MEDIA_RAM_DIR} tmpfs ' /proc/mounts; then exit 0; fi; "
            f"if grep -q ' {_MEDIA_RAM_DIR} ' /proc/mounts; then "
            f"echo 'unexpected mount on {_MEDIA_RAM_DIR}' 1>&2; exit 1; fi; "
            f"mkdir -p {_MEDIA_RAM_DIR} && "
            f"mount -t tmpfs -o {_MEDIA_TMPFS_OPTIONS} tmpfs {_MEDIA_RAM_DIR}"
        )
        self._run_adb("shell", script)

    def _file_exists(self, remote_name: str) -> bool:
        raw_name = remote_name.encode("utf-8")
        response = self._send_resilient(
            _CMD_FILE_EXISTS,
            raw_name,
            expect_response=True,
            restore_before_retry=False,
        )
        if response is None:
            raise RuntimeError("missing FILE_EXISTS response")

        command, payload = response
        if command != _CMD_FILE_EXISTS:
            raise RuntimeError(f"unexpected FILE_EXISTS response command 0x{command:02x}")
        if len(payload) != len(raw_name) + 1 or payload[0] not in (0, 1) or payload[1:] != raw_name:
            raise RuntimeError(f"unexpected FILE_EXISTS response payload {payload.hex(' ')}")
        return payload[0] == 1

    def _delete_file(self, remote_name: str) -> None:
        # State 1 deletes a single named file.  State 0 can delete unrelated
        # application files and must never be used for cleanup.
        payload = b"\x01" + remote_name.encode("utf-8")
        response = self._send_resilient(
            _CMD_DELETE_FILE,
            payload,
            expect_response=True,
            restore_before_retry=False,
        )
        if response is None:
            raise RuntimeError("missing DELETE_FILE response")

        command, ack = response
        if command != _CMD_DELETE_FILE or ack != payload:
            raise RuntimeError(
                "unexpected DELETE_FILE acknowledgement: "
                f"command=0x{command:02x}, payload={ack.hex(' ')}"
            )

    def _upload_media(self, remote_name: str, data: bytes) -> None:
        """Upload media; restart the entire stateful transfer on disconnect."""

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                self._upload_media_once(remote_name, data)
                return
            except (OSError, ConnectionError, TimeoutError, RuntimeError) as err:
                last_error = err
                if attempt == 1:
                    break
                _LOGGER.warning(
                    "media upload to HAF700 failed: %s; reconnecting and restarting",
                    err,
                )
                self._connect_magicbox()

        raise RuntimeError(f"failed to upload HAF700 media {remote_name!r}: {last_error}")

    def _upload_media_once(self, remote_name: str, data: bytes) -> None:
        encoded_name = remote_name.encode("utf-8")
        join_payload = struct.pack(">I", len(data)) + encoded_name
        response = self._send_once(
            _CMD_BEGIN_UPLOAD,
            join_payload,
            expect_response=True,
        )
        if response is None:
            raise RuntimeError("missing BEGIN_UPLOAD response")

        command, payload = response
        if command != _CMD_BEGIN_UPLOAD:
            raise RuntimeError(f"unexpected BEGIN_UPLOAD response command 0x{command:02x}")
        if len(payload) < 4 or payload[:4] != b"\x00\x00\x00\x00" or payload[4:] != encoded_name:
            raise RuntimeError(f"command BEGIN_UPLOAD rejected {remote_name!r}: {payload.hex(' ')}")

        for offset in range(0, len(data), _UPLOAD_CHUNK_SIZE):
            chunk = data[offset : offset + _UPLOAD_CHUNK_SIZE]
            response = self._send_once(
                _CMD_UPLOAD_CHUNK,
                struct.pack(">I", offset) + chunk,
                expect_response=True,
            )
            if response is None:
                raise RuntimeError("missing UPLOAD_CHUNK response")

            command, payload = response
            if command != _CMD_UPLOAD_CHUNK or payload != b"\x00\x00\x00\x04":
                raise RuntimeError(
                    "unexpected UPLOAD_CHUNK acknowledgement: "
                    f"command=0x{command:02x}, payload={payload.hex(' ')}"
                )

        response = self._send_once(_CMD_FINISH_UPLOAD, expect_response=True)
        if response is None:
            raise RuntimeError("missing FINISH_UPLOAD response")

        command, payload = response
        if command != _CMD_FINISH_UPLOAD or payload:
            raise RuntimeError(
                "unexpected FINISH_UPLOAD acknowledgement: "
                f"command=0x{command:02x}, payload={payload.hex(' ')}"
            )

        if not self._file_exists(remote_name):
            raise RuntimeError(f"uploaded media was not retained by MagicBox: {remote_name!r}")

    def _list_liquidctl_media(self) -> list[str]:
        # The file-list command is not recursive, so enumerate the dedicated
        # media directory through ADB instead.
        result = self._run_adb("shell", f"ls {_MEDIA_RAM_DIR}", check=False)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            if "No such file or directory" in stderr or "No such file or directory" in stdout:
                return []
            raise ConnectionError(
                "could not list HAF700 RAM media directory: "
                f"{stderr or stdout or result.returncode}"
            )

        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _cleanup_liquidctl_media(self, keep_remote_name: str) -> None:
        keep_basename = Path(keep_remote_name).name
        for item in self._list_liquidctl_media():
            if item == keep_basename:
                continue
            self._delete_file(f"{_MEDIA_RAM_PREFIX}{item}")
