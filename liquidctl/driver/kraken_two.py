"""USB driver for third generation NZXT Kraken X liquid coolers.

These coolers (X72, X62, X52 and X42) are made by Asetek, housing a 5-th
generation pump and a second PCB for advanced RGB LED capabilites.

Note: the Kraken M22 shares similar RGB funcionality, but is otherwise very
different: made by Apaltek, it has no liquid temperature sensor and no fan or
pump speed readings or control.  This driver does not support it at the moment,
but its lighting control scheme is likely similar.

Copyright (C) 2018  Jonas Malaco
Copyright (C) 2018  each contribution's author

Incorporates work by leaty, KsenijaS, Alexander Tong and Jens Neumaier, under
the terms of the GNU General Public License.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import itertools
import logging

import liquidctl.util
from liquidctl.driver.base_usb import BaseUsbDriver


logger = logging.getLogger(__name__)

SUPPORTED_DEVICES = [
    (0x1e71, 0x170e, None, 'NZXT Kraken X (X42, X52, X62 or X72)', {}),
]
SPEED_CHANNELS = {  # (base, minimum duty, maximum duty)
    'fan':   (0x80, 25, 100),
    'pump':  (0xc0, 60, 100),  # firmware accepts 50% but keep CAM's safety margin
}
COLOR_CHANNELS = {
    'sync':     0x0,
    'logo':     0x1,
    'ring':     0x2,
}
COLOR_MODES = {
    # (byte3/mode, byte2/reverse, byte4/modifier, min colors, max colors, only ring)
    'off':                           (0x00, 0x00, 0x00, 0, 0, False),
    'fixed':                         (0x00, 0x00, 0x00, 1, 1, False),
    'super-fixed':                   (0x00, 0x00, 0x00, 1, 9, False),  # independent logo + ring leds
    'fading':                        (0x01, 0x00, 0x00, 2, 8, False),
    'spectrum-wave':                 (0x02, 0x00, 0x00, 0, 0, False),
    'backwards-spectrum-wave':       (0x02, 0x10, 0x00, 0, 0, False),
    'marquee-3':                     (0x03, 0x00, 0x00, 1, 1, True),
    'marquee-4':                     (0x03, 0x00, 0x08, 1, 1, True),
    'marquee-5':                     (0x03, 0x00, 0x10, 1, 1, True),
    'marquee-6':                     (0x03, 0x00, 0x18, 1, 1, True),
    'backwards-marquee-3':           (0x03, 0x10, 0x00, 1, 1, True),
    'backwards-marquee-4':           (0x03, 0x10, 0x08, 1, 1, True),
    'backwards-marquee-5':           (0x03, 0x10, 0x10, 1, 1, True),
    'backwards-marquee-6':           (0x03, 0x10, 0x18, 1, 1, True),
    'covering-marquee':              (0x04, 0x00, 0x00, 1, 8, True),
    'covering-backwards-marquee':    (0x04, 0x10, 0x00, 1, 8, True),
    'alternating':                   (0x05, 0x00, 0x00, 2, 2, True),
    'moving-alternating':            (0x05, 0x08, 0x00, 2, 2, True),
    'backwards-moving-alternating':  (0x05, 0x18, 0x00, 2, 2, True),
    'breathing':                     (0x06, 0x00, 0x00, 1, 8, False),  # colors for each step
    'super-breathing':               (0x06, 0x00, 0x00, 1, 9, False),  # one step, independent logo + ring leds
    'pulse':                         (0x07, 0x00, 0x00, 1, 8, False),
    'tai-chi':                       (0x08, 0x00, 0x00, 2, 2, True),
    'water-cooler':                  (0x09, 0x00, 0x00, 0, 0, True),
    'loading':                       (0x0a, 0x00, 0x00, 1, 1, True),
    'wings':                         (0x0c, 0x00, 0x00, 1, 1, True),
    'super-wave':                    (0x0d, 0x00, 0x00, 1, 8, True),  # independent ring leds
    'backwards-super-wave':          (0x0d, 0x10, 0x00, 1, 8, True),  # independent ring leds
}
ANIMATION_SPEEDS = {
    'slowest':  0x0,
    'slower':   0x1,
    'normal':   0x2,
    'faster':   0x3,
    'fastest':  0x4,
}
READ_ENDPOINT = 0x81
READ_LENGTH = 64
READ_TIMEOUT = 2000
WRITE_ENDPOINT = 0x1
WRITE_LENGTH = 65
WRITE_TIMEOUT = 2000


class KrakenTwoDriver(BaseUsbDriver):
    """USB driver for third generation NZXT Kraken X liquid coolers."""

    supported_devices = SUPPORTED_DEVICES

    def get_status(self):
        msg = self.device.read(READ_ENDPOINT, READ_LENGTH, READ_TIMEOUT)
        logger.debug('received %s', ' '.join(format(i, '02x') for i in msg))
        firmware = '{}.{}.{}'.format(msg[0xb], msg[0xc] << 8 | msg[0xd], msg[0xe])
        return [
            ('Liquid temperature', msg[1] + msg[2]/10, '°C'),
            ('Fan speed', msg[3] << 8 | msg[4], 'rpm'),
            ('Pump speed', msg[5] << 8 | msg[6], 'rpm'),
            ('Firmware version', firmware, '')
        ]

    def set_color(self, channel, mode, colors, speed):
        if mode == 'super':
            logger.warning('deprecated mode, update to super-fixed, super-breathing or super-wave')
            mode = 'super-fixed'
        mval, mod2, mod4, mincolors, maxcolors, ringonly = COLOR_MODES[mode]
        if ringonly and channel != 'ring':
            logger.warning('mode=%s unsupported with channel=%s, dropping to ring',
                           mode, channel)
            channel = 'ring'
        steps = self._generate_steps(colors, mincolors, maxcolors, mode, ringonly)
        sval = ANIMATION_SPEEDS[speed]
        byte2 = mod2 | COLOR_CHANNELS[channel]
        for i, leds in enumerate(steps):
            seq = i << 5
            byte4 = sval | seq | mod4
            logo = [leds[0][1], leds[0][0], leds[0][2]]
            ring = list(itertools.chain(*leds[1:]))
            self._write([0x2, 0x4c, byte2, mval, byte4] + logo + ring)

    def _generate_steps(self, colors, mincolors, maxcolors, mode, ringonly):
        colors = list(colors)
        if len(colors) < mincolors:
            raise ValueError('Not enough colors for mode={}, at least {} required'
                             .format(mode, mincolors))
        elif maxcolors == 0:
            if len(colors) > 0:
                logger.warning('too many colors for mode=%s, none needed', mode)
            colors = [(0, 0, 0)]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            logger.warning('too many colors for mode=%s, dropping to %i',
                           mode, maxcolors)
            colors = colors[:maxcolors]
        # generate steps from mode and colors: usually each color set by the user generates
        # one step, where it is specified to all leds and the device handles the animation;
        # but in super mode there is a single step and each color directly controls a led
        if not 'super' in mode:
            steps = [(color,)*9 for color in colors]
        elif ringonly:
            steps = [[(0,0,0)] + colors]
        else:
            steps = [colors]
        return steps

    def set_speed_profile(self, channel, profile):
        cbase, dmin, dmax = SPEED_CHANNELS[channel]
        # ideally we could just call normalize_profile (optionally followed by autofill_profile),
        # but Kraken devices currently require the same set of temperatures on both channels
        stdtemps = range(20, 62, 2)
        tmp = liquidctl.util.normalize_profile(profile, 60)
        norm = [(t, liquidctl.util.interpolate_profile(tmp, t)) for t in stdtemps]
        for i, (temp, duty) in enumerate(norm):
            if duty < dmin:
                duty = dmin
            elif duty > dmax:
                duty = dmax
            logger.info('setting %s PWM duty to %i%% for liquid temperature >= %i°C',
                         channel, duty, temp)
            self._write([0x2, 0x4d, cbase + i, temp, duty])

    def set_fixed_speed(self, channel, speed):
        self.set_speed_profile(channel, [(0, speed), (59, speed), (60, 100), (100, 100)])

    def _write(self, data):
        padding = [0x0]*(WRITE_LENGTH - len(data))
        logger.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        if self.dry_run:
            return
        self.device.write(WRITE_ENDPOINT, data + padding, WRITE_TIMEOUT)

    def initialize(self):
        # deprecated behavior: connect to the Kraken
        self.connect()

    def finalize(self):
        # deprecated: disconnect from the Kraken
        self.disconnect()

