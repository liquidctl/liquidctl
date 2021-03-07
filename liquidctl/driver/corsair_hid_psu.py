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
_CORSAIR_READ_OUTPUT_POWER = CMD.MFR_SPECIFIC_EE
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
        (0x1b1c, 0x1c05, None, 'Corsair HX750i', {
            'fpowin115': (0.00013153276902318052, 1.0118732314945875, 9.783796618886313),
            'fpowin230': ( 9.268856467314546e-05, 1.0183515407387007, 8.279822175342481),
        }),
        (0x1b1c, 0x1c06, None, 'Corsair HX850i', {
            'fpowin115': (0.00011552923724840388, 1.0111311876704099, 12.015296651918918),
            'fpowin230': ( 8.126644224872423e-05, 1.0176256272095185, 10.290640442373850),
        }),
        (0x1b1c, 0x1c07, None, 'Corsair HX1000i', {
            'fpowin115': (9.48609754417109e-05,  1.0170509865269720, 11.619826520447452),
            'fpowin230': (9.649987544008507e-05, 1.0018241767296636, 12.759957859756842),
        }),
        (0x1b1c, 0x1c08, None, 'Corsair HX1200i', {
            'fpowin115': (6.244705156199815e-05,  1.0234738310580973, 15.293509559389241),
            'fpowin230': (5.9413179794350966e-05, 1.0023670927127724, 15.886126793547152),
        }),
        (0x1b1c, 0x1c0a, None, 'Corsair RM650i', {
            'fpowin115': (0.00017323493381072683, 1.0047044721686030, 12.376592422281606),
            'fpowin230': (0.00012413136310310370, 1.0284317478987164,  9.465259079360674),
        }),
        (0x1b1c, 0x1c0b, None, 'Corsair RM750i', {
            'fpowin115': (0.00015013694263596336, 1.0047044721686027, 14.280683564171110),
            'fpowin230': (0.00010460621468919797, 1.0173089573727216, 11.495900706372142),
        }),
        (0x1b1c, 0x1c0c, None, 'Corsair RM850i', {
            'fpowin115': (0.00012280002467981107, 1.0159421430340847, 13.555472968718759),
            'fpowin230': ( 8.816054254801031e-05, 1.0234738318592156, 10.832902491655597),
        }),
        (0x1b1c, 0x1c0d, None, 'Corsair RM1000i', {
            'fpowin115': (0.00010018433053123574, 1.0272313660072225, 14.092187353321624),
            'fpowin230': ( 8.600634771656125e-05, 1.0289245073649413, 13.701515390258626),
        }),
    ]

    def __init__(self, *args, fpowin115=None, fpowin230=None, **kwargs):
        assert fpowin115 and fpowin230

        super().__init__(*args, **kwargs)
        self.fpowin115 = fpowin115
        self.fpowin230 = fpowin230

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
            _LOGGER.info('changing +12V OCP mode to %s', mode)
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

        input_voltage = self._get_float(CMD.READ_VIN)

        status = [
            ('Current uptime', self._get_timedelta(_CORSAIR_READ_UPTIME), ''),
            ('Total uptime', self._get_timedelta(_CORSAIR_READ_TOTAL_UPTIME), ''),
            ('Temperature 1', self._get_float(CMD.READ_TEMPERATURE_1), '°C'),
            ('Temperature 2', self._get_float(CMD.READ_TEMPERATURE_2), '°C'),
            ('Fan control mode', self._get_fan_control_mode(), ''),
            ('Fan speed', self._get_float(CMD.READ_FAN_SPEED_1), 'rpm'),
            ('Input voltage', input_voltage, 'V'),
            ('+12V OCP mode', self._get_12v_ocp_mode(), ''),
        ]

        for rail in [_RAIL_12V, _RAIL_5V, _RAIL_3P3V]:
            name = _RAIL_NAMES[rail]
            self._exec(WriteBit.WRITE, CMD.PAGE, [rail])
            status.append((f'{name} output voltage', self._get_float(CMD.READ_VOUT), 'V'))
            status.append((f'{name} output current', self._get_float(CMD.READ_IOUT), 'A'))
            status.append((f'{name} output power', self._get_float(CMD.READ_POUT), 'W'))

        output_power = self._get_float(_CORSAIR_READ_OUTPUT_POWER)
        input_power = round(self._input_power_at(input_voltage, output_power), 0)
        efficiency = round(output_power / input_power * 100, 0)

        status.append(('Total power output', output_power, 'W'))
        status.append(('Estimated input power', input_power, 'W'))
        status.append(('Estimated efficiency', efficiency, '%'))

        self._exec(WriteBit.WRITE, CMD.PAGE, [0])
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

    def _input_power_at(self, input_voltage, output_power):
        def quadratic(params, x):
            a, b, c = params
            return a * x**2 + b * x + c

        for_in115v = quadratic(self.fpowin115, output_power)
        for_in230v = quadratic(self.fpowin230, output_power)

        # interpolate for input_voltage
        return for_in115v + (for_in230v - for_in115v) / 115 * (input_voltage - 115)

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
