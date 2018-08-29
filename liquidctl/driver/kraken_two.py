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
import sys

import usb.core
import usb.util

import liquidctl.util

SUPPORTED_DEVICES = [   # (vendor, product, description)
    (0x1e71, 0x170e, 'NZXT Kraken X (X42, X52, X62 or X72)'),
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
    'fixed':                         (0x00, 0x00, 0x00, 1, 1, False),
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
    'covering-marquee':              (0x04, 0x00, 0x00, 2, 8, True),
    'covering-backwards-marquee':    (0x04, 0x10, 0x00, 2, 8, True),
    'alternating':                   (0x05, 0x00, 0x00, 2, 2, True),
    'moving-alternating':            (0x05, 0x08, 0x00, 2, 2, True),
    'breathing':                     (0x06, 0x00, 0x00, 1, 8, False),
    'pulse':                         (0x07, 0x00, 0x00, 1, 8, False),
    'tai-chi':                       (0x08, 0x00, 0x00, 2, 2, True),
    'water-cooler':                  (0x09, 0x00, 0x00, 0, 0, True),
    'loading':                       (0x0a, 0x00, 0x00, 1, 1, True),
    'wings':                         (0x0c, 0x00, 0x00, 1, 1, True),

    # supercharged control: set logo + each of the 8 ring leds separately
    'super':                         (0x00, 0x00, 0x00, 9, 9, False),
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


class KrakenTwoDriver:
    """USB driver for third generation NZXT Kraken X liquid coolers."""

    def __init__(self, device, description):
        self.device = device
        self.description = description
        self._should_reattach_kernel_driver = False

    @classmethod
    def find_supported_devices(cls):
        devs = []
        for vid, pid, desc in SUPPORTED_DEVICES:
            usbdevs = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
            devs = devs + [cls(i, desc) for i in usbdevs]
        return devs

    def initialize(self):
        if sys.platform.startswith('linux') and self.device.is_kernel_driver_active(0):
            liquidctl.util.debug('detaching currently active kernel driver')
            self.device.detach_kernel_driver(0)
            self._should_reattach_kernel_driver = True
        self.device.set_configuration()

    def finalize(self):
        usb.util.dispose_resources(self.device)
        if self._should_reattach_kernel_driver:
            liquidctl.util.debug('reattaching previously active kernel driver')
            self.device.attach_kernel_driver(0)

    def get_status(self):
        msg = self.device.read(READ_ENDPOINT, READ_LENGTH, READ_TIMEOUT)
        liquidctl.util.debug('read {}'.format(' '.join(format(i, '02x') for i in msg)))
        firmware = '{}.{}.{}'.format(msg[0xb], msg[0xc] << 8 | msg[0xd], msg[0xe])
        return [
            ('Liquid temperature', msg[1] + msg[2]/10, '°C'),
            ('Fan speed', msg[3] << 8 | msg[4], 'rpm'),
            ('Pump speed', msg[5] << 8 | msg[6], 'rpm'),
            ('Firmware version', firmware, '')
        ]

    def set_color(self, channel, mode, colors, speed):
        mval, mod2, mod4, mincolors, maxcolors, ringonly = COLOR_MODES[mode]
        colors = list(colors)
        if ringonly and channel != 'ring':
            liquidctl.util.debug('mode={} unsupported with channel={}, dropping to ring'.format(mode, channel))
            channel = 'ring'
        if len(colors) < mincolors:
            raise ValueError('Not enough colors for mode={}, at least {} required'.format(mode, mincolors))
        elif maxcolors == 0:
            colors = [(0xff,0xff,0xff)]
        elif len(colors) > maxcolors:
            liquidctl.util.debug('too many colors for mode={}, dropping to {}'.format(mode, maxcolors))
            colors = colors[:maxcolors]
        # from mode and colors generate the steps
        if mode == 'super':
            steps = list(zip(*[iter(colors)]*9))
        else:
            steps = [(color,)*9 for color in colors]
        sval = ANIMATION_SPEEDS[speed]
        byte2 = mod2 | COLOR_CHANNELS[channel]
        for i, colors in enumerate(steps):
            seq = i << 5
            byte4 = sval | seq | mod4
            textcolor = [colors[0][1], colors[0][0], colors[0][2]]
            ringcolor = list(itertools.chain(*colors[1:]))
            self._write([0x2, 0x4c, byte2, mval, byte4] + textcolor + ringcolor)

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
            liquidctl.util.debug('for liquid temperature >= {}°C, setting {} PWM duty to {}%'
                                 .format(temp, channel, duty))
            self._write([0x2, 0x4d, cbase + i, temp, duty])

    def set_fixed_speed(self, channel, speed):
        self.set_speed_profile(channel, [(0, speed), (59, speed), (60, 100), (100, 100)])

    def _write(self, data):
        liquidctl.util.debug('write {}'.format(' '.join(format(i, '02x') for i in data)))
        padding = [0x0]*(WRITE_LENGTH - len(data))
        if liquidctl.util.dryrun:
            return
        self.device.write(WRITE_ENDPOINT, data + padding, WRITE_TIMEOUT)
