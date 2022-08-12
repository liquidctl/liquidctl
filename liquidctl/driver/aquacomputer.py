"""liquidctl driver for Aquacomputer family of watercooling devices.

Aquacomputer D5 Next watercooling pump
--------------------------------------
The pump sends a status HID report every second with no initialization
being required.

The status HID report exposes sensor values such as liquid temperature and
two groups of fan sensors, for the pump and the optionally connected fan.
These groups provide RPM speed, voltage, current and power readings. The
pump additionally exposes +5V and +12V voltage rail readings.

Aquacomputer Farbwerk 360
-------------------------
Farbwerk 360 is an RGB controller and sends a status HID report every second
with no initialization being required.

The status HID report exposes four temperature sensor values.

Aquacomputer Octo
-------------------------
Octo is a fan/RGB controller and sends a status HID report every second with
no initialization being required.

The status HID report exposes four temperature sensor values and eight groups
of fan sensors for optionally connected fans.

Aquacomputer Quadro
-------------------------
Quadro is a fan/RGB controller and sends a status HID report every second with
no initialization being required.

The status HID report exposes four temperature sensor values and four groups
of fan sensors for optionally connected fans.

Driver
------
Linux has the aquacomputer_d5next driver available since v5.15. Subsequent
releases have more functionality and support a wider range of devices
(detailed below). If present, it's used instead of reading the status
reports directly.

Hwmon support:
    - D5 Next watercooling pump: sensors - 5.15+
    - Farbwerk 360: sensors - 5.18+
    - Octo: sensors - 5.19+
    - Quadro: sensors - 6.0+

Copyright (C) 2022 - Aleksa Savic

SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDriver, NotSupportedByDevice
from liquidctl.util import u16be_from

_LOGGER = logging.getLogger(__name__)

_AQC_TEMP_SENSOR_DISCONNECTED = 0x7FFF
_AQC_FAN_VOLTAGE_OFFSET = 0x02
_AQC_FAN_CURRENT_OFFSET = 0x04
_AQC_FAN_POWER_OFFSET = 0x06
_AQC_FAN_SPEED_OFFSET = 0x08

_AQC_STATUS_READ_ENDPOINT = 0x01


class Aquacomputer(UsbHidDriver):
    _DEVICE_D5NEXT = "D5 Next"
    _DEVICE_FARBWERK360 = "Farbwerk 360"
    _DEVICE_OCTO = "Octo"
    _DEVICE_QUADRO = "Quadro"

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
        },
        _DEVICE_FARBWERK360: {
            "type": _DEVICE_FARBWERK360,
            "temp_sensors": [0x32, 0x34, 0x36, 0x38],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "status_report_length": 0xB6,
        },
        _DEVICE_OCTO: {
            "type": _DEVICE_OCTO,
            "fan_sensors": [0x7D, 0x8A, 0x97, 0xA4, 0xB1, 0xBE, 0xCB, 0xD8],
            "temp_sensors": [0x3D, 0x3F, 0x41, 0x43],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "fan_speed_label": [f"Fan {num} speed" for num in range(1, 8 + 1)],
            "fan_power_label": [f"Fan {num} power" for num in range(1, 8 + 1)],
            "fan_voltage_label": [f"Fan {num} voltage" for num in range(1, 8 + 1)],
            "fan_current_label": [f"Fan {num} current" for num in range(1, 8 + 1)],
            "status_report_length": 0x147,
        },
        _DEVICE_QUADRO: {
            "type": _DEVICE_QUADRO,
            "fan_sensors": [0x70, 0x7D, 0x8A, 0x97],
            "temp_sensors": [0x34, 0x36, 0x38, 0x3A],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "fan_speed_label": [f"Fan {num} speed" for num in range(1, 4 + 1)],
            "fan_power_label": [f"Fan {num} power" for num in range(1, 4 + 1)],
            "fan_voltage_label": [f"Fan {num} voltage" for num in range(1, 4 + 1)],
            "fan_current_label": [f"Fan {num} current" for num in range(1, 4 + 1)],
            "flow_sensor_offset": 0x6E,
            "status_report_length": 0xDC,
        },
    }

    _MATCHES = [
        (
            0x0C70,
            0xF00E,
            "Aquacomputer D5 Next",
            {"device_info": _DEVICE_INFO[_DEVICE_D5NEXT]},
        ),
        (
            0x0C70,
            0xF010,
            "Aquacomputer Farbwerk 360",
            {"device_info": _DEVICE_INFO[_DEVICE_FARBWERK360]},
        ),
        (
            0x0C70,
            0xF011,
            "Aquacomputer Octo",
            {"device_info": _DEVICE_INFO[_DEVICE_OCTO]},
        ),
        (
            0x0C70,
            0xF00D,
            "Aquacomputer Quadro",
            {"device_info": _DEVICE_INFO[_DEVICE_QUADRO]},
        ),
    ]

    def __init__(self, device, description, device_info, **kwargs):
        super().__init__(device, description)

        # Read when necessary
        self._firmware_version = None
        self._serial = None

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
        serial_number = self._serial_number

        return [("Firmware version", fw, ""), ("Serial number", serial_number, "")]

    def _get_status_directly(self):
        msg = self._read()

        sensor_readings = []

        # Read temp sensor values
        for idx, temp_sensor_offset in enumerate(self._device_info.get("temp_sensors", [])):
            temp_sensor_value = u16be_from(msg, temp_sensor_offset)

            if temp_sensor_value != _AQC_TEMP_SENSOR_DISCONNECTED:
                temp_sensor_reading = (
                    self._device_info["temp_sensors_label"][idx],
                    temp_sensor_value * 1e-2,
                    "°C",
                )
                sensor_readings.append(temp_sensor_reading)

        # Read fan speed and related values
        for idx, fan_sensor_offset in enumerate(self._device_info.get("fan_sensors", [])):
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
        elif self._device_info["type"] == self._DEVICE_QUADRO:
            # Read flow sensor value
            flow_sensor_value = (
                "Flow sensor",
                u16be_from(msg, self._device_info["flow_sensor_offset"]),
                "dL/h",
            )
            sensor_readings.append(flow_sensor_value)

        return sensor_readings

    def _get_status_from_hwmon(self):
        sensor_readings = []

        # Read temp sensor values
        for idx, temp_sensor_offset in enumerate(self._device_info.get("temp_sensors", [])):
            temp_sensor_reading = (
                self._device_info["temp_sensors_label"][idx],
                self._hwmon.get_int(f"temp{idx + 1}_input") * 1e-3,
                "°C",
            )
            sensor_readings.append(temp_sensor_reading)

        # Read fan speed and related values
        for idx, fan_sensor_offset in enumerate(self._device_info.get("fan_sensors", [])):
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
        elif self._device_info["type"] == self._DEVICE_QUADRO:
            # Read flow sensor value
            flow_sensor_value = ("Flow sensor", self._hwmon.get_int("fan5_input"), "dL/h")
            sensor_readings.append(flow_sensor_value)

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
        if (
            self._device_info["type"] == self._DEVICE_D5NEXT
            or self._device_info["type"] == self._DEVICE_OCTO
            or self._device_info["type"] == self._DEVICE_QUADRO
        ):
            # Not yet reverse engineered / implemented
            raise NotSupportedByDriver()
        elif self._device_info["type"] == self._DEVICE_FARBWERK360:
            raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        if (
            self._device_info["type"] == self._DEVICE_D5NEXT
            or self._device_info["type"] == self._DEVICE_OCTO
            or self._device_info["type"] == self._DEVICE_QUADRO
        ):
            # Not yet implemented
            raise NotSupportedByDriver()
        elif self._device_info["type"] == self._DEVICE_FARBWERK360:
            raise NotSupportedByDevice()

    def set_color(self, channel, mode, colors, **kwargs):
        # Not yet reverse engineered / implemented
        raise NotSupportedByDriver()

    def _read_device_statics(self):
        if self._firmware_version is None or self._serial is None:
            msg = self._read(clear_first=False)

            self._firmware_version = u16be_from(msg, 0xD)
            self._serial = f"{u16be_from(msg, 0x3):05}-{u16be_from(msg, 0x5):05}"

    @property
    def firmware_version(self):
        self._read_device_statics()
        return self._firmware_version

    @property
    def _serial_number(self):
        self._read_device_statics()
        return self._serial

    def _read(self, clear_first=True):
        if clear_first:
            self.device.clear_enqueued_reports()
        msg = self.device.read(self._device_info["status_report_length"])
        return msg
