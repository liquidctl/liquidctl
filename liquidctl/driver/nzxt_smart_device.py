"""USB driver for NZXT's Smart Device from their H-series cases.

Supported features in this driver:

 - [x] set the fan speeds
 - [o] set the lighing mode and colors
 - [ ] read the fan speeds
 - [x] read the firmware version
 - [ ] read the noise level

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
import sys

import usb.core
import usb.util

import liquidctl.util

SUPPORTED_DEVICES = [   # (vendor, product, description)
    (0x1e71, 0x1714, 'NZXT Smart Device'),
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
    # (byte2/mode, byte3/modified, byte4/modifier, min colors, max colors)
    'off':                           (0x00, 0x00, 0x00, 0,  0),
    'fixed':                         (0x00, 0x00, 0x00, 1,  1),
    # supercharged control: set each of the 20 leds separately
    'super':                         (0x00, 0x00, 0x00, 0, 40),
}
ANIMATION_SPEEDS = {
    'normal':   0x2,
}
READ_ENDPOINT = 0x81
READ_LENGTH = 21
READ_TIMEOUT = 2000
WRITE_ENDPOINT = 0x1
WRITE_LENGTH = 65
WRITE_TIMEOUT = 2000


class NzxtSmartDeviceDriver:
    """USB driver for NZXT's Smart Device from their H-series cases."""

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
            ('Firmware version', firmware, '')
        ]

    def set_color(self, channel, mode, colors, speed):
        mval, mod3, mod4, mincolors, maxcolors = COLOR_MODES[mode]
        colors = [[g, r, b] for [r, g, b] in colors]
        if len(colors) < mincolors:
            raise ValueError('Not enough colors for mode={}, at least {} required'
                             .format(mode, mincolors))
        elif maxcolors == 0:
            colors = [[0, 0, 0]]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            liquidctl.util.debug('too many colors for mode={}, dropping to {}'
                                 .format(mode, maxcolors))
            colors = colors[:maxcolors]
        # generate steps from mode and colors: usually each color set by the user generates
        # one step, where it is specified to all leds and the device handles the animation;
        # but in super mode there is a single step and each color directly controls a led
        if mode == 'super':
            steps = [list(itertools.chain(*colors))]
        else:
            steps = [color*40 for color in colors] 
        sval = ANIMATION_SPEEDS[speed]
        for i, leds in enumerate(steps):
            seq = i << 5
            byte4 = sval | seq | mod4
            self._write([0x2, 0x4b, mval, mod3, byte4] + leds[0:57])
            self._write([0x3] + leds[57:])

    def set_speed_profile(self, channel, profile):
        raise NotImplementedError("The Smart Device does not support onboard speed profiles")

    def set_fixed_speed(self, channel, duty):
        cid, dmin, dmax = SPEED_CHANNELS[channel]
        if duty < dmin:
            duty = dmin
        elif duty > dmax:
            duty = dmax
        self._write([0x2, 0x4d, cid, 0, duty])

    def _write(self, data):
        liquidctl.util.debug('write {}'.format(' '.join(format(i, '02x') for i in data)))
        padding = [0x0]*(WRITE_LENGTH - len(data))
        if liquidctl.util.dryrun:
            return
        self.device.write(WRITE_ENDPOINT, data + padding, WRITE_TIMEOUT)

