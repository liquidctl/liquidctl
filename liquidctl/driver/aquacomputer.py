"""liquidctl driver for Aquacomputer family of watercooling devices.

Aquacomputer D5 Next watercooling pump
--------------------------------------
The pump sends a status HID report every second with no initialization
being required.

The status HID report exposes sensor values such as liquid temperature and
two groups of fan sensors, for the pump and the optionally connected fan.
These groups provide RPM speed, voltage, current and power readings. The
pump additionally exposes +5V and +12V voltage rail readings.

Driver
------
Linux has the aquacomputer_d5next driver available since v5.15. Subsequent
releases have more functionality and support a wider range of devices. If
present, it's used instead of reading the status reports directly.

Copyright (C) 2022 - Aleksa Savic

SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDriver
from liquidctl.util import u16be_from

_LOGGER = logging.getLogger(__name__)

_AQC_TEMP_SENSOR_DISCONNECTED = 0x7FFF
_AQC_FAN_VOLTAGE_OFFSET = 0x02
_AQC_FAN_CURRENT_OFFSET = 0x04
_AQC_FAN_POWER_OFFSET = 0x06
_AQC_FAN_SPEED_OFFSET = 0x08

_AQC_STATUS_READ_ENDPOINT = 0x01


class Aquacomputer(UsbHidDriver):
    # Support for hwmon: aquacomputer_d5next, sensors - 5.15+

    _DEVICE_D5NEXT = "D5 Next"

    _DEVICE_INFO = {
        _DEVICE_D5NEXT: {
            "type": _DEVICE_D5NEXT,
            "fan_sensors": [0x6C, 0x5F],
            "temp_sensors": [0x57],
            "plus_5v_voltage": 0x39,
            "plus_12v_voltage": 0x37,
            "temp_sensors_label": ["Liquid temperature"],
            "fan_speed_label": ["Pump speed", "Fan speed"],
            "fan_power_label": ["Pump power", "Fan power"],
            "fan_voltage_label": ["Pump voltage", "Fan voltage"],
            "fan_current_label": ["Pump current", "Fan current"],
            "status_report_length": 0x9E,
        }
    }

    SUPPORTED_DEVICES = [
        (0x0C70, 0xF00E, None, "Aquacomputer D5 Next", {"device_info": _DEVICE_INFO[_DEVICE_D5NEXT]}),
    ]

    def __init__(self, device, description, device_info, **kwargs):
        super().__init__(device, description)

        # Read when necessary
        self._firmware_version = None

        self._device_info = device_info

    def initialize(self, **kwargs):
        """Initialize the device and the driver.

        This method should be called every time the system boots, resumes from
        a suspended state, or if the device has just been (re)connected.  In
        those scenarios, no other method, except `connect()` or `disconnect()`,
        should be called until the device and driver has been (re-)initialized.

        Returns None or a list of `(property, value, unit)` tuples, similarly
        to `get_status()`.
        """

        fw = self.firmware_version

        return [("Firmware version", fw, "")]

    def _get_status_directly(self):
        msg = self._read()

        sensor_readings = []

        # Read temp sensor values
        for label, offset in zip(self._device_info["temp_sensors_label"], self._device_info["temp_sensors"]):
            temp_sensor_value = u16be_from(msg, offset)

            if temp_sensor_value != _AQC_TEMP_SENSOR_DISCONNECTED:
                temp_sensor_reading = (
                    label,
                    temp_sensor_value * 1e-2,
                    "°C",
                )
                sensor_readings.append(temp_sensor_reading)

        # Read fan speed and related values
        for idx, fan_sensor_offset in enumerate(self._device_info["fan_sensors"]):
            fan_speed = (
                self._device_info["fan_speed_label"][idx],
                u16be_from(msg, fan_sensor_offset + _AQC_FAN_SPEED_OFFSET),
                "rpm",
            )
            sensor_readings.append(fan_speed)

            fan_power = (
                self._device_info["fan_power_label"][idx],
                u16be_from(msg, fan_sensor_offset + _AQC_FAN_POWER_OFFSET) * 1e-2,
                "W",
            )
            sensor_readings.append(fan_power)

            fan_voltage = (
                self._device_info["fan_voltage_label"][idx],
                u16be_from(msg, fan_sensor_offset + _AQC_FAN_VOLTAGE_OFFSET) * 1e-2,
                "V",
            )
            sensor_readings.append(fan_voltage)

            fan_current = (
                self._device_info["fan_current_label"][idx],
                u16be_from(msg, fan_sensor_offset + _AQC_FAN_CURRENT_OFFSET) * 1e-3,
                "A",
            )
            sensor_readings.append(fan_current)

        # Special-case sensor readings
        if self._device_info["type"] == self._DEVICE_D5NEXT:
            # Read +5V voltage rail value
            plus_5v_voltage = (
                "+5V voltage",
                u16be_from(msg, self._device_info["plus_5v_voltage"]) * 1e-2,
                "V",
            )
            sensor_readings.append(plus_5v_voltage)

            # Read +12V voltage rail value
            plus_12v_voltage = (
                "+12V voltage",
                u16be_from(msg, self._device_info["plus_12v_voltage"]) * 1e-2,
                "V",
            )
            sensor_readings.append(plus_12v_voltage)

        return sensor_readings

    def _get_status_from_hwmon(self):
        sensor_readings = []

        # Read temp sensor values
        for idx, temp_sensor_offset in enumerate(self._device_info["temp_sensors"]):
            temp_sensor_reading = (
                self._device_info["temp_sensors_label"][idx],
                self._hwmon.get_int(f"temp{idx + 1}_input") * 1e-3,
                "°C",
            )
            sensor_readings.append(temp_sensor_reading)

        # Read fan speed and related values
        for idx, fan_sensor_offset in enumerate(self._device_info["fan_sensors"]):
            fan_speed = (
                self._device_info["fan_speed_label"][idx],
                self._hwmon.get_int(f"fan{idx + 1}_input"),
                "rpm",
            )
            sensor_readings.append(fan_speed)

            fan_power = (
                self._device_info["fan_power_label"][idx],
                self._hwmon.get_int(f"power{idx + 1}_input") * 1e-6,
                "W",
            )
            sensor_readings.append(fan_power)

            fan_voltage = (
                self._device_info["fan_voltage_label"][idx],
                self._hwmon.get_int(f"in{idx}_input") * 1e-3,
                "V",
            )
            sensor_readings.append(fan_voltage)

            fan_current = (
                self._device_info["fan_current_label"][idx],
                self._hwmon.get_int(f"curr{idx + 1}_input") * 1e-3,
                "A",
            )
            sensor_readings.append(fan_current)

        # Special-case sensor readings
        if self._device_info["type"] == self._DEVICE_D5NEXT:
            # Read +5V voltage rail value
            plus_5v_voltage = ("+5V voltage", self._hwmon.get_int("in2_input") * 1e-3, "V")
            sensor_readings.append(plus_5v_voltage)

            if self._hwmon.has_attribute("in3_input"):
                # The driver exposes the +12V voltage of the pump (kernel v5.20+), read the value
                plus_12v_voltage = ("+12V voltage", self._hwmon.get_int("in3_input") * 1e-3, "V")
                sensor_readings.append(plus_12v_voltage)
            else:
                _LOGGER.warning(
                    "some attributes cannot be read from %s kernel driver", self._hwmon.module
                )

        return sensor_readings

    def get_status(self, direct_access=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        if self._hwmon and not direct_access:
            _LOGGER.info("bound to %s kernel driver, reading status from hwmon", self._hwmon.module)
            return self._get_status_from_hwmon()

        if self._hwmon:
            _LOGGER.warning(
                "directly reading the status despite %s kernel driver", self._hwmon.module
            )

        return self._get_status_directly()

    def set_speed_profile(self, channel, profile, **kwargs):
        # Not yet reverse engineered / implemented
        raise NotSupportedByDriver()

    def set_fixed_speed(self, channel, duty, **kwargs):
        # Not yet implemented
        raise NotSupportedByDriver()

    def set_color(self, channel, mode, colors, **kwargs):
        # Not yet reverse engineered / implemented
        raise NotSupportedByDriver()

    @property
    def firmware_version(self):
        if self._firmware_version is None:
            _ = self._read(clear_first=False)
        return self._firmware_version

    def _read(self, clear_first=True):
        if clear_first:
            self.device.clear_enqueued_reports()
        msg = self.device.read(self._device_info["status_report_length"])
        self._firmware_version = u16be_from(msg, 0xD)
        return msg
