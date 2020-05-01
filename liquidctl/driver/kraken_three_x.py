"""liquidctl driver for Kraken X3 devices from NZXT.

 Supported devices
 -----------------

  - [ ] NZXT Kraken X53
  - [ ] NZXT Kraken X63
  - [✓] NZXT Kraken X73

 Supported features
 ------------------

  - [✓] general monitoring
  - [✓] pump speed control
  - [✓] lighting control
  - [✓] lighting control advanced - super-breathing, super-fixed, wings, water-cooler
  - [✓] pump speed curve

 ---

 liquidctl driver for Kraken X3 devices from NZXT.
 Copyright (C) 2020–2020  Jonas Malaco
 Copyright (C) 2020–2020  Tom Frey
 Copyright (C) 2020–2020  each contribution's author

 This file is part of liquidctl.

 liquidctl is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 liquidctl is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.
 """

import logging
import itertools

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.util import normalize_profile, interpolate_profile, clamp

LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64
_MAX_READ_ATTEMPTS = 12
_CRITICAL_TEMPERATURE = 59

_COLOR_CHANNELS = {
    'ring': 0x02,
    'logo': 0x04,
}
_COLOR_MODES = {
    # (mode, size/variant, speed scale, min colors, max colors)
    'off':                                  (0x00, 0x00, 0, 0, 0),
    'fixed':                                (0x00, 0x00, 0, 1, 1),
    'fading':                               (0x01, 0x00, 1, 1, 8),
    'super-fixed':                          (0x01, 0x01, 9, 1, 8),
    'spectrum-wave':                        (0x02, 0x00, 2, 0, 0),
    'backwards-spectrum-wave':              (0x02, 0x00, 2, 0, 0),
    'marquee-3':                            (0x03, 0x03, 2, 1, 1),
    'marquee-4':                            (0x03, 0x04, 2, 1, 1),
    'marquee-5':                            (0x03, 0x05, 2, 1, 1),
    'marquee-6':                            (0x03, 0x06, 2, 1, 1),
    'backwards-marquee-3':                  (0x03, 0x03, 2, 1, 1),
    'backwards-marquee-4':                  (0x03, 0x04, 2, 1, 1),
    'backwards-marquee-5':                  (0x03, 0x05, 2, 1, 1),
    'backwards-marquee-6':                  (0x03, 0x06, 2, 1, 1),
    'covering-marquee':                     (0x04, 0x00, 2, 1, 8),
    'covering-backwards-marquee':           (0x04, 0x00, 2, 1, 8),
    'alternating-3':                        (0x05, 0x03, 3, 1, 2),
    'alternating-4':                        (0x05, 0x04, 3, 1, 2),
    'alternating-5':                        (0x05, 0x05, 3, 1, 2),
    'alternating-6':                        (0x05, 0x06, 3, 1, 2),
    'moving-alternating-3':                 (0x05, 0x03, 4, 1, 2),
    'moving-alternating-4':                 (0x05, 0x04, 4, 1, 2),
    'moving-alternating-5':                 (0x05, 0x05, 4, 1, 2),
    'moving-alternating-6':                 (0x05, 0x06, 4, 1, 2),
    'backwards-moving-alternating-3':       (0x05, 0x03, 4, 1, 2),
    'backwards-moving-alternating-4':       (0x05, 0x04, 4, 1, 2),
    'backwards-moving-alternating-5':       (0x05, 0x05, 4, 1, 2),
    'backwards-moving-alternating-6':       (0x05, 0x06, 4, 1, 2),
    'pulse':                                (0x06, 0x00, 5, 1, 8),
    'breathing':                            (0x07, 0x00, 6, 1, 8),
    'super-breathing':                      (0x03, 0x00,10, 1, 8),
    'candle':                               (0x08, 0x00, 0, 1, 1),
    'starry-night':                         (0x09, 0x00, 5, 1, 1),
    'rainbow-flow':                         (0x0b, 0x00, 2, 0, 0),
    'super-rainbow':                        (0x0c, 0x00, 2, 0, 0),
    'rainbow-pulse':                        (0x0d, 0x00, 2, 0, 0),
    'backwards-rainbow-flow':               (0x0b, 0x00, 2, 0, 0),
    'backwards-super-rainbow':              (0x0c, 0x00, 2, 0, 0),
    'backwards-rainbow-pulse':              (0x0b, 0x00, 2, 0, 0),
    'loading':                              (0x10, 0x00, 8, 1, 1),
    'tai-chi':                              (0x0e, 0x00, 7, 1, 2),
    'water-cooler':                         (0x0f, 0x00, 6, 2, 2),
    'wings':                                (None, 0x00,11, 1, 1),
}
_STATIC_VALUE = {
    0x02: 0x08,
    0x04: 0x01
}
_SPEED_VALUE = {
    # (slowest, slow, normal, fast, fastest)
    0: ([0x32, 0x00], [0x32, 0x00], [0x32, 0x00], [0x32, 0x00], [0x32, 0x00]),
    1: ([0x50, 0x00], [0x3c, 0x00], [0x28, 0x00], [0x14, 0x00], [0x0a, 0x00]),
    2: ([0x5e, 0x01], [0x2c, 0x01], [0xfa, 0x00], [0x96, 0x00], [0x50, 0x00]),
    3: ([0x40, 0x06], [0x14, 0x05], [0xe8, 0x03], [0x20, 0x03], [0x58, 0x02]),
    4: ([0x20, 0x03], [0xbc, 0x02], [0xf4, 0x01], [0x90, 0x01], [0x2c, 0x01]),
    5: ([0x19, 0x00], [0x14, 0x00], [0x0f, 0x00], [0x07, 0x00], [0x04, 0x00]),
    6: ([0x28, 0x00], [0x1e, 0x00], [0x14, 0x00], [0x0a, 0x00], [0x04, 0x00]),
    7: ([0x32, 0x00], [0x28, 0x00], [0x1e, 0x00], [0x14, 0x00], [0x0a, 0x00]),
    8: ([0x14, 0x00], [0x14, 0x00], [0x14, 0x00], [0x14, 0x00], [0x14, 0x00]),
    9: ([0x00, 0x00], [0x00, 0x00], [0x00, 0x00], [0x00, 0x00], [0x00, 0x00]),
    10:([0x37, 0x00], [0x28, 0x00], [0x19, 0x00], [0x0a, 0x00], [0x00, 0x00]),
    11:([0x6e, 0x00], [0x53, 0x00], [0x39, 0x00], [0x2e, 0x00], [0x20, 0x00]),
}
_ANIMATION_SPEEDS = {
    'slowest': 0x0,
    'slower': 0x1,
    'normal': 0x2,
    'faster': 0x3,
    'fastest': 0x4,
}
_ACCESSORY_NAMES = {
    0x01: "HUE+ LED Strip",
    0x02: "AER RGB 1",
    0x04: "HUE 2 LED Strip 300 mm",
    0x05: "HUE 2 LED Strip 250 mm",
    0x06: "HUE 2 LED Strip 200 mm",
    0x08: "HUE 2 Cable Comb",
    0x09: "HUE 2 Underglow 300 mm",
    0x0a: "HUE 2 Underglow 200 mm",
    0x0b: "AER RGB 2 120 mm",
    0x0c: "AER RGB 2 140 mm",
    0x10: "Kraken X3 Pump Ring",
    0x11: "Kraken X3 Pump Logo",
}


class KrakenThreeXDriver(UsbHidDriver):
    """liquidctl driver for Kraken X3 devices from NZXT."""

    SUPPORTED_DEVICES = [
        (0x1e71, 0x2007, None, 'NZXT Kraken X (X53, X63 or X73) (experimental)', {})
    ]

    def initialize(self, **kwargs):
        """Initialize the device.

        Reports the current firmware of the device.

        Returns a list of (key, value, unit) tuples.
        """
        self.device.clear_enqueued_reports()
        # request static infos
        self._write([0x10, 0x01])  # firmware info
        self._write([0x20, 0x03])  # lighting info
        # initialize
        self._write([0x70, 0x02, 0x01, 0xb8, 0x0b])
        self._write([0x70, 0x01])
        status = []

        def parse_firm_info(msg):
            fw = '{}.{}.{}'.format(msg[0x11], msg[0x12], msg[0x13])
            status.append(('Firmware version', fw, ''))

        def parse_led_info(msg):
            """
            FIXME: is is possible to attach other accessories to the pump?
            currently not possible to address devices via led id e.g. "led1"
            accessory_id: ? (LED 1 - ?) & 0x10 (LED 2 - ring) & 0x11 (LED 3 - logo)
            """
            num_light_channels = msg[14]  # the 15th byte (index 14) is # of light channels
            accessories_per_channel = 6  # each lighting channel supports up to 6 accessories
            light_accessory_index = 15  # offset in msg of info about first light accessory
            for light_channel in range(num_light_channels):
                for accessory_num in range(accessories_per_channel):
                    accessory_id = msg[light_accessory_index]
                    light_accessory_index += 1
                    if accessory_id != 0:
                        status.append(('LED {} accessory {}'.format(light_channel + 1, accessory_num + 1),
                                       _ACCESSORY_NAMES.get(accessory_id, 'Unknown'), ''))

        self._read_until({b'\x11\x01': parse_firm_info, b'\x21\x03': parse_led_info})
        self.device.release()
        return sorted(status)

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        msg = self._read()
        return [
            ('Liquid temperature', msg[15] + msg[14] / 10, '°C'),
            ('Pump speed', msg[18] << 8 | msg[17], 'rpm'),
            ('Pump duty', msg[19], '%'),
        ]

    def set_color(self, channel, mode, colors, speed='normal', **kwargs):
        """Set the color mode for a specific channel."""
        cid = _COLOR_CHANNELS[channel]
        _, _, _, mincolors, maxcolors = _COLOR_MODES[mode]
        colors = [[g, r, b] for [r, g, b] in colors]
        if len(colors) < mincolors:
            raise ValueError('Not enough colors for mode={}, at least {} required'.format(mode, mincolors))
        elif maxcolors == 0:
            if colors:
                LOGGER.warning('too many colors for mode=%s, none needed', mode)
            colors = [[0, 0, 0]]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            LOGGER.warning('too many colors for mode=%s, dropping to %i', mode, maxcolors)
            colors = colors[:maxcolors]
        sval = _ANIMATION_SPEEDS[speed]
        self._write_colors(cid, mode, colors, sval)
        self.device.release()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to use a speed profile."""
        if channel != 'pump':
            assert False, 'kraken X3 devices only support changing pump speeds'
        header = [0x72, 0x01, 0x00, 0x00]
        norm = normalize_profile(profile, _CRITICAL_TEMPERATURE)
        interp = [(interpolate_profile(norm, t)) for t in range(20, 60)]
        LOGGER.debug('setting pump curve: %s', [(num + 20, duty) for (num, duty) in enumerate(interp)])
        self._write(header + interp)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        duty = clamp(duty, 20, 100)
        self.set_speed_profile(channel, [(i, duty) for i in range(20, 60)])
        self.device.release()

    def _read(self):
        data = self.device.read(_READ_LENGTH)
        self.device.release()
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in data))
        return data

    def _read_until(self, parsers):
        for _ in range(_MAX_READ_ATTEMPTS):
            msg = self.device.read(_READ_LENGTH)
            LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                func(msg)
            if not parsers:
                return
        assert False, f'missing messages (attempts={_MAX_READ_ATTEMPTS}, missing={len(parsers)})'

    def _write(self, data):
        padding = [0x0] * (_WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)', ' '.join(format(i, '02x') for i in data), len(padding))
        self.device.write(data + padding)

    def _write_colors(self, cid, mode, colors, sval):
        mval, size_variant, speed_scale, mincolors, maxcolors = _COLOR_MODES[mode]
        color_count = len(colors)
        if 'super-fixed' == mode or 'super-breathing' == mode:
            color = list(itertools.chain(*colors)) + [0x00, 0x00, 0x00] * (maxcolors - color_count)
            speed_value = _SPEED_VALUE[speed_scale][sval]
            self._write([0x22, 0x10, cid, 0x00] + color)
            self._write([0x22, 0x11, cid, 0x00])
            self._write([0x22, 0xa0, cid, 0x00, mval] + speed_value + [0x08, 0x00, 0x00, 0x80, 0x00, 0x32, 0x00, 0x00, 0x01])
        elif mode == 'wings':  # wings requires special handling
            self._write([0x22, 0x10, cid])  # clear out all independent LEDs
            self._write([0x22, 0x11, cid])  # clear out all independent LEDs
            color_lists = {}
            color_lists[0] = colors[0] * 2
            color_lists[1] = [int(x // 2.5) for x in color_lists[0]]
            color_lists[2] = [int(x // 4) for x in color_lists[1]]
            color_lists[3] = [0x00] * 8
            for i in range(8):   #  send color scheme first, before enabling wings mode
                mod = 0x05 if i in [3, 7] else 0x01
                speed_value = _SPEED_VALUE[speed_scale][sval]
                direction = [0x04, 0x84] if i // 4 == 0 else [0x84, 0x04]
                msg = ([0x22, 0x20, cid, i, 0x04] + speed_value + [mod] + [0x00] * 7 + [0x02] + direction + [0x00] * 10)
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
            if 'backwards' in mode:
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
