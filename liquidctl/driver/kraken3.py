"""liquidctl drivers for fourth-generation NZXT Kraken X and Z liquid coolers.

Supported devices:

- NZXT Kraken X (X53, X63 and Z73)
- NZXT Kraken Z (Z63 and Z73); no OLED screen control yet

Copyright (C) 2020–2021  Tom Frey, Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import itertools

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.util import normalize_profile, interpolate_profile, clamp, \
                           Hue2Accessory, HUE2_MAX_ACCESSORIES_IN_CHANNEL

_LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64
_MAX_READ_ATTEMPTS = 12

# Available speed channels for model X coolers
# name -> (channel_id, min_duty, max_duty)
# TODO adjust min duty value to what the firmware enforces
_SPEED_CHANNELS_KRAKENX = {
    'pump': (0x1, 20, 100),
}

# Available speed channels for model Z coolers
# name -> (channel_id, min_duty, max_duty)
# TODO adjust min duty values to what the firmware enforces
_SPEED_CHANNELS_KRAKENZ = {
    'pump': (0x1, 20, 100),
    'fan': (0x2, 0, 100),
}

_CRITICAL_TEMPERATURE = 59

# Available color channels and IDs for model X coolers
_COLOR_CHANNELS_KRAKENX = {
    'external': 0b001,
    'ring': 0b010,
    'logo': 0b100,
    'sync': 0b111
}

# Available color channels and IDs for model Z coolers
_COLOR_CHANNELS_KRAKENZ = {
    'external': 0b001,
}

# Available LED channel modes/animations
# name -> (mode, size/variant, speed scale, min colors, max colors)
# FIXME any point in a one-color *alternating* or tai-chi animations?
# FIXME are all modes really supported by all channels? (this is better because
#       of synchronization, but it's not how the previous generation worked, so
#       I would like to double check)
_COLOR_MODES = {
    'off':                                  (0x00, 0x00,  0, 0, 0),
    'fixed':                                (0x00, 0x00,  0, 1, 1),
    'fading':                               (0x01, 0x00,  1, 1, 8),
    'super-fixed':                          (0x01, 0x01,  9, 1, 40),
    'spectrum-wave':                        (0x02, 0x00,  2, 0, 0),
    'marquee-3':                            (0x03, 0x03,  2, 1, 1),
    'marquee-4':                            (0x03, 0x04,  2, 1, 1),
    'marquee-5':                            (0x03, 0x05,  2, 1, 1),
    'marquee-6':                            (0x03, 0x06,  2, 1, 1),
    'covering-marquee':                     (0x04, 0x00,  2, 1, 8),
    'alternating-3':                        (0x05, 0x03,  3, 1, 2),
    'alternating-4':                        (0x05, 0x04,  3, 1, 2),
    'alternating-5':                        (0x05, 0x05,  3, 1, 2),
    'alternating-6':                        (0x05, 0x06,  3, 1, 2),
    'moving-alternating-3':                 (0x05, 0x03,  4, 1, 2),
    'moving-alternating-4':                 (0x05, 0x04,  4, 1, 2),
    'moving-alternating-5':                 (0x05, 0x05,  4, 1, 2),
    'moving-alternating-6':                 (0x05, 0x06,  4, 1, 2),
    'pulse':                                (0x06, 0x00,  5, 1, 8),
    'breathing':                            (0x07, 0x00,  6, 1, 8),
    'super-breathing':                      (0x03, 0x00, 10, 1, 40),
    'candle':                               (0x08, 0x00,  0, 1, 1),
    'starry-night':                         (0x09, 0x00,  5, 1, 1),
    'rainbow-flow':                         (0x0b, 0x00,  2, 0, 0),
    'super-rainbow':                        (0x0c, 0x00,  2, 0, 0),
    'rainbow-pulse':                        (0x0d, 0x00,  2, 0, 0),
    'loading':                              (0x10, 0x00,  8, 1, 1),
    'tai-chi':                              (0x0e, 0x00,  7, 1, 2),
    'water-cooler':                         (0x0f, 0x00,  6, 2, 2),
    'wings':                                (None, 0x00, 11, 1, 1),

    # deprecated in favor of direction=backward
    'backwards-spectrum-wave':              (0x02, 0x00,  2, 0, 0),
    'backwards-marquee-3':                  (0x03, 0x03,  2, 1, 1),
    'backwards-marquee-4':                  (0x03, 0x04,  2, 1, 1),
    'backwards-marquee-5':                  (0x03, 0x05,  2, 1, 1),
    'backwards-marquee-6':                  (0x03, 0x06,  2, 1, 1),
    'covering-backwards-marquee':           (0x04, 0x00,  2, 1, 8),
    'backwards-moving-alternating-3':       (0x05, 0x03,  4, 1, 2),
    'backwards-moving-alternating-4':       (0x05, 0x04,  4, 1, 2),
    'backwards-moving-alternating-5':       (0x05, 0x05,  4, 1, 2),
    'backwards-moving-alternating-6':       (0x05, 0x06,  4, 1, 2),
    'backwards-rainbow-flow':               (0x0b, 0x00,  2, 0, 0),
    'backwards-super-rainbow':              (0x0c, 0x00,  2, 0, 0),
    'backwards-rainbow-pulse':              (0x0d, 0x00,  2, 0, 0),
}

# A static value per channel that is somehow related to animation time and
# synchronization, although the specific mechanism is not yet understood.
# Could require information from `initialize`, but more testing is required.
_STATIC_VALUE = {
    0b001: 40,  # may result in long all-off intervals (FIXME?)
    0b010: 8,
    0b100: 1,
    0b111: 40,  # may result in long all-off intervals (FIXME?)
}

# Speed scale/timing bytes
# scale -> (slowest, slower, normal, faster, fastest)
_SPEED_VALUE = {
    0:  ([0x32, 0x00], [0x32, 0x00], [0x32, 0x00], [0x32, 0x00], [0x32, 0x00]),
    1:  ([0x50, 0x00], [0x3c, 0x00], [0x28, 0x00], [0x14, 0x00], [0x0a, 0x00]),
    2:  ([0x5e, 0x01], [0x2c, 0x01], [0xfa, 0x00], [0x96, 0x00], [0x50, 0x00]),
    3:  ([0x40, 0x06], [0x14, 0x05], [0xe8, 0x03], [0x20, 0x03], [0x58, 0x02]),
    4:  ([0x20, 0x03], [0xbc, 0x02], [0xf4, 0x01], [0x90, 0x01], [0x2c, 0x01]),
    5:  ([0x19, 0x00], [0x14, 0x00], [0x0f, 0x00], [0x07, 0x00], [0x04, 0x00]),
    6:  ([0x28, 0x00], [0x1e, 0x00], [0x14, 0x00], [0x0a, 0x00], [0x04, 0x00]),
    7:  ([0x32, 0x00], [0x28, 0x00], [0x1e, 0x00], [0x14, 0x00], [0x0a, 0x00]),
    8:  ([0x14, 0x00], [0x14, 0x00], [0x14, 0x00], [0x14, 0x00], [0x14, 0x00]),
    9:  ([0x00, 0x00], [0x00, 0x00], [0x00, 0x00], [0x00, 0x00], [0x00, 0x00]),
    10: ([0x37, 0x00], [0x28, 0x00], [0x19, 0x00], [0x0a, 0x00], [0x00, 0x00]),
    11: ([0x6e, 0x00], [0x53, 0x00], [0x39, 0x00], [0x2e, 0x00], [0x20, 0x00]),
}

_ANIMATION_SPEEDS = {
    'slowest': 0x0,
    'slower': 0x1,
    'normal': 0x2,
    'faster': 0x3,
    'fastest': 0x4,
}


class KrakenX3(UsbHidDriver):
    """Fourth-generation Kraken X liquid cooler."""

    SUPPORTED_DEVICES = [
        (0x1e71, 0x2007, None, 'NZXT Kraken X (X53, X63 or X73)', {
            'speed_channels': _SPEED_CHANNELS_KRAKENX,
            'color_channels': _COLOR_CHANNELS_KRAKENX,
        })
    ]

    def __init__(self, device, description, speed_channels, color_channels, **kwargs):
        super().__init__(device, description)
        self._speed_channels = speed_channels
        self._color_channels = color_channels

    def initialize(self, **kwargs):
        """Initialize the device.

        Reports the current firmware of the device.  Returns a list of (key,
        value, unit) tuples.
        """

        self.device.clear_enqueued_reports()
        # request static infos
        self._write([0x10, 0x01])  # firmware info
        self._write([0x20, 0x03])  # lighting info
        # initialize
        update_interval = (lambda secs: 1 + round((secs - .5) / .25))(.5)  # see issue #128
        self._write([0x70, 0x02, 0x01, 0xb8, update_interval])
        self._write([0x70, 0x01])
        status = []

        def parse_firm_info(msg):
            fw = f'{msg[0x11]}.{msg[0x12]}.{msg[0x13]}'
            status.append(('Firmware version', fw, ''))

        def parse_led_info(msg):
            channel_count = msg[14]
            assert channel_count == len(self._color_channels) - ('sync' in self._color_channels), \
                   f'Unexpected number of color channels received: {channel_count}'

            def find(channel, accessory):
                offset = 15  # offset of first channel/first accessory
                acc_id = msg[offset + channel * HUE2_MAX_ACCESSORIES_IN_CHANNEL + accessory]
                return Hue2Accessory(acc_id) if acc_id else None

            for i in range(HUE2_MAX_ACCESSORIES_IN_CHANNEL):
                accessory = find(0, i)
                if not accessory:
                    break
                status.append((f'LED accessory {i + 1}', accessory, ''))

            if len(self._color_channels) > 1:
                found_ring = find(1, 0) == Hue2Accessory.KRAKENX_GEN4_RING
                found_logo = find(2, 0) == Hue2Accessory.KRAKENX_GEN4_LOGO
                status.append(('Pump Ring LEDs', 'detected' if found_ring else 'missing', ''))
                status.append(('Pump Logo LEDs', 'detected' if found_logo else 'missing', ''))
                assert found_ring and found_logo, "Pump ring and/or logo were not detected"

        self._read_until({b'\x11\x01': parse_firm_info, b'\x21\x03': parse_led_info})
        return sorted(status)

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        self.device.clear_enqueued_reports()
        msg = self._read()
        if msg[15:17] == [0xff, 0xff]:
            _LOGGER.warning('unexpected temperature reading, possible firmware fault;')
            _LOGGER.warning('try resetting the device or updating the firmware')
            _LOGGER.warning('(see https://github.com/liquidctl/liquidctl/issues/172)')
        return [
            ('Liquid temperature', msg[15] + msg[16] / 10, '°C'),
            ('Pump speed', msg[18] << 8 | msg[17], 'rpm'),
            ('Pump duty', msg[19], '%'),
        ]

    def set_color(self, channel, mode, colors, speed='normal', direction='forward', **kwargs):
        """Set the color mode for a specific channel."""

        channel = channel.lower()
        mode = mode.lower()
        speed = speed.lower()
        direction = direction.lower()

        if 'backwards' in mode:
            _LOGGER.warning('deprecated mode, move to direction=backwards option')
            mode = mode.replace('backwards-', '')
            direction = 'backward'

        cid = self._color_channels[channel]
        _, _, _, mincolors, maxcolors = _COLOR_MODES[mode]
        colors = [[g, r, b] for [r, g, b] in colors]
        if len(colors) < mincolors:
            raise ValueError(f'not enough colors for mode={mode}, at least {mincolors} required')
        elif maxcolors == 0:
            if colors:
                _LOGGER.warning('too many colors for mode=%s, none needed', mode)
            colors = [[0, 0, 0]]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            _LOGGER.warning('too many colors for mode=%s, dropping to %d', mode, maxcolors)
            colors = colors[:maxcolors]

        sval = _ANIMATION_SPEEDS[speed]
        self._write_colors(cid, mode, colors, sval, direction)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to use a speed profile."""
        cid, dmin, dmax = self._speed_channels[channel]
        header = [0x72, cid, 0x00, 0x00]
        norm = normalize_profile(profile, _CRITICAL_TEMPERATURE)
        stdtemps = list(range(20, _CRITICAL_TEMPERATURE + 1))
        interp = [clamp(interpolate_profile(norm, t), dmin, dmax) for t in stdtemps]
        for temp, duty in zip(stdtemps, interp):
            _LOGGER.info('setting %s PWM duty to %d%% for liquid temperature >= %d°C',
                         channel, duty, temp)
        self._write(header + interp)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        self.set_speed_profile(channel, [(0, duty), (_CRITICAL_TEMPERATURE - 1, duty)])

    def _read(self):
        data = self.device.read(_READ_LENGTH)
        return data

    def _read_until(self, parsers):
        for _ in range(_MAX_READ_ATTEMPTS):
            msg = self.device.read(_READ_LENGTH)
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                func(msg)
            if not parsers:
                return
        assert False, f'missing messages (attempts={_MAX_READ_ATTEMPTS}, missing={len(parsers)})'

    def _write(self, data):
        padding = [0x0] * (_WRITE_LENGTH - len(data))
        self.device.write(data + padding)

    def _write_colors(self, cid, mode, colors, sval, direction):
        mval, size_variant, speed_scale, mincolors, maxcolors = _COLOR_MODES[mode]
        color_count = len(colors)

        if 'super-fixed' == mode or 'super-breathing' == mode:
            color = list(itertools.chain(*colors)) + [0x00, 0x00, 0x00] * (maxcolors - color_count)
            speed_value = _SPEED_VALUE[speed_scale][sval]
            self._write([0x22, 0x10, cid, 0x00] + color)
            self._write([0x22, 0x11, cid, 0x00])
            self._write([0x22, 0xa0, cid, 0x00, mval] + speed_value +
                        [0x08, 0x00, 0x00, 0x80, 0x00, 0x32, 0x00, 0x00, 0x01])

        elif mode == 'wings':  # wings requires special handling
            self._write([0x22, 0x10, cid])  # clear out all independent LEDs
            self._write([0x22, 0x11, cid])  # clear out all independent LEDs
            color_lists = {}
            color_lists[0] = colors[0] * 2
            color_lists[1] = [int(x // 2.5) for x in color_lists[0]]
            color_lists[2] = [int(x // 4) for x in color_lists[1]]
            color_lists[3] = [0x00] * 8
            speed_value = _SPEED_VALUE[speed_scale][sval]
            for i in range(8):  # send color scheme first, before enabling wings mode
                mod = 0x05 if i in [3, 7] else 0x01
                alt = [0x04, 0x84] if i // 4 == 0 else [0x84, 0x04]
                msg = ([0x22, 0x20, cid, i, 0x04] + speed_value + [mod] + [0x00] * 7 + [0x02] +
                       alt + [0x00] * 10)
                self._write(msg + color_lists[i % 4])
            self._write([0x22, 0x03, cid, 0x08])   # this actually enables wings mode

        else:
            opcode = [0x2a, 0x04]
            address = [cid, cid]
            speed_value = _SPEED_VALUE[speed_scale][sval]
            header = opcode + address + [mval] + speed_value
            color = list(itertools.chain(*colors)) + [0, 0, 0] * (16 - color_count)

            if 'marquee' in mode:
                backwards_byte = 0x04
            elif mode == 'starry-night' or 'moving-alternating' in mode:
                backwards_byte = 0x01
            else:
                backwards_byte = 0x00

            if direction == 'backward':
                backwards_byte += 0x02

            if mode == 'fading' or mode == 'pulse' or mode == 'breathing':
                mode_related = 0x08
            elif mode == 'tai-chi':
                mode_related = 0x05
            elif mode == 'water-cooler':
                mode_related = 0x05
                color_count = 0x01
            elif mode == 'loading':
                mode_related = 0x04
            else:
                mode_related = 0x00

            static_byte = _STATIC_VALUE[cid]
            led_size = size_variant if mval == 0x03 or mval == 0x05 else 0x03
            footer = [backwards_byte, color_count, mode_related, static_byte, led_size]
            self._write(header + color + footer)


class KrakenZ3(KrakenX3):
    """Fourth-generation Kraken Z liquid cooler."""

    SUPPORTED_DEVICES = [
        (0x1e71, 0x3008, None, 'NZXT Kraken Z (Z63 or Z73) (experimental)', {
            'speed_channels': _SPEED_CHANNELS_KRAKENZ,
            'color_channels': _COLOR_CHANNELS_KRAKENZ,
        })
    ]

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        self.device.clear_enqueued_reports()
        self._write([0x74, 0x01])
        msg = self._read()
        return [
            ('Liquid temperature', msg[15] + msg[16] / 10, '°C'),
            ('Pump speed', msg[18] << 8 | msg[17], 'rpm'),
            ('Pump duty', msg[19], '%'),
            ('Fan speed', msg[24] << 8 | msg[23], 'rpm'),
            ('Fan duty', msg[25], '%'),
        ]
