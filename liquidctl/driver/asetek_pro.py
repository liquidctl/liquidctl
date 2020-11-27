"""liquidctl drivers for sixth generation Asetek 690LC liquid coolers.

Supported devices:

- Corsair H100i PRO RGB, H115i PRO RGB or H150i PRO RGB (Experimental)

Copyright (C) 2018–2020  Jonas Malaco and contributors

Incorporates or uses as reference work by Kristóf Jakab, Sean Nelson
and Chris Griffith.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging

import usb

from liquidctl.driver.asetek import Modern690Lc
from liquidctl.driver.usb import UsbDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.keyval import RuntimeStorage
from liquidctl.util import clamp


LOGGER = logging.getLogger(__name__)

_MAX_PROFILE_POINTS = 7
_CRITICAL_TEMPERATURE = 60
_HIGH_TEMPERATURE = 45
_READ_LENGTH = 32
_READ_TIMEOUT = 2000
_WRITE_TIMEOUT = 2000

_PRO_WRITE_ENDPOINT = 0x1
_PRO_READ_ENDPOINT = 0x81
_PRO_CMD_READ_FIRMWARE = 0xaa
_PRO_CMD_READ_AIO_TEMP = 0xa9
_PRO_CMD_READ_FAN_SPEED = 0x41
_PRO_CMD_WRITE_FAN_SPEED = 0x40
_PRO_CMD_READ_PUMP_SPEED = 0x31
_PRO_CMD_READ_PUMP_MODE = 0x33
_PRO_CMD_WRITE_PUMP_MODE = 0x32
_PRO_PUMP_MODES = [
    'Quiet',
    'Balanced',
    'Performance'
    ]

_PRO_SPEEDS = {
    'rainbow': [
        0x30, # slow
        0x18, # medium
        0x0C  # fast
    ],
    'shift': [
        0x46, # slow
        0x28, # medium
        0x0F  # fast
    ],
    'pulse':[
        0x50, # slow
        0x37, # medium
        0x1E  # fast
    ],
    'blinking': [
        0x0F, # slow
        0x0A, # medium
        0x05  # fast
    ]
}


class CorsairAsetekProDriver(Modern690Lc):
    """liquidctl driver for Corsair-branded sixth generation Asetek coolers."""
    SUPPORTED_DEVICES = [
        (0x1b1c, 0x0c12, None, 'Corsair Hydro H150i Pro', {}),
        (0x1b1c, 0x0c13, None, 'Corsair Hydro H115i Pro', {}),
        (0x1b1c, 0x0c14, None, 'Corsair Hydro H110i Pro', {}),
        (0x1b1c, 0x0c15, None, 'Corsair Hydro H100i Pro', {}),
        (0x1b1c, 0x0c16, None, 'Corsair Hydro H80i Pro', {}),
    ]

    def _write(self, data):
        """Write data to the AIO and log"""
        LOGGER.debug('write %s', ' '.join(format(i, '02x') for i in data))
        self.device.write(_PRO_WRITE_ENDPOINT, data, _WRITE_TIMEOUT)

    # Not calling this (or begin transaction) since they do not seem to be needed for H100i Pro
    def _end_transaction_and_read(self, length=_READ_LENGTH):
        """End the transaction by reading from the device.
        According to the official documentation, as well as Craig's open-source
        implementation (libSiUSBXp), it should be necessary to check the queue
        size and read data in chunks.  However, leviathan and its derivatives
        seem to work fine without this complexity; we currently try the same
        approach.
        """
        msg = self.device.read(_PRO_READ_ENDPOINT, length, _READ_TIMEOUT)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
        self.device.release()
        return msg

    def _write_color_change_speed(self, mode, speed):
        """Send the speed to cycle colors on the RGB pump"""
        if speed < 1 or speed > 3:
            raise ValueError('Unsupported speed ({}), only 1-3 supported'.format(speed))

        self._write([0x53, _PRO_SPEEDS[mode][int(speed)-1]])
        self._end_transaction_and_read(3)

    def _write_color(self, colors):
        """Write a list of colors to cycle between, the cycle pattern comes from the
        value used for cycle speed"""
        colorCount = 0
        setColors = []
        for color in colors:
            LOGGER.debug('color %s', color)
            colorCount = colorCount + 1
            setColors = setColors + color
        self._write([0x56, colorCount] + setColors)
        self._end_transaction_and_read(3)

    def _get_fan_speeds(self):
        """Read the RPM speed of the fans. This Tries to get the speeds for 3 fans as that is
        how many the H150i PRO has"""
        speeds = []
        for i in [0, 1, 2]:
            self._write([_PRO_CMD_READ_FAN_SPEED, i])
            msg = self._end_transaction_and_read(6)
            if msg[0] != 0x41 or msg[1] != 0x12 or msg[2] != 0x34 or msg[3] != i:
                LOGGER.debug('Unable to get speed for fan id {}'.format(i))
                continue
            speeds.append((msg[4] << 8) + msg[5])
        return speeds

    def _get_fan_indexes(self, channel):
        if len(channel) > 3:
            return [int(channel[3:]) - 1]
        return range(len(self._get_fan_speeds()))

    def initialize(self, pump_mode=None, **kwargs):
        """Initialize the device."""
        LOGGER.debug('Pro configure device...')
        if pump_mode == None:
            return
        else:
            LOGGER.debug('pump_mode %s write value %s', pump_mode,
                format(_PRO_PUMP_MODES.index(pump_mode),'02x'))
            self._write([_PRO_CMD_WRITE_PUMP_MODE, _PRO_PUMP_MODES.index(pump_mode)])
            self._end_transaction_and_read(5)

    def get_status(self, **kwargs):
        """Get a status report.
        Returns a list of `(property, value, unit)` tuples.
        """
        status = []
        ### Can some Pro devices have more than one temp sensor?   OCL seems to code for that?
        self._write([_PRO_CMD_READ_AIO_TEMP])
        msg = self._end_transaction_and_read(6)
        #LOGGER.debug('aio temp msg %s', ' '.join(format(i, '02x') for i in msg))
        aio_temp = msg[3] + msg[4]/10
        status.append(('Liquid temperature', aio_temp, '°C'))
        speeds = self._get_fan_speeds()
        for i in range(len(speeds)):
            status.append(('Fan {} speed'.format(i+1), speeds[i] | 0, 'rpm'))
        self._write([_PRO_CMD_READ_PUMP_MODE])
        msg = self._end_transaction_and_read(4)
        #LOGGER.debug('pump mode msg %s', ' '.join(format(i, '02x') for i in msg))
        pump_mode = msg[3]
        status.append(('Pump mode', _PRO_PUMP_MODES[pump_mode], ""))
        self._write([_PRO_CMD_READ_PUMP_SPEED])
        msg = self._end_transaction_and_read(5)
        #LOGGER.debug('pump speed msg %s', ' '.join(format(i, '02x') for i in msg))
        pump_speed = (msg[3] << 8) + msg[4]
        status.append(('Pump speed', pump_speed | 0, 'rpm'))
        self._write([_PRO_CMD_READ_FIRMWARE])
        msg = self._end_transaction_and_read(7)
        #LOGGER.debug('firmware id msg %s', ' '.join(format(i, '02x') for i in msg))
        firmware = '{}.{}.{}.{}'.format(format(msg[3], '01x'), format(msg[4], '01x'),
            format(msg[5], '01x'),format(msg[6], '01x'))
        status.append(('Firmware version', firmware, ''))
        return status

    def set_color(self, channel, mode, colors, time_per_color=1, time_off=None,
                  alert_threshold=_HIGH_TEMPERATURE, alert_color=[255, 0, 0],
                  speed=3, temps=['35', '45', '55'], **kwargs):
        """Set the color mode for a specific channel."""
        LOGGER.debug('kwargs %s', kwargs)
        colors = list(colors)
        LOGGER.debug('color count = %d', len(colors))
        LOGGER.debug('speed %s', int(speed))
        if mode == 'rainbow':
            self._write_color_change_speed(mode, speed)
            self._write([0x55, 0x01])
            self._end_transaction_and_read(3)
        elif mode == 'shift':
            self._write_color(colors)
            self._write_color_change_speed(mode, speed)
            self._write([0x55, 0x01])
            self._end_transaction_and_read(3)
        elif mode == 'pulse':
            self._write_color(colors)
            self._write_color_change_speed(mode, speed)
            self._write([0x52, 0x01])
            self._end_transaction_and_read(3)
        elif mode == 'blinking':
            self._write_color(colors)
            self._write_color_change_speed(mode, speed)
            self._write([0x58, 0x01])
            self._end_transaction_and_read(3)
        elif mode == 'fixed':
            self._write_color([colors[0], colors[0]])
            self._write([0x55, 0x01])
            self._end_transaction_and_read(3)
        elif mode == 'alert':
            temps = list(temps.split(' '))
            LOGGER.debug('temps count = %d', len(temps))
            LOGGER.debug('asetek temps %s %s %s', temps[0], temps[1], temps[2])
            LOGGER.debug('color count = %d', len(colors))
            self._write([0x5f, int(temps[0]), 0x00, int(temps[1]), 0x00, int(temps[2]), 0x00] + colors[0] + colors[1] + colors[2])
            self._end_transaction_and_read(6)
            self._write([0x5E, 0x01])
            self._end_transaction_and_read(3)
        else:
            raise KeyError('Unknown lighting mode {}'.format(mode))

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to follow a speed duty profile."""
        if channel == 'pump':
            raise ValueError('set_speed_profile not implemented for the pump on CorsairAsetekPro')
        adjusted = self._prepare_profile(profile, 0, 100, _MAX_PROFILE_POINTS)
        for temp, duty in adjusted:
            LOGGER.info('setting %s PWM point: (%i°C, %i%%), device interpolated',
                        channel, temp, duty)
        temps, duties = map(list, zip(*adjusted))
        # Need to write curve for each fan
        # Assume if we read n values from _get_fan_speed the fans are numbered [0, n)
        # This will have problems on a 2 fan system when the first fan has failed
        for i in self._get_fan_indexes(channel):
            self._write([_PRO_CMD_WRITE_FAN_SPEED, i] + temps + duties)
            self._end_transaction_and_read(32)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        if channel.startswith('fan'):
            # Setting a fix speed is supported, however it is done by sending RPM or PWM
            # values. I'm not 100% sure how this maps to %s used by liquidclt so set a flat
            # speed profile instead.
            LOGGER.info('using a flat profile to set %s to a fixed duty', channel)
            self.set_speed_profile(channel, [(0, duty), (_CRITICAL_TEMPERATURE - 1, duty)])
            return
        # Fixed speed pump is not supported, so guess a curve from the duty value given
        # less than 50 == quiet (0), less than 80 == balanced (1), greater than 80 == proformance (2).
        # Arbitrary values are arbitrary.
        if duty < 50:
            duty = 0
        elif duty < 80:
            duty = 1
        else:
            duty = 2
        self._write([_PRO_CMD_WRITE_PUMP_MODE, duty])
        self._end_transaction_and_read(5)
        # OCL Reads the mode after setting it, so do the same
        self._write([_PRO_CMD_READ_PUMP_MODE])
        self._end_transaction_and_read(4)

    @classmethod
    def probe(cls, handle, legacy_690lc=False, **kwargs):
        # the modern driver overrides probe and rigs it to switch on
        # --legacy-690lc, so we override it again
        return super().probe(handle, legacy_690lc=False, **kwargs)
