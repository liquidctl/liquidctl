"""USB driver for the NZXT Smart Device.

The device is a fan and LED controller that ships with the H200i, H400i, H500i
and H700i cases.

It provides three independent fan channels with standard 4-pin connectors.
Both PWM and DC control is supported, and the device automatically chooses the
appropriate mode.

Additionally, up to four chained HUE+ LED strips can be driven from a single
channel.  The firmware installed on the device exposes several presets, most of
them familiar to other NZXT products.

A microphone is also present onboard, for  noise level optimization through CAM
and AI.

This driver implements all features available at the hardware level:

 - initialize
 - detect connected fans and LED strips
 - control fan speed per channel
 - monitor fan presence, control mode, speed, voltage and current
 - customize and apply color modes
 - report LED strip count
 - monitor the noise level with the onboard microphone
 - report the firmware version

After powering on from Mechanical Off, or if there have been hardware changes,
the device must be initilizated by calling `initialize()`: connected fans and
LED strips will be detected and data reporting will begin.

Software based features offered by CAM, like noise level optimization, have not
been implemented.

Copyright (C) 2018  Jonas Malaco
Copyright (C) 2018  each contribution's author

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
    (0x1e71, 0x1714, None, 'NZXT Smart Device', {}),
]
SPEED_CHANNELS = {  # (base, minimum duty, maximum duty)
    'fan1': (0x00, 0, 100),
    'fan2': (0x01, 0, 100),
    'fan3': (0x02, 0, 100),
}
COLOR_CHANNELS = {
    'led': 0x0,
}
COLOR_MODES = {
    # (byte2/mode, byte3/variant, byte4/size, min colors, max colors)
    'off':                           (0x00, 0x00, 0x00, 0, 0),
    'fixed':                         (0x00, 0x00, 0x00, 1, 1),
    'super-fixed':                   (0x00, 0x00, 0x00, 1, 40),  # independent leds
    'fading':                        (0x01, 0x00, 0x00, 1, 8),
    'spectrum-wave':                 (0x02, 0x00, 0x00, 0, 0),
    'backwards-spectrum-wave':       (0x02, 0x10, 0x00, 0, 0),
    'marquee-3':                     (0x03, 0x00, 0x00, 1, 1),
    'marquee-4':                     (0x03, 0x00, 0x08, 1, 1),
    'marquee-5':                     (0x03, 0x00, 0x10, 1, 1),
    'marquee-6':                     (0x03, 0x00, 0x18, 1, 1),
    'backwards-marquee-3':           (0x03, 0x10, 0x00, 1, 1),
    'backwards-marquee-4':           (0x03, 0x10, 0x08, 1, 1),
    'backwards-marquee-5':           (0x03, 0x10, 0x10, 1, 1),
    'backwards-marquee-6':           (0x03, 0x10, 0x18, 1, 1),
    'covering-marquee':              (0x04, 0x00, 0x00, 1, 8),
    'covering-backwards-marquee':    (0x04, 0x10, 0x00, 1, 8),
    'alternating':                   (0x05, 0x00, 0x00, 2, 2),
    'moving-alternating':            (0x05, 0x08, 0x00, 2, 2),
    'backwards-moving-alternating':  (0x05, 0x18, 0x00, 2, 2),
    'pulse':                         (0x06, 0x00, 0x00, 1, 8),
    'breathing':                     (0x07, 0x00, 0x00, 1, 8),  # colors for each step
    'super-breathing':               (0x07, 0x00, 0x00, 1, 40),  # one step, independent leds
    'candle':                        (0x09, 0x00, 0x00, 1, 1),
    'wings':                         (0x0c, 0x00, 0x00, 1, 1),
    'super-wave':                    (0x0d, 0x00, 0x00, 1, 40),  # independent ring leds
    'backwards-super-wave':          (0x0d, 0x10, 0x00, 1, 40),  # independent ring leds
}
ANIMATION_SPEEDS = {
    'slowest':  0x0,
    'slower':   0x1,
    'normal':   0x2,
    'faster':   0x3,
    'fastest':  0x4,
}
READ_ENDPOINT = 0x81
READ_LENGTH = 21
READ_TIMEOUT = 2000
WRITE_ENDPOINT = 0x1
WRITE_LENGTH = 65
WRITE_TIMEOUT = 2000


class NzxtSmartDeviceDriver(BaseUsbDriver):
    """USB driver to a NZXT Smart Device."""

    supported_devices = SUPPORTED_DEVICES

    def initialize(self):
        self._write([0x1, 0x5c])  # initialize/detect connected devices and their type
        self._write([0x1, 0x5d])  # start reporting

    def get_status(self):
        status = []
        noise = []
        for i in range(0, 3):
            msg = self.device.read(READ_ENDPOINT, READ_LENGTH, READ_TIMEOUT)
            logger.debug('received %s', ' '.join(format(i, '02x') for i in msg))
            num = (msg[15] >> 4) + 1
            state = msg[15] & 0x3
            status.append(('Fan {}'.format(num), ['—', 'DC', 'PWM'][state], ''))
            noise.append(msg[1])
            if state:
                status.append(('Fan {} speed'.format(num), msg[3] << 8 | msg[4], 'rpm'))
                status.append(('Fan {} voltage'.format(num), msg[7] + msg[8]/100, 'V'))
                status.append(('Fan {} current'.format(num), msg[10]/100, 'A'))
            if i == 0:
                fw = '{}.{}.{}'.format(msg[0xb], msg[0xc] << 8 | msg[0xd], msg[0xe])
                status.append(( 'Firmware version', fw, ''))
                status.append(( 'LED strips', msg[0x11], ''))
        status.append(('Noise level', round(sum(noise)/len(noise)), 'dB'))
        return sorted(status)

    def set_color(self, channel, mode, colors, speed):
        mval, mod3, mod4, mincolors, maxcolors = COLOR_MODES[mode]
        colors = [[g, r, b] for [r, g, b] in colors]
        if len(colors) < mincolors:
            raise ValueError('Not enough colors for mode={}, at least {} required'
                             .format(mode, mincolors))
        elif maxcolors == 0:
            colors = [[0, 0, 0]]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            logger.warning('too many colors for mode=%s, dropping to %i',
                           mode, maxcolors)
            colors = colors[:maxcolors]
        # generate steps from mode and colors: usually each color set by the user generates
        # one step, where it is specified to all leds and the device handles the animation;
        # but in super mode there is a single step and each color directly controls a led
        if 'super' in mode:
            steps = [list(itertools.chain(*colors))]
        else:
            steps = [color*40 for color in colors]
        sval = ANIMATION_SPEEDS[speed]
        for i, leds in enumerate(steps):
            seq = i << 5
            byte4 = sval | seq | mod4
            self._write([0x2, 0x4b, mval, mod3, byte4] + leds[0:57])
            self._write([0x3] + leds[57:])

    def set_fixed_speed(self, channel, duty):
        cid, dmin, dmax = SPEED_CHANNELS[channel]
        if duty < dmin:
            duty = dmin
        elif duty > dmax:
            duty = dmax
        self._write([0x2, 0x4d, cid, 0, duty])

    def _write(self, data):
        padding = [0x0]*(WRITE_LENGTH - len(data))
        logger.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        if self.dry_run:
            return
        self.device.write(WRITE_ENDPOINT, data + padding, WRITE_TIMEOUT)

