"""liquidctl driver for NZXT Control Hub.

Copyright Joseph Livecchi, and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from liquidctl.driver.smart_device import _BaseSmartDevice
from liquidctl.util import Hue2Accessory, HUE2_MAX_ACCESSORIES_IN_CHANNEL

_MIN_DUTY = 0
_MAX_DUTY = 100


class ControlHub(_BaseSmartDevice):
    """NZXT Control Hub RGB and fan controller."""

    _MATCHES = [
        (0x1E71, 0x2022, "NZXT Control Hub", {"speed_channel_count": 5, "color_channel_count": 5}),
    ]

    _MAX_READ_ATTEMPTS = 12
    _READ_LENGTH = 64
    _WRITE_LENGTH = 64

    # Color modes with extended packet configuration
    # Format: (mode_byte, variant_byte, moving_byte, min_colors, max_colors, packet_config)
    # packet_config only needs to specify overrides; defaults are applied in _build_mode_packet
    _COLOR_MODES = {
        "off": (0x00, 0x00, 0x00, 0, 0, {"type": "fixed"}),
        "fixed": (0x00, 0x00, 0x00, 1, 1, {"type": "fixed"}),
        "fading": (
            0x01,
            0x00,
            0x00,
            1,
            8,
            {
                "speed_map": "fading",
                "has_colors": True,
                "color_count_pos": 56,
                "footer": [0x08, 0x18, 0x03, 0x00, 0x00],
            },
        ),
        "spectrum-wave": (
            0x02,
            0x00,
            0x00,
            0,
            0,
            {"has_direction": True, "footer": [0x00, 0x00, 0x12, 0x03, 0x00, 0x00]},
        ),
        "covering-marquee": (
            0x04,
            0x00,
            0x00,
            1,
            8,
            {
                "has_direction": True,
                "has_colors": True,
                "pad_to": 55,
                "direction_pos": 55,
                "color_count_pos": 56,
                "footer": [0x00, 0x18, 0x03, 0x00, 0x00],
            },
        ),
        "super-rainbow": (
            0x0C,
            0x00,
            0x00,
            0,
            0,
            {
                "has_direction": True,
                "header_padding": [0x00, 0x00],
                "footer": [0x00, 0x18, 0x03, 0x00, 0x00],
            },
        ),
    }

    # Speed mappings for different mode types
    _SPEED_MAPS = {
        "standard": {  # Used by spectrum-wave, marquee, rainbow modes
            "slowest": [0x5E, 0x01],
            "slower": [0x2C, 0x01],
            "normal": [0xFA, 0x00],
            "faster": [0x96, 0x00],
            "fastest": [0x50, 0x00],
        },
        "fading": {  # Used by fading mode
            "slowest": [0x50, 0x00],
            "slower": [0x3C, 0x00],
            "normal": [0x28, 0x00],
            "faster": [0x14, 0x00],
            "fastest": [0x0A, 0x00],
        },
    }

    # Channel ID to byte mapping
    _CHANNEL_BYTE_MAP = {0: 0x02, 1: 0x04, 2: 0x06, 3: 0x08, 4: 0x10}

    def __init__(self, device, description, speed_channel_count, color_channel_count, **kwargs):
        """Instantiate a driver with a device handle."""
        speed_channels = {
            f"fan{i + 1}": (i, _MIN_DUTY, _MAX_DUTY) for i in range(speed_channel_count)
        }
        color_channels = {f"led{i + 1}": i for i in range(color_channel_count)}
        if color_channels:
            color_channels["sync"] = 0xFF  # Special value for all channels
        super().__init__(device, description, speed_channels, color_channels)

    def initialize(self, **kwargs):
        """Initialize the device and the driver.

        Connected fans and LED accessories are detected.

        This method should be called every time the systems boots, resumes from
        a suspended state, or if the device has just been (re)connected.  In
        those scenarios, no other method, except `connect()` or `disconnect()`,
        should be called until the device and driver has been (re-)initialized.

        Returns None or a list of `(property, value, unit)` tuples, similarly
        to `get_status()`.
        """

        self.device.clear_enqueued_reports()

        update_interval = (lambda secs: 1 + round((secs - 0.5) / 0.25))(0.5)  # see issue #128
        self._write([0x60, 0x02, 0x01, 0xE8, update_interval, 0x01, 0xE8, update_interval])
        self._write([0x66, 0x01])

        # request static infos
        self._write([0x10, 0x02])  # firmware info
        self._write([0x20, 0x03])  # lighting info
        ret = []

        def parse_firm_info(msg):
            fw = f"{msg[0x11]}.{msg[0x12]}.{msg[0x13]}"
            ret.append(("Firmware version", fw, ""))

        def parse_led_info(msg):
            channel_count = msg[14]
            offset = 15  # offset of first channel/first accessory
            for c in range(channel_count):
                for a in range(HUE2_MAX_ACCESSORIES_IN_CHANNEL):
                    accessory_id = msg[offset + c * HUE2_MAX_ACCESSORIES_IN_CHANNEL + a]
                    if accessory_id == 0:
                        break
                    ret.append((f"LED {c + 1} accessory {a + 1}", Hue2Accessory(accessory_id), ""))

        parsers = {b"\x11\x02": parse_firm_info}
        if self._color_channels:
            parsers[b"\x21\x03"] = parse_led_info
        self._read_until(parsers)
        return sorted(ret)

    def get_status(self, **kwargs):
        ret = []

        def parse_fan_info(msg):
            mode_offset = 16
            rpm_offset = 24
            duty_offset = 40
            noise_offset = 56
            raw_modes = [None, "DC", "PWM"]

            for i, _ in enumerate(self._speed_channels):
                mode = raw_modes[msg[mode_offset + i]]
                ret.append(
                    (f"Fan {i + 1} speed", msg[rpm_offset + 1] << 8 | msg[rpm_offset], "rpm")
                )
                ret.append((f"Fan {i + 1} duty", msg[duty_offset + i], "%"))
                ret.append((f"Fan {i + 1} control mode", mode, ""))
                rpm_offset += 2
            ret.append(("Noise level", msg[noise_offset], "dB"))

        self.device.clear_enqueued_reports()
        self._read_until({b"\x67\x02": parse_fan_info})
        return sorted(ret)

    def set_color(self, channel, mode, colors, speed="normal", direction="forward", **kwargs):
        """Set the color mode for a specific channel.

        Supported modes:
        - off: Turn off the channel
        - fixed: Set a fixed color
        - fading: Fade between colors
        - spectrum-wave: Spectrum wave effect
        - covering-marquee: Covering marquee effect
        - super-rainbow: Super rainbow effect
        """
        if channel not in self._color_channels:
            raise ValueError(f"invalid channel: {channel}")

        if mode not in self._COLOR_MODES:
            raise ValueError(
                f"invalid mode: {mode}, supported modes: {list(self._COLOR_MODES.keys())}"
            )

        # Unpack mode configuration (extended format with config dict)
        mode_byte, variant_byte, moving_byte, min_colors, max_colors, packet_config = (
            self._COLOR_MODES[mode]
        )

        # Convert colors to list if it's a map object
        colors_list = (
            list(colors)
            if hasattr(colors, "__iter__") and not isinstance(colors, (list, tuple))
            else colors
        )

        # Validate color count
        if len(colors_list) < min_colors:
            raise ValueError(f"mode {mode!r} requires at least {min_colors} colors")
        if len(colors_list) > max_colors:
            raise ValueError(f"mode {mode!r} supports at most {max_colors} colors")

        # Handle off mode
        if mode == "off":
            colors_list = [(0, 0, 0)]

        # Determine channel ID
        cid = self._color_channels[channel]

        # Set color mode and data
        if cid == 0xFF:  # sync mode - set all channels
            for ch_id in range(len(self._color_channels) - 1):  # -1 to exclude 'sync'
                self._set_channel_color_mode(
                    ch_id,
                    mode_byte,
                    variant_byte,
                    moving_byte,
                    colors_list,
                    speed,
                    direction,
                    packet_config,
                )
        else:
            self._set_channel_color_mode(
                cid,
                mode_byte,
                variant_byte,
                moving_byte,
                colors_list,
                speed,
                direction,
                packet_config,
            )

    def _set_channel_color_mode(
        self,
        channel_id,
        mode_byte,
        _variant_byte,
        _moving_byte,
        colors,
        speed,
        direction,
        packet_config,
    ):
        """Set color mode for a specific channel."""
        channel_byte = self._CHANNEL_BYTE_MAP.get(channel_id, 0x08)

        # Use packet_config to build the data
        data = self._build_mode_packet(
            channel_byte, mode_byte, colors, speed, direction, packet_config
        )

        # Pad and write
        padding = [0x00] * (self._WRITE_LENGTH - len(data))
        data.extend(padding)
        self._write(data)

        # Apply settings if required
        if packet_config.get("type") == "fixed":
            self._apply_color_settings(channel_byte)

    def _build_mode_packet(self, channel_byte, mode_byte, colors, speed, direction, config):
        """Build packet based on mode configuration from _COLOR_MODES.

        Applies sensible defaults for common fields:
        - type: 'animated' (unless specified as 'fixed')
        - base_cmd: [0x2a, 0x04] for animated, [0x26, 0x04] for fixed
        - speed_map: 'standard'
        - pad_to: 56
        - direction_pos: 56 (when has_direction is True)
        - led_count: 24 (for fixed type)
        """
        # Apply defaults
        packet_type = config.get("type", "animated")

        if packet_type == "fixed":
            # Fixed color mode defaults
            base_cmd = config.get("base_cmd", [0x26, 0x04])
            led_count = config.get("led_count", 24)

            data = base_cmd + [channel_byte, 0x00]
            if colors:
                r, g, b = colors[0]
                for _ in range(led_count):
                    data.extend([g, r, b])  # GRB order
            else:
                data.extend([0x00] * (led_count * 3))

        else:  # animated
            # Animated mode defaults
            base_cmd = config.get("base_cmd", [0x2A, 0x04])
            speed_map_name = config.get("speed_map", "standard")
            pad_to = config.get("pad_to", 56)
            _direction_pos = config.get("direction_pos", 56)

            data = base_cmd + [channel_byte, channel_byte, mode_byte]

            # Add speed bytes if speed_map is specified
            if speed_map_name:
                speed_map = self._SPEED_MAPS[speed_map_name]
                speed_bytes = speed_map.get(speed, speed_map["normal"])
                data.extend(speed_bytes)

            # Add header padding if specified
            if "header_padding" in config:
                data.extend(config["header_padding"])

            # Add colors if mode supports them
            if config.get("has_colors") and colors:
                for r, g, b in colors:
                    data.extend([g, r, b])  # GRB order

            # Pad to specified position
            while len(data) < pad_to:
                data.append(0x00)

            # Add direction byte if needed
            if config.get("has_direction"):
                direction_byte = 0x02 if direction == "backward" else 0x00
                data.append(direction_byte)

            # Add color count if needed
            if config.get("has_colors") and "color_count_pos" in config and colors:
                data.append(len(colors))

            # Add footer bytes if specified
            if "footer" in config:
                data.extend(config["footer"])

            # Pad to minimum length if no colors provided
            if not colors and config.get("has_colors"):
                while len(data) < 61:
                    data.append(0x00)

        return data

    def _apply_color_settings(self, channel_byte):
        """Apply/commit the color settings to the device."""
        # Based on USB capture analysis:
        # Format: 26 06 [channel] 00 01 00 00 18 00 00 80 00 32 00 00 01 00 00...
        data = [
            0x26,
            0x06,
            channel_byte,
            0x00,
            0x01,
            0x00,
            0x00,
            0x18,
            0x00,
            0x00,
            0x80,
            0x00,
            0x32,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
        ]

        # Pad to full packet size
        padding = [0x00] * (self._WRITE_LENGTH - len(data))
        data.extend(padding)

        self._write(data)

    def _write_fixed_duty(self, cid, duty):
        msg = [
            0x62,
            0x01,
            0x01 << cid,
            0x00,
            0x00,
            0x00,
        ]  # fan channel passed as bitflag in last 3 bits of 3rd byte
        msg[cid + 3] = (
            duty  # duty percent in 4th, 5th, and 6th bytes for, respectively, fan1, fan2 and fan3
        )
        self._write(msg)

    def _read_until(self, parsers):
        for _ in range(self._MAX_READ_ATTEMPTS):
            msg = self.device.read(self._READ_LENGTH)
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                func(msg)
            if not parsers:
                return
        assert (
            False
        ), f"missing messages (attempts={self._MAX_READ_ATTEMPTS}, missing={len(parsers)})"
