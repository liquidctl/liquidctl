"""liquidctl drivers for sixth generation Asetek 690LC liquid coolers.

Supported devices:

- Corsair H100i PRO RGB, H115i PRO RGB or H150i PRO RGB (Experimental)

Copyright (C) 2018–2020  Jonas Malaco and contributors

Incorporates or uses as reference work by Kristóf Jakab, Sean Nelson
and Chris Griffith.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

import usb

from liquidctl.driver.asetek import _CommonAsetekDriver
from liquidctl.driver.usb import UsbDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.keyval import RuntimeStorage
from liquidctl.util import clamp, LazyHexRepr


_LOGGER = logging.getLogger(__name__)

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
_PRO_CMD_WRITE_FAN_CURVE = 0x40
_PRO_CMD_WRITE_FAN_SPEED = 0x42
_PRO_CMD_READ_PUMP_SPEED = 0x31
_PRO_CMD_READ_PUMP_MODE = 0x33
_PRO_CMD_WRITE_PUMP_MODE = 0x32
_PRO_CMD_WRITE_COLOR_LIST = 0x56
_PRO_PUMP_MODES = [
    'quiet',
    'balanced',
    'performance'
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

_PRO_COLOR_CHANGE_MODES = {
    'rainbow': [0x55, 0x01],
    'alert': [],
    'shitf': [0x55, 0x01],
    'pulse': [0x52, 0x01],
    'blinking': [0x58, 0x01],
    'fixed': [0x55, 0x01]
}


class CorsairAsetekProDriver(_CommonAsetekDriver):
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
        _LOGGER.debug('write %s', LazyHexRepr(data))
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
        _LOGGER.debug('received %s', LazyHexRepr(msg))
        self.device.release()
        return msg

    def _write_color_change_speed(self, mode, speed):
        """Send the speed to cycle colors on the RGB pump"""
        speed = clamp(speed, 1, 3)
        self._write([0x53, _PRO_SPEEDS[mode][int(speed)-1]])
        self._end_transaction_and_read(3)

    def _write_color(self, colors):
        """Write a list of colors to cycle between, the cycle pattern comes from the
        value used for cycle speed"""
        setColors = list(itertools.chain(*colors))
        colorCount = int(len(setColors) / 3)
        self._write([_PRO_CMD_WRITE_COLOR_LIST, colorCount] + setColors)
        self._end_transaction_and_read(3)

    def _get_fan_speeds(self):
        """Read the RPM speed of the fans. Try to get the speeds for 3 fans as that is
        how many the H150i PRO supports"""
        speeds = []
        for i in range(3):
            self._write([_PRO_CMD_READ_FAN_SPEED, i])
            msg = self._end_transaction_and_read(6)
            if msg[0] != 0x41 or msg[1] != 0x12 or msg[2] != 0x34 or msg[3] != i:
                _LOGGER.debug('Unable to get speed for fan id %d', i)
                continue
            speeds.append((i, (msg[4] << 8) + msg[5]))
        return speeds

    def _get_fan_indexes(self, channel):
        if len(channel) > 3:
            return [int(channel[3:]) - 1]
        return [reading[0] for reading in self._get_fan_speeds()]

    def initialize(self, pump_mode='balanced', **kwargs):
        """Initialize the device."""
        _LOGGER.debug('Pro configure device...')
        _LOGGER.debug('pump_mode %s', pump_mode)
        self._write([_PRO_CMD_WRITE_PUMP_MODE, _PRO_PUMP_MODES.index(pump_mode.lower())])
        self._end_transaction_and_read(5)

    def get_status(self, **kwargs):
        """Get a status report.
        Returns a list of `(property, value, unit)` tuples.
        """
        status = []
        self._write([_PRO_CMD_READ_AIO_TEMP])
        msg = self._end_transaction_and_read(6)
        aio_temp = msg[3] + msg[4]/10
        status.append(('Liquid temperature', aio_temp, '°C'))
        speeds = self._get_fan_speeds()
        for reading in speeds:
            fan_num = reading[0] + 1
            status.append((f'Fan {fan_num} speed', reading[1], 'rpm'))
        self._write([_PRO_CMD_READ_PUMP_MODE])
        msg = self._end_transaction_and_read(4)
        pump_mode = msg[3]
        status.append(('Pump mode', _PRO_PUMP_MODES[pump_mode], ""))
        self._write([_PRO_CMD_READ_PUMP_SPEED])
        msg = self._end_transaction_and_read(5)
        pump_speed = (msg[3] << 8) + msg[4]
        status.append(('Pump speed', pump_speed, 'rpm'))
        self._write([_PRO_CMD_READ_FIRMWARE])
        msg = self._end_transaction_and_read(7)
        firmware = '{}.{}.{}.{}'.format(*tuple(msg[3:7]))
        status.append(('Firmware version', firmware, ''))
        return status

    def set_color(self, channel, mode, colors, time_per_color=1, time_off=None,
                  alert_threshold=_HIGH_TEMPERATURE, alert_color=[255, 0, 0],
                  speed=3, temps=['35', '45', '55'], **kwargs):
        """Set the color mode for a specific channel."""
        if mode not in _PRO_COLOR_CHANGE_MODES:
            raise KeyError(f'Unknown lighting mode {mode}')
        colors = list(colors)
        _LOGGER.debug('color count = %d', len(colors))
        _LOGGER.debug('color change speed %d', int(speed))
        if mode == 'alert':
            self._write([0x5f, int(temps[0]), 0x00, int(temps[1]), 0x00, int(temps[2]), 0x00] + colors[0] + colors[1] + colors[2])
            self._end_transaction_and_read(6)
            self._write([0x5E, 0x01])
            self._end_transaction_and_read(3)
            return
        if mode == 'fixed':
            colors = [colors[0], colors[0]]
        if mode != 'rainbow':
            self._write_color(colors)
        if mode != 'fixed':
            self._write_color_change_speed(mode, speed)
        self._write(_PRO_COLOR_CHANGE_MODES[mode])
        self._end_transaction_and_read(3)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to follow a speed duty profile."""
        channel = channel.lower()
        if channel == 'pump':
            raise NotSupportedByDevice()
        if not channel.startswith('fan'):
            raise KeyError(f'Unknown channel: {channel}')
        adjusted = self._prepare_profile(profile, 0, 100, _MAX_PROFILE_POINTS)
        for temp, duty in adjusted:
            _LOGGER.info('setting %s PWM point: (%i°C, %i%%), device interpolated',
                        channel, temp, duty)
        temps, duties = map(list, zip(*adjusted))
        # Need to write curve for each fan in channel
        for i in self._get_fan_indexes(channel):
            _LOGGER.info('setting speed for fan %d', i+1)
            self._write([_PRO_CMD_WRITE_FAN_CURVE, i] + temps + duties)
            self._end_transaction_and_read(32)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        channel = channel.lower()
        if channel.startswith('fan'):
            duty = clamp(duty, 0, 100)
            # Need to write curve for each fan in channel
            for i in self._get_fan_indexes(channel):
                _LOGGER.info('setting speed for fan %d to %d', i+1, duty)
                self._write([_PRO_CMD_WRITE_FAN_SPEED, i, duty])
                self._end_transaction_and_read(32)
        elif channel == 'pump':
            raise NotSupportedByDevice()
        else:
            raise KeyError(f'Unknow channel: {channel}')

    @classmethod
    def probe(cls, handle, **kwargs):
        return super().probe(handle, **kwargs)
