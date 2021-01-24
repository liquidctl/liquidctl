"""liquidctl drivers for Corsair HXi and RMi series power supply units.

Supported devices:

- Corsair HXi (HX750i, HX850i, HX1000i and HX1200i)
- Corsair RMi (RM650i, RM750i, RM850i and RM1000i)

Copyright (C) 2019–2021  Jonas Malaco and contributors

Port of corsaiRMi by notaz and realies.
Copyright (c) notaz, 2016

Incorporates or uses as reference work by Sean Nelson.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging

from datetime import timedelta
from enum import Enum

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.pmbus import CommandCode as CMD
from liquidctl.pmbus import WriteBit, linear_to_float
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 64
_SLAVE_ADDRESS = 0x02
_CORSAIR_READ_TOTAL_UPTIME = CMD.MFR_SPECIFIC_D1
_CORSAIR_READ_UPTIME = CMD.MFR_SPECIFIC_D2
_CORSAIR_12V_OCP_MODE = CMD.MFR_SPECIFIC_D8
_CORSAIR_READ_INPUT_POWER = CMD.MFR_SPECIFIC_EE
_CORSAIR_FAN_CONTROL_MODE = CMD.MFR_SPECIFIC_F0

_RAIL_12V = 0x0
_RAIL_5V = 0x1
_RAIL_3P3V = 0x2
_RAIL_NAMES = {_RAIL_12V: '+12V', _RAIL_5V: '+5V', _RAIL_3P3V: '+3.3V'}
_MIN_FAN_DUTY = 0


class OCPMode(Enum):
    """Overcurrent protection mode."""

    SINGLE_RAIL = 0x1
    MULTI_RAIL = 0x2

    def __str__(self):
        return self.name.capitalize().replace('_', ' ')


class FanControlMode(Enum):
    """Fan control mode."""

    HARDWARE = 0x0
    SOFTWARE = 0x1

    def __str__(self):
        return self.name.capitalize()


class CorsairHidPsu(UsbHidDriver):
    """Corsair HXi or RMi series power supply unit."""

    SUPPORTED_DEVICES = [
        (0x1b1c, 0x1c05, None, 'Corsair HX750i', {}),
        (0x1b1c, 0x1c06, None, 'Corsair HX850i', {}),
        (0x1b1c, 0x1c07, None, 'Corsair HX1000i', {}),
        (0x1b1c, 0x1c08, None, 'Corsair HX1200i', {}),
        (0x1b1c, 0x1c0a, None, 'Corsair RM650i', {}),
        (0x1b1c, 0x1c0b, None, 'Corsair RM750i', {}),
        (0x1b1c, 0x1c0c, None, 'Corsair RM850i', {}),
        (0x1b1c, 0x1c0d, None, 'Corsair RM1000i', {}),
    ]

    def initialize(self, single_12v_ocp=False, **kwargs):
        """Initialize the device.

        Necessary to receive non-zero value responses from the device.

        Note: replies before calling this function appear to follow the
        pattern <address> <cte 0xfe> <zero> <zero> <padding...>.
        """

        self.device.clear_enqueued_reports()
        self._write([0xfe, 0x03])  # not well understood
        self._read()
        mode = OCPMode.SINGLE_RAIL if single_12v_ocp else OCPMode.MULTI_RAIL
        if mode != self._get_12v_ocp_mode():
            # TODO replace log level with info once this has been confimed to work
            _LOGGER.warning('(experimental feature) changing +12V OCP mode to %s', mode)
            self._exec(WriteBit.WRITE, _CORSAIR_12V_OCP_MODE, [mode.value])
        if self._get_fan_control_mode() != FanControlMode.HARDWARE:
            _LOGGER.info('resetting fan control to hardware mode')
            self._set_fan_control_mode(FanControlMode.HARDWARE)

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        self.device.clear_enqueued_reports()
        ret = self._exec(WriteBit.WRITE, CMD.PAGE, [0])
        if ret[1] == 0xfe:
            _LOGGER.warning('possibly uninitialized device')
        status = [
            ('Current uptime', self._get_timedelta(_CORSAIR_READ_UPTIME), ''),
            ('Total uptime', self._get_timedelta(_CORSAIR_READ_TOTAL_UPTIME), ''),
            ('Temperature 1', self._get_float(CMD.READ_TEMPERATURE_1), '°C'),
            ('Temperature 2', self._get_float(CMD.READ_TEMPERATURE_2), '°C'),
            ('Fan control mode', self._get_fan_control_mode(), ''),
            ('Fan speed', self._get_float(CMD.READ_FAN_SPEED_1), 'rpm'),
            ('Input voltage', self._get_float(CMD.READ_VIN), 'V'),
            ('Total power', self._get_float(_CORSAIR_READ_INPUT_POWER), 'W'),
            ('+12V OCP mode', self._get_12v_ocp_mode(), ''),
        ]
        for rail in [_RAIL_12V, _RAIL_5V, _RAIL_3P3V]:
            name = _RAIL_NAMES[rail]
            self._exec(WriteBit.WRITE, CMD.PAGE, [rail])
            status.append((f'{name} output voltage', self._get_float(CMD.READ_VOUT), 'V'))
            status.append((f'{name} output current', self._get_float(CMD.READ_IOUT), 'A'))
            status.append((f'{name} output power', self._get_float(CMD.READ_POUT), 'W'))
        self._exec(WriteBit.WRITE, CMD.PAGE, [0])
        _LOGGER.warning('reading the +12V OCP mode is an experimental feature')
        return status

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        duty = clamp(duty, _MIN_FAN_DUTY, 100)
        _LOGGER.info('ensuring fan control is in software mode')
        self._set_fan_control_mode(FanControlMode.SOFTWARE)
        _LOGGER.info('setting fan PWM duty to %d%%', duty)
        self._exec(WriteBit.WRITE, CMD.FAN_COMMAND_1, [duty])

    def set_color(self, channel, mode, colors, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def _write(self, data):
        assert len(data) <= _REPORT_LENGTH
        packet = bytearray(1 + _REPORT_LENGTH)
        packet[1: 1 + len(data)] = data  # device doesn't use numbered reports
        self.device.write(packet)

    def _read(self):
        return self.device.read(_REPORT_LENGTH)

    def _exec(self, writebit, command, data=None):
        self._write([_SLAVE_ADDRESS | WriteBit(writebit), CMD(command)] + (data or []))
        return self._read()

    def _get_12v_ocp_mode(self):
        """Get +12V single/multi-rail OCP mode."""
        return OCPMode(self._exec(WriteBit.READ, _CORSAIR_12V_OCP_MODE)[2])

    def _get_fan_control_mode(self):
        """Get hardware/software fan control mode."""
        return FanControlMode(self._exec(WriteBit.READ, _CORSAIR_FAN_CONTROL_MODE)[2])

    def _set_fan_control_mode(self, mode):
        """Set hardware/software fan control mode."""
        return self._exec(WriteBit.WRITE, _CORSAIR_FAN_CONTROL_MODE, [mode.value])

    def _get_float(self, command):
        """Get float value with `command`."""
        return linear_to_float(self._exec(WriteBit.READ, command)[2:])

    def _get_timedelta(self, command):
        """Get timedelta with `command`."""
        secs = int.from_bytes(self._exec(WriteBit.READ, command)[2:], byteorder='little')
        return timedelta(seconds=secs)


# deprecated aliases
CorsairHidPsuDriver = CorsairHidPsu
