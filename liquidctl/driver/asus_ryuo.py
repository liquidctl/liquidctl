"""liquidctl driver for the ASUS Ryuo I 240 liquid cooler.

Adds sensor telemetry (coolant temperature), LED color control, and OLED
display upload to the existing fan-speed driver.

The OLED upload protocol was reverse-engineered from ASUS LiveDash v1.05.03
(AuraIC.dll, WriteFileToFW function).  The device accepts GIF images via a
chunked HID transfer and renders them on a 160x128 OLED panel embedded in
the pump head.

Copyright Bloodhundur and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import io
import logging
import time
from typing import List

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet
from liquidctl.util import LazyHexRepr, clamp, rpadlist

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 65
_PREFIX = 0xEC

# Register read requests: (send_header, expected_response_header)
_REQUEST_GET_FIRMWARE = (0x82, 0x02)
_REQUEST_GET_SENSORS = (0xEA, 0x6A)

# Write commands
_CMD_SET_FAN_SPEED = 0x2A
_CMD_LED_MODE = 0x3B
_CMD_LED_SAVE = 0x3F
_CMD_XFER_CTRL = 0x51
_CMD_FILE_SLOT = 0x6B
_CMD_ANIM_CTRL = 0x6C
_CMD_XFER_DATA = 0x6E

# LED modes exposed to users
_LED_MODES = {
    "off": 0x00,
    "static": 0x01,
    "breathing": 0x02,
    "flash": 0x03,
    "spectrum": 0x04,
    "rainbow": 0x05,
}

# OLED display constants
_OLED_WIDTH = 160
_OLED_HEIGHT = 128
_OLED_CHUNK_SIZE = 62
_OLED_CHUNK_DELAY = 0.02  # seconds; hardware SPI flash write speed limit

# Status labels
_STATUS_FIRMWARE = "Firmware version"
_STATUS_COOLANT_TEMP = "Liquid temperature"


class AsusRyuo(UsbHidDriver):
    """ASUS Ryuo I 240 liquid cooler."""

    _MATCHES = [
        (0x0B05, 0x1887, "ASUS Ryuo I 240", {}),
    ]

    def initialize(self, **kwargs):
        """Report firmware version.

        Returns a list of tuples of `bool, key, value, unit`.
        """
        msg = self._request(*_REQUEST_GET_FIRMWARE)
        fw_string = bytes(msg[2:]).split(b"\x00")[0].decode("ascii", errors="ignore")
        return [
            (_STATUS_FIRMWARE, fw_string, ""),
        ]

    def get_status(self, **kwargs):
        """Report coolant temperature.

        Returns a list of tuples of `key, value, unit`.
        """
        msg = self._request(*_REQUEST_GET_SENSORS)
        _LOGGER.debug("sensor register: %r", LazyHexRepr(msg[2:8]))

        # byte offset 3 (msg[3]) is coolant temperature in degrees Celsius
        coolant_temp = msg[3]

        if coolant_temp == 0:
            _LOGGER.warning("coolant temperature reads 0, sensor may not be ready")

        return [
            (_STATUS_COOLANT_TEMP, coolant_temp, "°C"),
        ]

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set fan duty cycle.

        Valid channels: `fans`.
        Duty is a percentage from 0 to 100.
        """
        if channel not in ("fans", "fan"):
            raise ValueError(f"invalid channel: {channel}")
        duty = clamp(duty, 0, 100)
        _LOGGER.info("setting fan duty to %d%%", duty)
        self._write([_PREFIX, _CMD_SET_FAN_SPEED, duty])

    def set_color(self, channel, mode, colors, speed="normal", **kwargs):
        """Set the pump-head LED color and mode.

        Valid channels: `led`.
        Valid modes: `off`, `static`, `breathing`, `flash`, `spectrum`, `rainbow`.
        Colors is a list of `(r, g, b)` tuples; only the first color is used.

        For `spectrum` and `rainbow` modes the color argument is ignored.
        """
        if channel not in ("led",):
            raise ValueError(f"invalid channel: {channel}")

        mode_lower = mode.lower()
        if mode_lower not in _LED_MODES:
            raise ValueError(f"invalid mode: {mode} (valid: {', '.join(_LED_MODES)})")

        mode_byte = _LED_MODES[mode_lower]
        colors = list(colors)

        if mode_lower == "off":
            r, g, b = 0, 0, 0
        elif mode_lower in ("spectrum", "rainbow"):
            r, g, b = 0, 0, 0
        elif colors:
            r, g, b = colors[0]
        else:
            raise ValueError("colors required for this mode")

        _LOGGER.info("setting LED to (%d, %d, %d) mode=%s", r, g, b, mode_lower)
        self._write([_PREFIX, _CMD_LED_MODE, 0x00, 0x22, mode_byte, r, g, b, 0x00, 0x02])
        self._write([_PREFIX, _CMD_LED_SAVE, 0x55])

    def set_screen(self, channel, mode, value, **kwargs):
        """Upload an image or GIF to the pump-head OLED display.

        Unstable.

        The device has a 160x128 pixel OLED.  Images are automatically resized
        and converted to GIF format before upload.

        Valid channels: `lcd`.

        | Mode | Value |
        | --- | --- |
        | `static` | path to image file |
        | `gif` | path to animated GIF |

        Keyword arguments:

        | Keyword | Value |
        | --- | --- |
        | `rotation` | `0` or `180` — rotate image for flipped mounts |

        Requires Pillow (`pip install pillow`).

        From the CLI, pass rotation as an unsafe keyword::

            liquidctl set lcd screen gif animation.gif rotation=180
        """
        if channel not in ("lcd",):
            raise ValueError(f"invalid channel: {channel}")
        if mode not in ("static", "gif"):
            raise ValueError(f"invalid mode: {mode} (valid: static, gif)")
        if not value:
            raise ValueError("file path required")

        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError("Pillow is required for OLED uploads: pip install pillow")

        rotation = int(kwargs.get("rotation", 0))
        rotate = rotation == 180
        gif_data = self._prepare_gif(value, mode == "gif", rotate=rotate)
        _LOGGER.info("uploading %d bytes to OLED", len(gif_data))
        self._upload_oled(gif_data)

    # -- internal helpers --

    def _prepare_gif(self, image_path, is_animated, rotate=False):
        """Load, resize, and encode image as GIF bytes for the OLED."""
        from PIL import Image

        img = Image.open(image_path)
        has_frames = hasattr(img, "n_frames") and img.n_frames > 1

        if has_frames and is_animated:
            frames = []
            durations = []
            for i in range(img.n_frames):
                img.seek(i)
                frame = img.copy().convert("RGBA")
                frame.thumbnail((_OLED_WIDTH, _OLED_HEIGHT), Image.LANCZOS)
                canvas = Image.new("RGBA", (_OLED_WIDTH, _OLED_HEIGHT), (0, 0, 0, 255))
                canvas.paste(
                    frame,
                    (
                        (_OLED_WIDTH - frame.size[0]) // 2,
                        (_OLED_HEIGHT - frame.size[1]) // 2,
                    ),
                )
                if rotate:
                    canvas = canvas.rotate(180)
                frames.append(canvas.convert("RGB"))
                durations.append(max(img.info.get("duration", 100) or 100, 33))

            p_frames = [f.quantize(colors=256, method=2) for f in frames]
            buf = io.BytesIO()
            p_frames[0].save(
                buf,
                format="GIF",
                save_all=True,
                append_images=p_frames[1:],
                duration=durations,
                loop=0,
                optimize=True,
            )
            return buf.getvalue()
        else:
            frame = img.convert("RGB")
            frame.thumbnail((_OLED_WIDTH, _OLED_HEIGHT), Image.LANCZOS)
            canvas = Image.new("RGB", (_OLED_WIDTH, _OLED_HEIGHT), (0, 0, 0))
            canvas.paste(
                frame,
                (
                    (_OLED_WIDTH - frame.size[0]) // 2,
                    (_OLED_HEIGHT - frame.size[1]) // 2,
                ),
            )
            if rotate:
                canvas = canvas.rotate(180)
            buf = io.BytesIO()
            canvas.quantize(colors=256, method=2).save(buf, format="GIF", optimize=True)
            return buf.getvalue()

    def _upload_oled(self, gif_data, slot=1):
        """Execute the 9-step OLED upload protocol.

        Protocol reverse-engineered from ASUS LiveDash v1.05.03 AuraIC.dll
        (WriteFileToFW function).

        IMPORTANT: Do NOT write to register 0x5C after upload.  Any write to
        0x5C causes the OLED to go permanently black until a full power cycle.
        """
        # Step 1: Init transfer
        self._write([_PREFIX, _CMD_XFER_CTRL, 0xA0])
        time.sleep(0.05)

        # Step 2: Set file slot
        self._write([_PREFIX, _CMD_FILE_SLOT, 0x01, 0x00, slot])
        time.sleep(0.05)

        # Step 3-4: Stop animation
        self._write([_PREFIX, _CMD_ANIM_CTRL, 0x01])  # stop
        time.sleep(0.05)
        self._write([_PREFIX, _CMD_ANIM_CTRL, 0x03])  # force stop
        time.sleep(0.05)

        # Step 5: Prepare for transfer
        self._write([_PREFIX, _CMD_ANIM_CTRL, 0x04])
        time.sleep(0.05)

        # Step 6: Send file data in 62-byte chunks
        total = len(gif_data)
        offset = 0
        while offset < total:
            chunk = gif_data[offset : offset + _OLED_CHUNK_SIZE]
            self._write([_PREFIX, _CMD_XFER_DATA, len(chunk)] + list(chunk))
            offset += len(chunk)
            time.sleep(_OLED_CHUNK_DELAY)

        _LOGGER.debug("sent %d bytes in %d chunks", total, (total + 61) // 62)

        # Step 7: Signal transfer complete
        self._write([_PREFIX, _CMD_ANIM_CTRL, 0x05])
        time.sleep(0.1)

        # Step 8: Finalize / start animation
        self._write([_PREFIX, _CMD_ANIM_CTRL, 0xFF])
        time.sleep(0.1)

        # Step 9: Commit transfer
        self._write([_PREFIX, _CMD_XFER_CTRL, 0x10, 0x01, slot])
        time.sleep(0.2)

        # Step 10: Set slot and start playback
        self._write([_PREFIX, _CMD_FILE_SLOT, 0x01, 0x00, slot])
        time.sleep(0.1)
        self._write([_PREFIX, _CMD_XFER_DATA, 0x00])  # start playback

    def _request(self, request_header: int, response_header: int) -> List[int]:
        self.device.clear_enqueued_reports()
        self._write([_PREFIX, request_header])
        return self._read(response_header)

    def _read(self, expected_header=None) -> List[int]:
        msg = self.device.read(_REPORT_LENGTH)
        if msg[0] != _PREFIX:
            raise ExpectationNotMet("unexpected report prefix")
        if expected_header is not None and msg[1] != expected_header:
            raise ExpectationNotMet(
                f"unexpected response header {msg[1]:#04x}, expected {expected_header:#04x}"
            )
        return msg

    def _write(self, data: List[int]):
        self.device.write(rpadlist(data, _REPORT_LENGTH, 0))
