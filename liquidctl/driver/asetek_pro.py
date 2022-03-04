"""liquidctl drivers for sixth generation Asetek liquid coolers.

Copyright (C) 2020–2022  Andrew Robertson, Jonas Malaco and contributors

SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from liquidctl.driver.asetek import _Base690Lc
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_READ_ENDPOINT = 0x81
_READ_MAX_LENGTH = 32
_READ_TIMEOUT = 2000
_WRITE_ENDPOINT = 0x1
_WRITE_TIMEOUT = 2000

_MAX_PROFILE_POINTS = 7

_CMD_READ_AIO_TEMP = 0xa9
_CMD_READ_FAN_SPEED = 0x41
_CMD_READ_FIRMWARE = 0xaa
_CMD_READ_PUMP_MODE = 0x33
_CMD_READ_PUMP_SPEED = 0x31
_CMD_WRITE_COLOR_LIST = 0x56
_CMD_WRITE_COLOR_SPEED = 0x53
_CMD_WRITE_FAN_CURVE = 0x40
_CMD_WRITE_FAN_SPEED = 0x42
_CMD_WRITE_PUMP_MODE = 0x32

_PUMP_MODES = ['quiet', 'balanced', 'performance']

_COLOR_SPEEDS = ['slower', 'normal', 'faster']

_COLOR_SPEEDS_VALUES = {
    'shift': [
        0x46, # slower
        0x28, # normal
        0x0F  # faster
    ],
    'pulse':[
        0x50, # slower
        0x37, # normal
        0x1E  # faster
    ],
    'blinking': [
        0x0F, # slower
        0x0A, # normal
        0x05  # faster
    ],
}

_COLOR_CHANGE_MODES = {
    'alert': [],
    'shift': [0x55, 0x01],
    'pulse': [0x52, 0x01],
    'blinking': [0x58, 0x01],
    'fixed': [0x55, 0x01],
}

# FIXME unknown required and maximum values
_COLOR_COUNT_BOUNDS = {
    'alert': (3, 3),
    'shift': (2, 4),
    'pulse': (1, 4),
    'blinking': (1, 4),
    'fixed': (1, 1),
}


def _quoted(*names):
    return ', '.join(map(repr, names))


# we inherit from _Base690Lc to reuse its implementation of connect
# and disconnect, that emulates the stock SiUSBXp driver on Windows
class HydroPro(_Base690Lc):
    """liquidctl driver for Corsair-branded sixth generation Asetek coolers."""

    SUPPORTED_DEVICES = [
        (0x1b1c, 0x0c12, None, 'Corsair Hydro H150i Pro', {'fan_count': 3}),
        (0x1b1c, 0x0c13, None, 'Corsair Hydro H115i Pro', {'fan_count': 2}),
        (0x1b1c, 0x0c15, None, 'Corsair Hydro H100i Pro', {'fan_count': 2})
    ]

    def __init__(self, device, description, fan_count, **kwargs):
        super().__init__(device, description, **kwargs)
        self._fan_count = fan_count
        self._data = None

    def _post(self, data, *, read_length=None):
        """Write `data` and return response of up to `read_length` bytes."""

        assert read_length is not None and read_length <= _READ_MAX_LENGTH

        self.device.write(_WRITE_ENDPOINT, data, _WRITE_TIMEOUT)
        return self.device.read(_READ_ENDPOINT, read_length, _READ_TIMEOUT)[0:read_length]

    def initialize(self, pump_mode='balanced', **kwargs):
        """Initialize the device."""

        pump_mode = pump_mode.lower()

        if pump_mode not in _PUMP_MODES:
            raise ValueError(f'unknown pump mode, should be one of: {_quoted(*_PUMP_MODES)}')

        self._post([_CMD_WRITE_PUMP_MODE, _PUMP_MODES.index(pump_mode)], read_length=5)
        self.device.release()

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        msg = self._post([_CMD_READ_AIO_TEMP], read_length=6)
        aio_temp = msg[3] + msg[4]/10

        speeds = self._get_fan_speeds()

        msg = self._post([_CMD_READ_PUMP_MODE], read_length=4)
        pump_mode = _PUMP_MODES[msg[3]]

        msg = self._post([_CMD_READ_PUMP_SPEED], read_length=5)
        pump_speed = (msg[3] << 8) + msg[4]

        msg = self._post([_CMD_READ_FIRMWARE], read_length=7)
        firmware = '{}.{}.{}.{}'.format(*tuple(msg[3:7]))

        self.device.release()

        status = [('Liquid temperature', aio_temp, '°C')]

        for i, speed in enumerate(speeds):
            if speed is not None:
                status.append((f'Fan {i + 1} speed', speed, 'rpm'))

        return status + [
            ('Pump mode', pump_mode, ""),
            ('Pump speed', pump_speed, 'rpm'),
            ('Firmware version', firmware, '')
        ]

    def _get_fan_speeds(self):
        """Read the RPM speed of the fans."""

        speeds = []

        for i in range(self._fan_count):
            msg = self._post([_CMD_READ_FAN_SPEED, i], read_length=6)

            if msg[0] != 0x41 or msg[1] != 0x12 or msg[2] != 0x34 or msg[3] != i:
                _LOGGER.warning('failed to get current speed of fan %d', i)
                speeds.append(None)
                continue

            speeds.append((msg[4] << 8) + msg[5])
        return speeds

    def set_color(self, channel, mode, colors, speed='normal', **kwargs):
        """Set the color mode for a specific channel."""

        mode = mode.lower()
        speed = speed.lower()
        colors = list(colors)

        if mode not in _COLOR_CHANGE_MODES:
            valid = _quoted(*_COLOR_CHANGE_MODES.keys())
            raise ValueError(f'unknown lighting mode, should be one of: {valid}')

        if speed not in _COLOR_SPEEDS:
            valid = _quoted(*_COLOR_SPEEDS)
            raise ValueError(f'unknown speed value, should be one of {valid}')

        if mode == 'alert':
            # FIXME this mode is far from being completely implemented; for
            # one, the temperatures are hardcoded; additionally, it may also be
            # possible to combine it with other modes, but exploring that would
            # require some experimentation
            temps = (30, 40, 50)
            self._post([0x5f, temps[0], 0x00, temps[1], 0x00, temps[1], 0x00]
                       + colors[0] + colors[1] + colors[2], read_length=6)
            self._post([0x5e, 0x01], read_length=3)
            self.device.release()
            return

        colors = self._check_color_count_bounds(colors, mode)

        if mode == 'fixed':
            colors = [colors[0], colors[0]]

        set_colors = list(itertools.chain(*colors))
        self._post([_CMD_WRITE_COLOR_LIST, len(colors)] + set_colors, read_length=3)

        if mode != 'fixed':
            magic_value = _COLOR_SPEEDS_VALUES[mode][_COLOR_SPEEDS.index(speed)]
            self._post([_CMD_WRITE_COLOR_SPEED, magic_value], read_length=3)

        self._post(_COLOR_CHANGE_MODES[mode], read_length=3)
        self.device.release()

    def _check_color_count_bounds(self, color_list, mode_name):
        requires, maximum = _COLOR_COUNT_BOUNDS[mode_name]

        if len(color_list) < requires:
            raise ValueError(f'{mode_name} mode requires {requires} colors')

        if len(color_list) > maximum:
            _LOGGER.debug('too many colors, dropping to %d', maximum)
            color_list = color_list[:maximum]

        return color_list

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to follow a speed duty profile."""

        channel = channel.lower()
        fan_indexes = self._fan_indexes(channel)

        adjusted = self._prepare_profile(profile, 0, 100, _MAX_PROFILE_POINTS)
        for temp, duty in adjusted:
            _LOGGER.info('setting %s PWM point: (%i°C, %i%%), device interpolated',
                        channel, temp, duty)

        temps, duties = map(list, zip(*adjusted))
        for i in fan_indexes:
            self._post([_CMD_WRITE_FAN_CURVE, i] + temps + duties, read_length=32)

        self.device.release()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""

        channel = channel.lower()
        duty = clamp(duty, 0, 100)

        for i in self._fan_indexes(channel):
            _LOGGER.info('setting speed for fan %d to %d', i + 1, duty)
            self._post([_CMD_WRITE_FAN_SPEED, i, duty], read_length=32)
        self.device.release()

    def _fan_indexes(self, channel):
        if channel.startswith('fan'):
            if len(channel) > 3:
                channel_num = int(channel[3:]) - 1
                if channel_num >= self._fan_count:
                    raise ValueError(f'unknown channel: {channel}')
                return [channel_num]
            return range(self._fan_count)
        elif channel == 'pump':
            raise NotSupportedByDevice()
        else:
            raise ValueError(f'unknown channel: {channel}')

    @classmethod
    def probe(cls, handle, **kwargs):
        return super().probe(handle, **kwargs)


# backward compatibility
CorsairAsetekProDriver = HydroPro
