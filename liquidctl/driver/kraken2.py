"""liquidctl drivers for third generation NZXT Kraken X and M liquid coolers.

Kraken X (X42, X52, X62 and X72)
--------------------------------

These coolers house 5-th generation Asetek pumps with additional PCBs for
advanced control and RGB capabilites.

Kraken M22
----------

The Kraken M22 shares similar RGB funcionality to the X models of the same
generation, but has no liquid temperature sensor and no hability to report or
set fan or pump speeds.

Copyright (C) 2018–2021  Jonas Malaco and contributors

Incorporates work by leaty, Ksenija Stanojevic, Alexander Tong and Jens
Neumaier.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp, normalize_profile, interpolate_profile

_LOGGER = logging.getLogger(__name__)

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
    'marquee-3':                     (0x03, 0x00, 0x00, 1, 1, True),
    'marquee-4':                     (0x03, 0x00, 0x08, 1, 1, True),
    'marquee-5':                     (0x03, 0x00, 0x10, 1, 1, True),
    'marquee-6':                     (0x03, 0x00, 0x18, 1, 1, True),
    'covering-marquee':              (0x04, 0x00, 0x00, 1, 8, True),
    'alternating':                   (0x05, 0x00, 0x00, 2, 2, True),
    'moving-alternating':            (0x05, 0x08, 0x00, 2, 2, True),
    'breathing':                     (0x06, 0x00, 0x00, 1, 8, False),  # colors for each step
    'super-breathing':               (0x06, 0x00, 0x00, 1, 9, False),  # one step, independent logo + ring leds
    'pulse':                         (0x07, 0x00, 0x00, 1, 8, False),
    'tai-chi':                       (0x08, 0x00, 0x00, 2, 2, True),
    'water-cooler':                  (0x09, 0x00, 0x00, 0, 0, True),
    'loading':                       (0x0a, 0x00, 0x00, 1, 1, True),
    'wings':                         (0x0c, 0x00, 0x00, 1, 1, True),
    'super-wave':                    (0x0d, 0x00, 0x00, 1, 8, True),  # independent ring leds
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
_WRITE_ENDPOINT = 0x1
_WRITE_LENGTH = 65


class Kraken2(UsbHidDriver):
    """Third generation NZXT Kraken X or M liquid cooler."""

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

    def __init__(self, device, description, device_type=DEVICE_KRAKENX, **kwargs):
        super().__init__(device, description)
        self.device_type = device_type
        self.supports_lighting = True
        self.supports_cooling = self.device_type != self.DEVICE_KRAKENM
        self._supports_cooling_profiles = None  # physical storage/later inferred from fw version
        self._connected = False

    def connect(self, **kwargs):
        ret = super().connect(**kwargs)
        self._connected = True
        return ret

    def disconnect(self, **kwargs):
        super().disconnect(**kwargs)
        self._connected = False

    def initialize(self, **kwargs):
        # before v1.1 `initialize` was used to connect to the device; that has
        # since been deprecated, but we have to support that usage until v2
        if not self._connected:
            self.connect(**kwargs)

    def finalize(self):
        """Deprecated."""
        _LOGGER.warning('deprecated: use disconnect() instead')
        if self._connected:
            self.disconnect()

    def get_status(self, **kwargs):
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

    def set_color(self, channel, mode, colors, speed='normal', direction='forward', **kwargs):
        """Set the color mode for a specific channel."""
        if not self.supports_lighting:
            raise NotSupportedByDevice()

        channel = channel.lower()
        mode = mode.lower()
        speed = speed.lower()
        direction = direction.lower()

        if mode == 'super':
            _LOGGER.warning('deprecated mode, move to super-fixed, super-breathing or super-wave')
            mode = 'super-fixed'
        if 'backwards' in mode:
            _LOGGER.warning('deprecated mode, move to direction=backwards option')
            mode = mode.replace('backwards-', '')
            direction = 'backward'

        mval, mod2, mod4, mincolors, maxcolors, ringonly = _COLOR_MODES[mode]

        if direction == 'backward':
            mod2 += 0x10

        if ringonly and channel != 'ring':
            _LOGGER.warning('mode=%s unsupported with channel=%s, dropping to ring',
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

    def _generate_steps(self, colors, mincolors, maxcolors, mode, ringonly):
        colors = list(colors)
        if len(colors) < mincolors:
            raise ValueError(f'not enough colors for mode={mode}, at least {mincolors} required')
        elif maxcolors == 0:
            if len(colors) > 0:
                _LOGGER.warning('too many colors for mode=%s, none needed', mode)
            colors = [(0, 0, 0)]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            _LOGGER.warning('too many colors for mode=%s, dropping to %d',
                            mode, maxcolors)
            colors = colors[:maxcolors]
        # generate steps from mode and colors: usually each color set by the user generates
        # one step, where it is specified to all leds and the device handles the animation;
        # but in super mode there is a single step and each color directly controls a led
        if 'super' not in mode:
            steps = [(color,)*9 for color in colors]
        elif ringonly:
            steps = [[(0, 0, 0)] + colors]
        else:
            steps = [colors]
        return steps

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to use a speed profile."""
        if not self.supports_cooling_profiles:
            raise NotSupportedByDevice()
        norm = normalize_profile(profile, _CRITICAL_TEMPERATURE)
        # due to a firmware limitation the same set of temperatures must be
        # used on both channels; we reduce the number of writes by trimming the
        # interval and/or resolution to the most useful range
        stdtemps = list(range(20, 50)) + list(range(50, 60, 2)) + [60]
        interp = [(t, interpolate_profile(norm, t)) for t in stdtemps]
        cbase, dmin, dmax = _SPEED_CHANNELS[channel]
        for i, (temp, duty) in enumerate(interp):
            duty = clamp(duty, dmin, dmax)
            _LOGGER.info('setting %s PWM duty to %d%% for liquid temperature >= %d°C',
                         channel, duty, temp)
            self._write([0x2, 0x4d, cbase + i, temp, duty])

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed."""
        if not self.supports_cooling:
            raise NotSupportedByDevice()
        elif self.supports_cooling_profiles:
            self.set_speed_profile(channel, [(0, duty), (59, duty), (60, 100), (100, 100)])
        else:
            self.set_instantaneous_speed(channel, duty)

    def set_instantaneous_speed(self, channel, duty, **kwargs):
        """Set channel to speed, but do not ensure persistence."""
        if not self.supports_cooling:
            raise NotSupportedByDevice()
        cbase, dmin, dmax = _SPEED_CHANNELS[channel]
        duty = clamp(duty, dmin, dmax)
        _LOGGER.info('setting %s PWM duty to %d%%', channel, duty)
        self._write([0x2, 0x4d, cbase & 0x70, 0, duty])

    @property
    def supports_cooling_profiles(self):
        if self._supports_cooling_profiles is None:
            if self.supports_cooling:
                self._read(clear_first=False)
                self._supports_cooling_profiles = self._firmware_version >= (3, 0, 0)
            else:
                self._supports_cooling_profiles = False
        return self._supports_cooling_profiles

    def _read(self, clear_first=True):
        if clear_first:
            self.device.clear_enqueued_reports()
        msg = self.device.read(_READ_LENGTH)
        self._firmware_version = (msg[0xb], msg[0xc] << 8 | msg[0xd], msg[0xe])
        return msg

    def _write(self, data):
        padding = [0x0]*(_WRITE_LENGTH - len(data))
        self.device.write(data + padding)


# deprecated aliases
KrakenTwoDriver = Kraken2
