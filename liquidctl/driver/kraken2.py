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

Copyright (C) 2018–2022  Jonas Malaco and contributors

Incorporates work by leaty, Ksenija Stanojevic, Alexander Tong and Jens
Neumaier.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp, normalize_profile, interpolate_profile, \
                           map_direction

_LOGGER = logging.getLogger(__name__)

_SPEED_CHANNELS = {  # (base, minimum duty, maximum duty)
    'fan':   (0x80, 0, 100),
    'pump':  (0xc0, 0, 100),
}

_STATUS_TEMPERATURE = 'Liquid temperature'
_STATUS_FAN_SPEED = 'Fan speed'
_STATUS_PUMP_SPEED = 'Pump speed'
_STATUS_FWVERSION = 'Firmware version'

# more aggressive than observed 4.0.3 and 6.0.2 firmware defaults
_RESET_FAN_PROFILE = [(20, 25), (30, 50), (50, 90), (60, 100)]
_RESET_PUMP_PROFILE = [(20, 50), (30, 60), (40, 90), (50, 100)]

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

    # support for hwmon: nzxt-kraken2, Linux 5.13

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
        self._firmware_version = None  # read once necessary

    def initialize(self, **kwargs):
        """Initialize the device and the driver.

        This method should be called every time the systems boots, resumes from
        a suspended state, or if the device has just been (re)connected.  In
        those scenarios, no other method, except `connect()` or `disconnect()`,
        should be called until the device and driver has been (re-)initialized.

        Returns None or a list of `(property, value, unit)` tuples, similarly
        to `get_status()`.
        """

        if self.supports_cooling_profiles:
            # due to a firmware limitation the same set of temperatures must be
            # used on both channels; ensure that is always true, even if the
            # user later only changes one of them, by resetting the profiles
            self.set_speed_profile('fan', _RESET_FAN_PROFILE)
            self.set_speed_profile('pump', _RESET_PUMP_PROFILE)

        firmware = '{}.{}.{}'.format(*self.firmware_version)
        return [('Firmware version', firmware, '')]

    def _get_status_directly(self, with_firmware):
        # the firmware version is duplicated here as a temporary migration aid
        # for GKraken; it will be removed once GKraken no longer needs it, or
        # in liquidctl 1.10.x, whatever happens first

        msg = self._read()

        ret = [
            (_STATUS_TEMPERATURE, msg[1] + msg[2]/10, '°C'),
            (_STATUS_FAN_SPEED, msg[3] << 8 | msg[4], 'rpm'),
            (_STATUS_PUMP_SPEED, msg[5] << 8 | msg[6], 'rpm'),
        ]

        # TODO remove
        if with_firmware:
            firmware_version = '{}.{}.{}'.format(*self.firmware_version)
            ret.append((_STATUS_FWVERSION, firmware_version, ''))

        return ret

    def _get_status_from_hwmon(self, with_firmware):
        # the firmware version is duplicated here as a temporary migration aid
        # for GKraken; it will be removed once GKraken no longer needs it, or
        # in liquidctl 1.10.x, whatever happens first

        ret = [
            (_STATUS_TEMPERATURE, self._hwmon.get_int('temp1_input') * 1e-3, '°C'),
            (_STATUS_FAN_SPEED, self._hwmon.get_int('fan1_input'), 'rpm'),
            (_STATUS_PUMP_SPEED, self._hwmon.get_int('fan2_input'), 'rpm'),
        ]

        # TODO remove
        if with_firmware:
            firmware_version = '{}.{}.{}'.format(*self.firmware_version)
            ret.append((_STATUS_FWVERSION, firmware_version, ''))

        return ret

    def get_status(self, direct_access=False, *, _internal_called_from_cli=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        if self.device_type == self.DEVICE_KRAKENM:
            return []

        # already omit the firmware version when the caller is our own cli
        with_firmware = not _internal_called_from_cli

        if self._hwmon and not direct_access:
            _LOGGER.info('bound to %s kernel driver, reading status from hwmon', self._hwmon.module)
            return self._get_status_from_hwmon(with_firmware)

        if self._hwmon:
            _LOGGER.warning('directly reading the status despite %s kernel driver',
                            self._hwmon.module)

        return self._get_status_directly(with_firmware)

    def set_color(self, channel, mode, colors, speed='normal', direction='forward', **kwargs):
        """Set the color mode for a specific channel."""

        if not self.supports_lighting:
            raise NotSupportedByDevice()

        if mode == 'super':
            _LOGGER.warning('deprecated mode, move to super-fixed, super-breathing or super-wave')
            mode = 'super-fixed'
        if 'backwards' in mode:
            _LOGGER.warning('deprecated mode, move to direction=backward option')
            mode = mode.replace('backwards-', '')
            direction = 'backward'

        mval, mod2, mod4, mincolors, maxcolors, ringonly = _COLOR_MODES[mode]
        mod2 += map_direction(direction, 0, 0x10)

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
        """Set channel to follow a speed duty profile."""

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
        """Set channel to a fixed speed duty."""

        if not self.supports_cooling:
            raise NotSupportedByDevice()
        elif self.supports_cooling_profiles:
            self.set_speed_profile(channel, [(0, duty), (59, duty), (60, 100), (100, 100)])
        else:
            self.set_instantaneous_speed(channel, duty)

    def set_instantaneous_speed(self, channel, duty, **kwargs):
        """Set channel to speed duty, but do not guarantee persistence."""

        if not self.supports_cooling:
            raise NotSupportedByDevice()
        cbase, dmin, dmax = _SPEED_CHANNELS[channel]
        duty = clamp(duty, dmin, dmax)
        _LOGGER.info('setting %s PWM duty to %d%%', channel, duty)
        self._write([0x2, 0x4d, cbase & 0x70, 0, duty])

    @property
    def supports_cooling_profiles(self):
        return self.supports_cooling and self.firmware_version >= (3, 0, 0)

    @property
    def firmware_version(self):
        if self._firmware_version is None:
            _ = self._read(clear_first=False)
        return self._firmware_version

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
