"""USB driver for third generation NZXT Kraken X and M liquid coolers.


Kraken X (X42, X52, X62 and X72)
--------------------------------

These coolers house 5-th generation Asetek pumps with additional PCBs for
advanced control and RGB capabilites.


Kraken M22
----------

The Kraken M22 shares similar RGB funcionality to the X models of the same
generation, but has no liquid temperature sensor and no hability to report or
set fan or pump speeds.


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
from liquidctl.driver.usb import UsbHidDriver


LOGGER = logging.getLogger(__name__)

_SPEED_CHANNELS = {  # (base, minimum duty, maximum duty)
    'fan':   (0x80, 25, 100),
    'pump':  (0xc0, 50, 100),
}
_CRITICAL_TEMPERATURE = 60
_COLOR_CHANNELS = {
    'sync':     0x0,
    'logo':     0x1,
    'ring':     0x2,
}
_COLOR_MODES = {
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
_ANIMATION_SPEEDS = {
    'slowest':  0x0,
    'slower':   0x1,
    'normal':   0x2,
    'faster':   0x3,
    'fastest':  0x4,
}
_READ_ENDPOINT = 0x81
_READ_LENGTH = 64
_READ_TIMEOUT = 2000
_WRITE_ENDPOINT = 0x1
_WRITE_LENGTH = 65
_WRITE_TIMEOUT = 2000


class KrakenTwoDriver(UsbHidDriver):
    """USB driver for third generation NZXT Kraken X and M liquid coolers."""

    DEVICE_KRAKENX = 'Kraken X'
    DEVICE_KRAKENM = 'Kraken M'
    SUPPORTED_DEVICES = [
        (0x1e71, 0x170e, None, 'NZXT Kraken X (X42, X52, X62 or X72)', {
            'device_type': DEVICE_KRAKENX
        }),
        (0x1e71, 0x1715, None, 'NZXT Kraken M22', {
            'device_type': DEVICE_KRAKENM
        }),
    ]

    def __init__(self, device, description, device_type=DEVICE_KRAKENX, dry_run=False, **kwargs):
        super().__init__(device, description)
        self.device_type = device_type
        self.supports_lighting = True
        self.supports_cooling = self.device_type != self.DEVICE_KRAKENM
        self._supports_cooling_profiles = None  # physical storage/later inferred from fw version
        self.dry_run = dry_run

    def get_status(self):
        """Get a status report.

        Returns a list of (key, value, unit) tuples.
        """
        msg = self._read()
        firmware = '{}.{}.{}'.format(*self._firmware_version)
        if self.device_type == self.DEVICE_KRAKENM:
            return [('Firmware version', firmware, '')]
        else:
            return [
                ('Liquid temperature', msg[1] + msg[2]/10, '°C'),
                ('Fan speed', msg[3] << 8 | msg[4], 'rpm'),
                ('Pump speed', msg[5] << 8 | msg[6], 'rpm'),
                ('Firmware version', firmware, '')
            ]

    def set_color(self, channel, mode, colors, speed):
        """Set the color mode for a specific channel."""
        if not self.supports_lighting:
            raise NotImplementedError()
        if mode == 'super':
            LOGGER.warning('deprecated mode, update to super-fixed, super-breathing or super-wave')
            mode = 'super-fixed'
        mval, mod2, mod4, mincolors, maxcolors, ringonly = _COLOR_MODES[mode]
        if ringonly and channel != 'ring':
            LOGGER.warning('mode=%s unsupported with channel=%s, dropping to ring',
                           mode, channel)
            channel = 'ring'
        steps = self._generate_steps(colors, mincolors, maxcolors, mode, ringonly)
        sval = _ANIMATION_SPEEDS[speed]
        byte2 = mod2 | _COLOR_CHANNELS[channel]
        for i, leds in enumerate(steps):
            seq = i << 5
            byte4 = sval | seq | mod4
            logo = [leds[0][1], leds[0][0], leds[0][2]]
            ring = list(itertools.chain(*leds[1:]))
            self._write([0x2, 0x4c, byte2, mval, byte4] + logo + ring)
        self.device.release()

    def _generate_steps(self, colors, mincolors, maxcolors, mode, ringonly):
        colors = list(colors)
        if len(colors) < mincolors:
            raise ValueError('Not enough colors for mode={}, at least {} required'
                             .format(mode, mincolors))
        elif maxcolors == 0:
            if len(colors) > 0:
                LOGGER.warning('too many colors for mode=%s, none needed', mode)
            colors = [(0, 0, 0)]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            LOGGER.warning('too many colors for mode=%s, dropping to %i',
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
        """Set channel to use a speed profile."""
        if not self.supports_cooling_profiles:
            raise NotImplementedError()
        cbase, dmin, dmax = _SPEED_CHANNELS[channel]
        # ideally we could just call normalize_profile (optionally followed by autofill_profile),
        # but Kraken devices currently require the same set of temperatures on both channels
        stdtemps = range(20, 62, 2)
        tmp = liquidctl.util.normalize_profile(profile, _CRITICAL_TEMPERATURE)
        norm = [(t, liquidctl.util.interpolate_profile(tmp, t)) for t in stdtemps]
        for i, (temp, duty) in enumerate(norm):
            if duty < dmin:
                duty = dmin
            elif duty > dmax:
                duty = dmax
            LOGGER.info('setting %s PWM duty to %i%% for liquid temperature >= %i°C',
                         channel, duty, temp)
            self._write([0x2, 0x4d, cbase + i, temp, duty])
        self.device.release()

    def set_fixed_speed(self, channel, speed):
        """Set channel to a fixed speed."""
        if not self.supports_cooling:
            raise NotImplementedError()
        elif self.supports_cooling_profiles:
            self.set_speed_profile(channel, [(0, speed), (59, speed), (60, 100), (100, 100)])
        else:
            self.set_instantaneous_speed(channel, speed)

    def set_instantaneous_speed(self, channel, speed):
        """Set channel to speed, but do not ensure persistence."""
        if not self.supports_cooling:
            raise NotImplementedError()
        cbase, smin, smax = _SPEED_CHANNELS[channel]
        if speed < smin:
            speed = smin
        elif speed > smax:
            speed = smax
        LOGGER.info('setting %s PWM duty to %i%%', channel, speed)
        self._write([0x2, 0x4d, cbase & 0x70, 0, speed])
        self.device.release()

    @property
    def supports_cooling_profiles(self):
        if self._supports_cooling_profiles is None:
            if self.supports_cooling:
                self._read()
                self._supports_cooling_profiles = self._firmware_version >= (3, 0, 0)
            else:
                self._supports_cooling_profiles = False
        return self._supports_cooling_profiles

    def _read(self):
        msg = self.device.read(_READ_LENGTH)
        self.device.release()
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
        self._firmware_version = (msg[0xb], msg[0xc] << 8 | msg[0xd], msg[0xe])
        return msg

    def _write(self, data):
        padding = [0x0]*(_WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        if self.dry_run:
            return
        self.device.write(data + padding)

    def initialize(self):
        """NOOP."""
        self.connect()  # deprecated behavior from v1.0.0

    def finalize(self):
        """Deprecated."""
        LOGGER.warning('deprecated: use disconnect() instead')
        self.disconnect()

