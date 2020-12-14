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

_WRITE_ENDPOINT = 0x1
_READ_ENDPOINT = 0x81
_CMD_READ_FIRMWARE = 0xaa
_CMD_READ_AIO_TEMP = 0xa9
_CMD_READ_FAN_SPEED = 0x41
_CMD_WRITE_FAN_CURVE = 0x40
_CMD_WRITE_FAN_SPEED = 0x42
_CMD_READ_PUMP_SPEED = 0x31
_CMD_READ_PUMP_MODE = 0x33
_CMD_WRITE_PUMP_MODE = 0x32
_CMD_WRITE_COLOR_LIST = 0x56
_PUMP_MODES = [
    'quiet',
    'balanced',
    'performance'
    ]

_COLOR_SPEEDS = ['slower', 'normal', 'faster']

_COLOR_SPEEDS_VALUES = {
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

_COLOR_CHANGE_MODES = {
    'rainbow': [0x55, 0x01],
    'alert': [],
    'shift': [0x55, 0x01],
    'pulse': [0x52, 0x01],
    'blinking': [0x58, 0x01],
    'fixed': [0x55, 0x01]
}


class CorsairAsetekProDriver(_CommonAsetekDriver):
    """liquidctl driver for Corsair-branded sixth generation Asetek coolers."""
    SUPPORTED_DEVICES = [
        (0x1b1c, 0x0c12, None, 'Corsair Hydro H150i Pro', {'fan_count': 3}),
        (0x1b1c, 0x0c13, None, 'Corsair Hydro H115i Pro', {'fan_count': 2}),
        (0x1b1c, 0x0c15, None, 'Corsair Hydro H100i Pro', {'fan_count': 2})
    ]

    def __init__(self, device, description, fan_count=0, **kwargs):
        super().__init__(device, description, **kwargs)
        self._data = None
        self._fan_count = fan_count


    def _write(self, data):
        """Write data to the AIO and log"""
        self.device.write(_WRITE_ENDPOINT, data, _WRITE_TIMEOUT)

    # Not calling this (or begin transaction) since they do not seem to be needed for H100i Pro
    def _end_transaction_and_read(self, length=_READ_LENGTH):
        """End the transaction by reading from the device.
        According to the official documentation, as well as Craig's open-source
        implementation (libSiUSBXp), it should be necessary to check the queue
        size and read data in chunks.  However, leviathan and its derivatives
        seem to work fine without this complexity; we currently try the same
        approach.
        """
        msg = self.device.read(_READ_ENDPOINT, length, _READ_TIMEOUT)
        self.device.release()
        return msg

    def _write_color_change_speed(self, mode, speed):
        """Send the speed to cycle colors on the RGB pump"""
        self._write([0x53, _COLOR_SPEEDS_VALUES[mode][_COLOR_SPEEDS.index(speed)]])
        self._end_transaction_and_read(3)

    def _write_color(self, colors):
        """Write a list of colors to cycle between, the cycle pattern comes from the
        value used for cycle speed"""
        setColors = list(itertools.chain(*colors))
        colorCount = int(len(setColors) / 3)
        self._write([_CMD_WRITE_COLOR_LIST, colorCount] + setColors)
        self._end_transaction_and_read(3)

    def _get_fan_speeds(self):
        """Read the RPM speed of the fans. Try to get the speeds for 3 fans as that is
        how many the H150i PRO supports"""
        speeds = []
        for i in range(self._fan_count):
            self._write([_CMD_READ_FAN_SPEED, i])
            msg = self._end_transaction_and_read(6)
            if msg[0] != 0x41 or msg[1] != 0x12 or msg[2] != 0x34 or msg[3] != i:
                _LOGGER.debug('Unable to get speed for fan id %d', i)
                speeds.append(-1)
                continue
            speeds.append((msg[4] << 8) + msg[5])
        return speeds

    def _get_fan_indexes(self, channel):
        if len(channel) > 3:
            channel_num = int(channel[3:])
            if channel_num > self._fan_count:
                raise ValueError(f'Unknown channel: {channel}')
            return [channel_num - 1]
        return range(self._fan_count)

    def initialize(self, pump_mode='balanced', **kwargs):
        """Initialize the device."""
        _LOGGER.debug('Pro configure device...')
        _LOGGER.debug('pump_mode %s', pump_mode)
        pump_mode = pump_mode.lower()
        if pump_mode not in _PUMP_MODES:
            valid = ", ".join(_PUMP_MODES)
            raise KeyError(f'Unknown pump mode {pump_mode}, should be one of {valid}')
        self._write([_CMD_WRITE_PUMP_MODE, _PUMP_MODES.index(pump_mode.lower())])
        self._end_transaction_and_read(5)

    def get_status(self, **kwargs):
        """Get a status report.
        Returns a list of `(property, value, unit)` tuples.
        """
        # Liquid temperature
        self._write([_CMD_READ_AIO_TEMP])
        msg = self._end_transaction_and_read(6)
        aio_temp = msg[3] + msg[4]/10
        speeds = self._get_fan_speeds()
        # Pump mode
        self._write([_CMD_READ_PUMP_MODE])
        msg = self._end_transaction_and_read(4)
        pump_mode = msg[3]
        # Pump Speed
        self._write([_CMD_READ_PUMP_SPEED])
        msg = self._end_transaction_and_read(5)
        pump_speed = (msg[3] << 8) + msg[4]
        # Firmware
        self._write([_CMD_READ_FIRMWARE])
        msg = self._end_transaction_and_read(7)
        firmware = '{}.{}.{}.{}'.format(*tuple(msg[3:7]))
        status = [('Liquid temperature', aio_temp, '°C')]
        for i in range(len(speeds)):
            speed = speeds[i] if speeds[i] >= 0 else 'Error'
            status.append((f'Fan {i+1} speed', speed, 'rpm'))
        return status + [
            ('Pump mode', _PUMP_MODES[pump_mode], ""),
            ('Pump speed', pump_speed, 'rpm'),
            ('Firmware version', firmware, '')
        ]

    def set_color(self, channel, mode, colors, speed='faster',
                  temps=['35', '45', '55'], **kwargs):
        """Set the color mode for a specific channel."""
        speed = speed.lower()
        if mode not in _COLOR_CHANGE_MODES:
            valid = ', '.join(_COLOR_CHANGE_MODES.keys())
            raise KeyError(f'Unknown lighting mode {mode}, should be one of {valid}')
        if speed not in _COLOR_SPEEDS:
            valid = ', '.join(_COLOR_SPEEDS)
            raise KeyError(f'Unknown speed {speed}, should be one of {valid}')
        if channel != 'pump':
            raise KeyError('Cosair PRO only supports setting the color on the pump')
        colors = list(colors)
        _LOGGER.debug('color count = %d', len(colors))
        _LOGGER.debug('color change speed %s', speed)
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
        self._write(_COLOR_CHANGE_MODES[mode])
        self._end_transaction_and_read(3)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to follow a speed duty profile."""
        channel = channel.lower()
        if channel == 'pump':
            raise NotSupportedByDevice()
        if not channel.startswith('fan'):
            raise ValueError(f'Unknown channel: {channel}')
        adjusted = self._prepare_profile(profile, 0, 100, _MAX_PROFILE_POINTS)
        for temp, duty in adjusted:
            _LOGGER.info('setting %s PWM point: (%i°C, %i%%), device interpolated',
                        channel, temp, duty)
        temps, duties = map(list, zip(*adjusted))
        # Need to write curve for each fan in channel
        for i in self._get_fan_indexes(channel):
            _LOGGER.info('setting speed for fan %d', i+1)
            self._write([_CMD_WRITE_FAN_CURVE, i] + temps + duties)
            self._end_transaction_and_read(32)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        channel = channel.lower()
        if channel.startswith('fan'):
            duty = clamp(duty, 0, 100)
            # Need to write curve for each fan in channel
            for i in self._get_fan_indexes(channel):
                _LOGGER.info('setting speed for fan %d to %d', i+1, duty)
                self._write([_CMD_WRITE_FAN_SPEED, i, duty])
                self._end_transaction_and_read(32)
        elif channel == 'pump':
            raise NotSupportedByDevice()
        else:
            raise KeyError(f'Unknow channel: {channel}')

    @classmethod
    def probe(cls, handle, **kwargs):
        return super().probe(handle, **kwargs)
