"""LCD asset handling and dashboard rendering for ASUS Ryujin devices.

This module deliberately contains no USB or HID transport code.  Keeping the
presentation layer separate makes the device driver easier to audit.

Copyright Aenima4six2 and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence

_LCD_RESOLUTION = (640, 480)
_LCD_FRAME_SIZE = _LCD_RESOLUTION[0] * _LCD_RESOLUTION[1] * 3
_LCD_STATS_DEFAULT_ACCENT = "#b300ff"
_LCD_STATS_NAMES = {
    "liquid_temperature": "Liquid temperature",
    "pump_speed": "Pump speed",
    "pump_duty": "Pump duty",
    "pump_fan_speed": "Pump fan speed",
    "pump_fan_duty": "Pump fan duty",
}


def _prepare_lcd_image(image):
    """Convert a Pillow image to the Ryujin III Extreme's native frame format."""
    return image.convert("RGB").resize(_LCD_RESOLUTION).tobytes("raw", "RGB")


def _prepare_lcd_frame(path):
    """Load an image file and convert it to the Ryujin III Extreme frame format."""
    with Image.open(path) as image:
        return _prepare_lcd_image(image)


def _iter_lcd_animation(path):
    """Yield converted GIF frames and their display durations in seconds."""
    with Image.open(path) as animation:
        if not getattr(animation, "is_animated", False):
            raise ValueError("GIF mode requires an animated image")
        while True:
            for image in ImageSequence.Iterator(animation):
                yield _prepare_lcd_image(image), max(image.info.get("duration", 100), 20) / 1000


def _iter_lcd_background(path):
    """Yield resized RGB background frames and their display durations."""
    with Image.open(path) as animation:
        if not getattr(animation, "is_animated", False):
            raise ValueError("background is not animated")
        while True:
            for image in ImageSequence.Iterator(animation):
                yield image.convert("RGB").resize(_LCD_RESOLUTION), max(
                    image.info.get("duration", 100), 20
                ) / 1000


def _load_lcd_static_background(path):
    """Load a non-animated background image, returning None for an animation."""
    with Image.open(path) as image:
        if getattr(image, "is_animated", False):
            return None
        return image.convert("RGB").resize(_LCD_RESOLUTION)


def _lcd_font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _parse_lcd_color(value):
    value = str(_LCD_STATS_DEFAULT_ACCENT if value is None else value).lstrip("#")
    if len(value) != 6:
        raise ValueError("stats colour must be a six-digit RGB hex value")
    try:
        return tuple(int(value[index : index + 2], 16) for index in range(0, 6, 2))
    except ValueError as err:
        raise ValueError("stats colour must be a six-digit RGB hex value") from err


def _parse_lcd_opacity(value):
    try:
        value = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError("background opacity must be a number from 0.0 to 1.0") from err
    if not 0 <= value <= 1:
        raise ValueError("background opacity must be a number from 0.0 to 1.0")
    return value


def _scale_color(color, factor):
    return tuple(round(component * factor) for component in color)


def _lighten_color(color, amount):
    return tuple(round(component + (255 - component) * amount) for component in color)


def _read_lcd_custom_stat(config):
    """Run a configured argv command and return its output as an LCD value."""
    try:
        result = subprocess.run(
            config["command"], shell=False, capture_output=True, check=True, text=True, timeout=2
        )
    except (OSError, subprocess.SubprocessError) as err:
        raise ValueError(f"custom statistic command failed: {config['command']}") from err
    value = result.stdout.strip().replace("\n", " ")
    if not value:
        raise ValueError(f"custom statistic command returned no value: {config['command']}")
    return value, config.get("unit", "")


def _read_lcd_custom_stats(config, page):
    return [
        _read_lcd_custom_stat(selected) if selected["stat"] == "custom" else None
        for card in config["layout"].values()
        for selected in [card["stats"][page % len(card["stats"])]]
    ]


def _format_lcd_number(value, max_digits):
    value = float(value)
    magnitude, suffix = abs(value), ""
    if magnitude >= 10**max_digits:
        value, suffix = (value / 1_000_000, "M") if magnitude >= 1_000_000 else (value / 1_000, "k")
        magnitude = abs(value)
    places = max(0, min(2, max_digits - len(str(int(magnitude)))))
    formatted = f"{value:.{places}f}"
    return f"{formatted.rstrip('0').rstrip('.') if places else formatted}{suffix}"


def _format_lcd_value(value, unit, max_digits):
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return f"{value}{unit}".strip()
    return f"{_format_lcd_number(value, max_digits)}{unit}"


def _lcd_stats_cards(layout):
    """Return balanced card positions and value font sizes for a card count."""
    cards = {
        1: [(32, 108, 576, 340, 128)],
        2: [(32, 108, 268, 340, 58), (340, 108, 268, 340, 58)],
        3: [(32, 108, 576, 162, 108), (32, 304, 268, 144, 52), (340, 304, 268, 144, 52)],
        4: [
            (32, 108, 268, 154, 50),
            (340, 108, 268, 154, 50),
            (32, 294, 268, 154, 50),
            (340, 294, 268, 154, 50),
        ],
    }
    return [
        dict(zip(("x", "y", "width", "height", "font_size"), card)) for card in cards[len(layout)]
    ]


def _fit_lcd_label(draw, text, max_width, max_height):
    words = text.upper().split()
    for size in range(26, 11, -1):
        font, lines, line = _lcd_font(size), [], ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if line and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        line_height = draw.textbbox((0, 0), "Ag", font=font)[3]
        if len(lines) <= 2 and len(lines) * line_height <= max_height:
            return font, lines, line_height
    return _lcd_font(12), [text.upper()], 14


def _default_lcd_stats_config(
    background_color="#100713", font_color=_LCD_STATS_DEFAULT_ACCENT, interval=5
):
    return {
        "background_color": _parse_lcd_color(background_color),
        "background_opacity": 1.0,
        "font_color": _parse_lcd_color(font_color),
        "interval": interval,
        "title": "RYUJIN III EXTREME",
        "background": None,
        "layout": {
            "liquid": {
                "background_color": None,
                "font_color": None,
                "stats": [{"stat": "liquid_temperature", "indicator": "LIQUID"}],
            },
            "pump": {
                "background_color": None,
                "font_color": None,
                "stats": [
                    {"stat": "pump_speed", "indicator": "PUMP"},
                    {"stat": "pump_duty", "indicator": "PUMP"},
                ],
            },
            "pump_fan": {
                "background_color": None,
                "font_color": None,
                "stats": [
                    {"stat": "pump_fan_speed", "indicator": "PUMP FAN"},
                    {"stat": "pump_fan_duty", "indicator": "PUMP FAN"},
                ],
            },
        },
    }


def _validate_lcd_stats_config(config):
    if not isinstance(config, dict):
        raise ValueError("stats configuration must be a JSON object")
    allowed = {
        "background_color",
        "background_opacity",
        "font_color",
        "interval",
        "title",
        "layout",
        "background",
    }
    unknown = config.keys() - allowed
    if unknown:
        raise ValueError(f"unknown stats configuration key: {next(iter(unknown))}")
    result = _default_lcd_stats_config()
    for key, parser in (
        ("background_color", _parse_lcd_color),
        ("background_opacity", _parse_lcd_opacity),
        ("font_color", _parse_lcd_color),
    ):
        if key in config:
            result[key] = parser(config[key])
    try:
        result["interval"] = float(config.get("interval", result["interval"]))
    except (TypeError, ValueError) as err:
        raise ValueError("stats interval must be a number of seconds") from err
    if result["interval"] <= 0:
        raise ValueError("stats interval must be greater than zero")
    if "title" in config:
        if not isinstance(config["title"], str):
            raise ValueError("stats title must be a string")
        result["title"] = config["title"]
    if "layout" in config:
        layout = config["layout"]
        if not isinstance(layout, dict) or not 1 <= len(layout) <= 4:
            raise ValueError("layout must map one to four cards to stat lists")
        for card_name, card in layout.items():
            if not isinstance(card_name, str) or not isinstance(card, dict):
                raise ValueError("each layout card must be a mapping")
            allowed_card = {
                "background_color",
                "background_opacity",
                "font_color",
                "offset_x",
                "offset_y",
                "stats",
            }
            if (
                set(card) - allowed_card
                or not isinstance(card.get("stats"), list)
                or not card["stats"]
            ):
                raise ValueError("each layout card needs a non-empty stats list")
            for key in ("background_color", "font_color"):
                if key in card and card[key] is not None:
                    card[key] = _parse_lcd_color(card[key])
            if "background_opacity" in card:
                card["background_opacity"] = _parse_lcd_opacity(card["background_opacity"])
            for key in ("offset_x", "offset_y"):
                if key in card and not isinstance(card[key], int):
                    raise ValueError(f"card {key} must be an integer number of pixels")
            for stat in card["stats"]:
                if not isinstance(stat, dict) or not isinstance(stat.get("indicator"), str):
                    raise ValueError("card stat or indicator is invalid")
                if stat.get("stat") == "custom":
                    if set(stat) - {"stat", "indicator", "command", "unit"}:
                        raise ValueError("custom card stats only support command and unit")
                    command = stat.get("command")
                    if (
                        not isinstance(command, list)
                        or not command
                        or not all(isinstance(arg, str) and arg for arg in command)
                    ):
                        raise ValueError(
                            "custom card stat command must be a non-empty list of strings"
                        )
                    if "unit" in stat and not isinstance(stat["unit"], str):
                        raise ValueError("custom card stat unit must be a string")
                elif set(stat) != {"stat", "indicator"} or stat["stat"] not in _LCD_STATS_NAMES:
                    raise ValueError("card stat or indicator is invalid")
        result["layout"] = layout
    if "background" in config:
        if config["background"] is not None and not isinstance(config["background"], str):
            raise ValueError("background must be a path to an image or GIF")
        result["background"] = config["background"]
    return result


def _load_lcd_stats_config(value, interval):
    path = Path(value) if value else None
    if path and path.is_file():
        with path.open(encoding="utf-8") as config_file:
            config = _validate_lcd_stats_config(json.load(config_file))
        if config["background"]:
            background = Path(config["background"])
            config["background"] = (
                background if background.is_absolute() else path.parent / background
            )
        if interval is not None:
            config["interval"] = float(interval)
            if config["interval"] <= 0:
                raise ValueError("stats interval must be greater than zero")
        return config
    if value and path.suffix.lower() == ".json":
        raise ValueError(f"could not read stats configuration: {value}")
    shorthand_interval = float(interval) if interval is not None else 5
    if shorthand_interval <= 0:
        raise ValueError("stats interval must be greater than zero")
    return _default_lcd_stats_config(font_color=value, interval=shorthand_interval)


def _render_lcd_stats(
    status, config, page, remaining_seconds, background_image=None, custom_values=None
):
    by_name, visible = {stat[0]: stat for stat in status}, []
    for index, card_config in enumerate(config["layout"].values()):
        selected = card_config["stats"][page % len(card_config["stats"])]
        if selected["stat"] == "custom":
            value, unit = (
                custom_values[index]
                if custom_values is not None
                else _read_lcd_custom_stat(selected)
            )
        else:
            stat = by_name.get(_LCD_STATS_NAMES[selected["stat"]])
            if stat is None:
                raise ValueError(f"configured statistic is unavailable: {selected['stat']}")
            value, unit = stat[1:]
        visible.append((selected["indicator"], value, unit))
    font_color, background = config["font_color"], config["background_color"]
    panel, border, muted = (
        _scale_color(font_color, 0.14),
        _scale_color(font_color, 0.55),
        _lighten_color(font_color, 0.55),
    )
    image = (
        background_image.convert("RGB").resize(_LCD_RESOLUTION)
        if background_image is not None
        else Image.new("RGB", _LCD_RESOLUTION, background)
    )
    if background_image is not None and config["background_opacity"] < 1:
        image = Image.alpha_composite(
            image.convert("RGBA"),
            Image.new(
                "RGBA", _LCD_RESOLUTION, (*background, round(config["background_opacity"] * 255))
            ),
        ).convert("RGB")
    draw, title_font = ImageDraw.Draw(image), _lcd_font(28)
    draw.text((32, 28), config["title"], font=title_font, fill=muted)
    countdown = f"{math.ceil(remaining_seconds)}s"
    draw.text(
        (608 - draw.textbbox((0, 0), countdown, font=title_font)[2], 28),
        countdown,
        font=title_font,
        fill=muted,
    )
    draw.line((32, 76, 608, 76), fill=border, width=2)
    for card, card_config, (name, value, unit) in zip(
        _lcd_stats_cards(config["layout"]), config["layout"].values(), visible
    ):
        x0, y0 = card["x"] + card_config.get("offset_x", 0), card["y"] + card_config.get(
            "offset_y", 0
        )
        x1, y1 = x0 + card["width"], y0 + card["height"]
        card_background = card_config.get("background_color") or panel
        overlay = Image.new("RGBA", _LCD_RESOLUTION)
        ImageDraw.Draw(overlay).rectangle(
            (x0, y0, x1, y1),
            fill=(*card_background, round(card_config.get("background_opacity", 1.0) * 255)),
        )
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)
        draw.rectangle((x0, y0, x1, y1), outline=border, width=2)
        label_font, lines, line_height = _fit_lcd_label(
            draw, name, card["width"] - 40, card["height"] // 3
        )
        label_color = _lighten_color(card_config.get("font_color") or font_color, 0.55)
        for line_index, line in enumerate(lines):
            draw.text(
                (x0 + 20, y0 + 20 + line_index * line_height),
                line,
                font=label_font,
                fill=label_color,
            )
        value_text = _format_lcd_value(value, unit, 8 if card["width"] >= 500 else 5)
        value_font = _lcd_font(card["font_size"])
        while (
            value_font.size > 12
            and draw.textbbox((0, 0), value_text, font=value_font)[2] > card["width"] - 40
        ):
            value_font = _lcd_font(value_font.size - 1)
        value_bottom = draw.textbbox((0, 0), value_text, font=value_font)[3]
        draw.text(
            (x0 + 20, y1 - 20 - value_bottom),
            value_text,
            font=value_font,
            fill=card_config.get("font_color") or font_color,
        )
    return _prepare_lcd_image(image)
