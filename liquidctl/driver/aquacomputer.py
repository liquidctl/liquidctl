"""liquidctl driver for Aquacomputer family of watercooling devices.

Aquacomputer D5 Next watercooling pump
--------------------------------------
The pump sends a status HID report every second with no initialization
being required.

The status HID report exposes sensor values such as liquid temperature and
two groups of fan sensors, for the pump and the optionally connected fan.
These groups provide RPM speed, voltage, current and power readings. The
pump additionally exposes +5V and +12V voltage rail readings and eight virtual
temperature sensors.

The pump and fan can be set to a fixed speed (0-100%).

Aquacomputer Farbwerk 360
-------------------------
Farbwerk 360 is an RGB controller and sends a status HID report every second
with no initialization being required.

The status HID report exposes four physical and sixteen virtual temperature
sensor values.

Aquacomputer Octo
-------------------------
Octo is a fan/RGB controller and sends a status HID report every second with
no initialization being required.

The status HID report exposes four temperature sensor values and eight groups
of fan sensors for optionally connected fans. Octo additionaly exposes sixteen
virtual temp sensors through this report.

Aquacomputer Quadro
-------------------------
Quadro is a fan/RGB controller and sends a status HID report every second with
no initialization being required.

The status HID report exposes four physical and sixteen virtual temperature sensor
values, and four groups of fan sensors for optionally connected fans.

Driver
------
Linux has the aquacomputer_d5next driver available since v5.15. Subsequent
releases have more functionality and support a wider range of devices
(detailed below). If present, it's used instead of reading the status
reports directly.

Hwmon support:
    - D5 Next watercooling pump: sensors - 5.15+, direct PWM control - not yet in fully
    - Farbwerk 360: sensors - 5.18+
    - Octo: sensors - 5.19+, direct PWM control - not yet in fully
    - Quadro: sensors - 6.0+, direct PWM control - not yet in fully

Virtual temp sensor reading is supported in 6.0+.

Copyright Aleksa Savic and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""
# uses the psf/black style

import logging, time, errno

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDriver, NotSupportedByDevice
from liquidctl.util import u16be_from, clamp, mkCrcFun

_LOGGER = logging.getLogger(__name__)

_AQC_TEMP_SENSOR_DISCONNECTED = 0x7FFF
_AQC_FAN_VOLTAGE_OFFSET = 0x02
_AQC_FAN_CURRENT_OFFSET = 0x04
_AQC_FAN_POWER_OFFSET = 0x06
_AQC_FAN_SPEED_OFFSET = 0x08

_AQC_STATUS_READ_ENDPOINT = 0x01
_AQC_CTRL_REPORT_ID = 0x03

_AQC_FAN_TYPE_OFFSET = 0x00
_AQC_FAN_PERCENT_OFFSET = 0x01


def put_unaligned_be16(value, data, offset):
    value_be = bytearray(value.to_bytes(2, "big"))
    data[offset], data[offset + 1] = value_be[0], value_be[1]


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
            "virt_temp_sensors": [0x3F + offset * 2 for offset in range(0, 8)],
            "plus_5v_voltage": 0x39,
            "plus_12v_voltage": 0x37,
            "temp_sensors_label": ["Liquid temperature"],
            "virt_temp_sensors_label": [f"Soft. Sensor {num}" for num in range(1, 8 + 1)],
            "temp_offsets_label": ["Sensor 1 offset"],
            "fan_speed_label": ["Pump speed", "Fan speed"],
            "fan_power_label": ["Pump power", "Fan power"],
            "fan_voltage_label": ["Pump voltage", "Fan voltage"],
            "fan_current_label": ["Pump current", "Fan current"],
            "status_report_length": 0x9E,
            "ctrl_report_length": 0x329,
            "fan_ctrl": {"pump": 0x96, "fan": 0x41},
            "temp_offset_ctrl": [0x2D],
            "hwmon_ctrl_mapping": {"pump": "pwm1", "fan": "pwm2"},
        },
        _DEVICE_FARBWERK360: {
            "type": _DEVICE_FARBWERK360,
            "temp_sensors": [0x32, 0x34, 0x36, 0x38],
            "virt_temp_sensors": [0x3A + offset * 2 for offset in range(0, 16)],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "virt_temp_sensors_label": [f"Soft. Sensor {num}" for num in range(1, 16 + 1)],
            "temp_offsets_label": [f"Sensor {num} offset" for num in range(1, 4 + 1)],
            "status_report_length": 0xB6,
            "ctrl_report_length": 0x682,
            "temp_offset_ctrl": [0x8 + i * 2 for i in range(0, 4)],
        },
        _DEVICE_OCTO: {
            "type": _DEVICE_OCTO,
            "fan_sensors": [0x7D, 0x8A, 0x97, 0xA4, 0xB1, 0xBE, 0xCB, 0xD8],
            "temp_sensors": [0x3D, 0x3F, 0x41, 0x43],
            "virt_temp_sensors": [0x45 + offset * 2 for offset in range(0, 16)],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "virt_temp_sensors_label": [f"Soft. Sensor {num}" for num in range(1, 16 + 1)],
            "temp_offsets_label": [f"Sensor {num} offset" for num in range(1, 4 + 1)],
            "fan_speed_label": [f"Fan {num} speed" for num in range(1, 8 + 1)],
            "fan_power_label": [f"Fan {num} power" for num in range(1, 8 + 1)],
            "fan_voltage_label": [f"Fan {num} voltage" for num in range(1, 8 + 1)],
            "fan_current_label": [f"Fan {num} current" for num in range(1, 8 + 1)],
            "status_report_length": 0x147,
            "ctrl_report_length": 0x65F,
            "fan_ctrl": {
                name: offset
                for (name, offset) in zip(
                    [f"fan{i}" for i in range(1, 8 + 1)],
                    [0x5A, 0xAF, 0x104, 0x159, 0x1AE, 0x203, 0x258, 0x2AD],
                )
            },
            "temp_offset_ctrl": [0xA + i * 2 for i in range(0, 4)],
        },
        _DEVICE_QUADRO: {
            "type": _DEVICE_QUADRO,
            "fan_sensors": [0x70, 0x7D, 0x8A, 0x97],
            "temp_sensors": [0x34, 0x36, 0x38, 0x3A],
            "virt_temp_sensors": [0x3C + offset * 2 for offset in range(0, 16)],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "virt_temp_sensors_label": [f"Soft. Sensor {num}" for num in range(1, 16 + 1)],
            "temp_offsets_label": [f"Sensor {num} offset" for num in range(1, 4 + 1)],
            "fan_speed_label": [f"Fan {num} speed" for num in range(1, 4 + 1)],
            "fan_power_label": [f"Fan {num} power" for num in range(1, 4 + 1)],
            "fan_voltage_label": [f"Fan {num} voltage" for num in range(1, 4 + 1)],
            "fan_current_label": [f"Fan {num} current" for num in range(1, 4 + 1)],
            "flow_sensor_offset": 0x6E,
            "status_report_length": 0xDC,
            "ctrl_report_length": 0x3C1,
            "fan_ctrl": {
                name: offset
                for (name, offset) in zip(
                    [f"fan{i}" for i in range(1, 4 + 1)],
                    [0x36, 0x8B, 0xE0, 0x135],
                )
            },
            "temp_offset_ctrl": [0xA + i * 2 for i in range(0, 4)],
        },
    }

    _MATCHES = [
        (
            0x0C70,
            0xF00E,
            "Aquacomputer D5 Next (experimental)",
            {"device_info": _DEVICE_INFO[_DEVICE_D5NEXT]},
        ),
        (
            0x0C70,
            0xF010,
            "Aquacomputer Farbwerk 360 (experimental)",
            {"device_info": _DEVICE_INFO[_DEVICE_FARBWERK360]},
        ),
        (
            0x0C70,
            0xF011,
            "Aquacomputer Octo (experimental)",
            {"device_info": _DEVICE_INFO[_DEVICE_OCTO]},
        ),
        (
            0x0C70,
            0xF00D,
            "Aquacomputer Quadro (experimental)",
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
        def _read_temp_sensors(offsets_key, labels_key, report, read_signed=False):
            for idx, temp_sensor_offset in enumerate(self._device_info.get(offsets_key, [])):
                temp_sensor_value = u16be_from(report, temp_sensor_offset, read_signed)

                if temp_sensor_value != _AQC_TEMP_SENSOR_DISCONNECTED:
                    temp_sensor_reading = (
                        self._device_info[labels_key][idx],
                        temp_sensor_value * 1e-2,
                        "°C",
                    )
                    sensor_readings.append(temp_sensor_reading)

        msg = self._read()

        sensor_readings = []

        # Read temp sensor values
        _read_temp_sensors("temp_sensors", "temp_sensors_label", msg)

        # Read virtual temp sensor values
        _read_temp_sensors("virt_temp_sensors", "virt_temp_sensors_label", msg)

        # Read temp sensor offets
        _, ctrl_report = self._request_ctrl_report()
        _read_temp_sensors("temp_offset_ctrl", "temp_offsets_label", ctrl_report, True)

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
        def _read_temp_sensors(offsets_key, labels_key, idx_add=0, entry_suffix="input"):
            encountered_errors = False

            for idx, _ in enumerate(self._device_info.get(offsets_key, [])):
                try:
                    hwmon_val = (
                        self._hwmon.read_int(f"temp{idx + 1 + idx_add}_{entry_suffix}") * 1e-3
                    )
                except OSError as os_error:
                    # For reference, the driver returns ENODATA when a sensor is unset/empty. ENOENT means that the
                    # current driver version does not support the requested sensors, warn the user later
                    if os_error.errno == errno.ENOENT:
                        encountered_errors = True
                    continue

                temp_sensor_reading = (
                    self._device_info[labels_key][idx],
                    hwmon_val,
                    "°C",
                )
                sensor_readings.append(temp_sensor_reading)

            if encountered_errors:
                _LOGGER.warning(
                    f"some temp sensors cannot be read from %s kernel driver",
                    self._hwmon.driver,
                )

        sensor_readings = []

        # Read temp sensor values
        _read_temp_sensors("temp_sensors", "temp_sensors_label")

        # Read virtual temp sensor values
        _read_temp_sensors(
            "virt_temp_sensors",
            "virt_temp_sensors_label",
            len(self._device_info.get("temp_sensors", [])),
        )

        # Read temp sensor offsets
        _read_temp_sensors("temp_sensors", "temp_offsets_label", entry_suffix="offset")

        # Read fan speed and related values
        for idx, fan_sensor_offset in enumerate(self._device_info.get("fan_sensors", [])):
            fan_speed = (
                self._device_info["fan_speed_label"][idx],
                self._hwmon.read_int(f"fan{idx + 1}_input"),
                "rpm",
            )
            sensor_readings.append(fan_speed)

            fan_power = (
                self._device_info["fan_power_label"][idx],
                self._hwmon.read_int(f"power{idx + 1}_input") * 1e-6,
                "W",
            )
            sensor_readings.append(fan_power)

            fan_voltage = (
                self._device_info["fan_voltage_label"][idx],
                self._hwmon.read_int(f"in{idx}_input") * 1e-3,
                "V",
            )
            sensor_readings.append(fan_voltage)

            fan_current = (
                self._device_info["fan_current_label"][idx],
                self._hwmon.read_int(f"curr{idx + 1}_input") * 1e-3,
                "A",
            )
            sensor_readings.append(fan_current)

        # Special-case sensor readings
        if self._device_info["type"] == self._DEVICE_D5NEXT:
            # Read +5V voltage rail value
            plus_5v_voltage = ("+5V voltage", self._hwmon.read_int("in2_input") * 1e-3, "V")
            sensor_readings.append(plus_5v_voltage)

            if self._hwmon.has_attribute("in3_input"):
                # The driver exposes the +12V voltage of the pump (kernel v6.0+), read the value
                plus_12v_voltage = ("+12V voltage", self._hwmon.read_int("in3_input") * 1e-3, "V")
                sensor_readings.append(plus_12v_voltage)
            else:
                _LOGGER.warning(
                    "+12V voltage cannot be read from %s kernel driver", self._hwmon.driver
                )
        elif self._device_info["type"] == self._DEVICE_QUADRO:
            # Read flow sensor value
            flow_sensor_value = ("Flow sensor", self._hwmon.read_int("fan5_input"), "dL/h")
            sensor_readings.append(flow_sensor_value)

        return sensor_readings

    def get_status(self, direct_access=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        if self._hwmon and not direct_access:
            _LOGGER.info("bound to %s kernel driver, reading status from hwmon", self._hwmon.driver)
            return self._get_status_from_hwmon()

        if self._hwmon:
            _LOGGER.warning(
                "directly reading the status despite %s kernel driver", self._hwmon.driver
            )

        return self._get_status_directly()

    def _request_ctrl_report(self):
        """Request an up to date ctrl report."""
        report_length = self._device_info["ctrl_report_length"]
        return report_length, self.device.get_feature_report(_AQC_CTRL_REPORT_ID, report_length)

    def _update_device_ctrl_report(self, processing_func):
        report_length, ctrl_report = self._request_ctrl_report()

        # Let the caller make changes to it
        processing_func(ctrl_report)

        # Update checksum value at the end of the report
        crc16usb_func = mkCrcFun("crc-16-usb")

        checksum_part = bytes(ctrl_report[0x01 : report_length - 3 + 1])
        checksum_bytes = crc16usb_func(checksum_part)
        put_unaligned_be16(checksum_bytes, ctrl_report, report_length - 2)

        self.device.send_feature_report(ctrl_report)

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

    def _fan_name_to_hwmon_names(self, channel):
        if "hwmon_ctrl_mapping" in self._device_info:
            # Custom fan name to hwmon pwmX translation
            pwm_name = self._device_info["hwmon_ctrl_mapping"][channel]
        else:
            # Otherwise, assume that fanX translates to pwmX
            pwm_name = f"pwm{channel[3]}"

        return pwm_name, f"{pwm_name}_enable"

    def _set_fixed_speed_hwmon(self, channel, duty):
        hwmon_pwm_name, hwmon_pwm_enable_name = self._fan_name_to_hwmon_names(channel)

        # Set channel to direct percent mode
        self._hwmon.write_int(hwmon_pwm_enable_name, 1)

        # Some devices (Octo, Quadro and Aquaero) can not accept reports in quick succession, so slow down a bit
        time.sleep(0.2)

        # Convert duty from percent to PWM range (0-255)
        pwm_duty = duty * 255 // 100

        # Write to hwmon
        self._hwmon.write_int(hwmon_pwm_name, pwm_duty)

    def _set_fixed_speed_directly(self, channel, duty):
        def _set_fixed_speed_ctrl_report(ctrl_report):
            fan_ctrl_offset = self._device_info["fan_ctrl"][channel]

            # Set fan to direct percent-value mode
            ctrl_report[fan_ctrl_offset + _AQC_FAN_TYPE_OFFSET] = 0

            # Write down duty for channel
            put_unaligned_be16(
                duty * 100,  # Centi-percent
                ctrl_report,
                fan_ctrl_offset + _AQC_FAN_PERCENT_OFFSET,
            )

        self._update_device_ctrl_report(_set_fixed_speed_ctrl_report)

    def _perform_write(
        self, direct_access, hwmon_check_func, hwmon_func, direct_access_func, explanation
    ):
        """Decides whether to route the write request through hwmon or directly to the device."""
        if self._hwmon:
            if hwmon_check_func():
                # Check passed - if we have to use direct access, warn that we are sidestepping the kernel driver
                if direct_access:
                    _LOGGER.warning(
                        f"directly writing {explanation} despite {self._hwmon.driver} kernel driver having support"
                    )
                    return direct_access_func()

                _LOGGER.info(
                    f"bound to {self._hwmon.driver} kernel driver, writing {explanation} to hwmon"
                )
                return hwmon_func()
            elif not direct_access:
                _LOGGER.warning(
                    f"required {explanation} functionality is not available in {self._hwmon.driver} kernel driver, "
                    f"falling back to direct access",
                )

        direct_access_func()

    def set_fixed_speed(self, channel, duty, direct_access=False, **kwargs):
        if self._device_info["type"] == self._DEVICE_FARBWERK360:
            raise NotSupportedByDevice()

        # Clamp duty between 0 and 100
        duty = clamp(duty, 0, 100)

        def _hwmon_check():
            hwmon_pwm_name, hwmon_pwm_enable_name = self._fan_name_to_hwmon_names(channel)
            return self._hwmon.has_attribute(hwmon_pwm_name) and self._hwmon.has_attribute(
                hwmon_pwm_enable_name
            )

        self._perform_write(
            direct_access,
            lambda: _hwmon_check(),
            lambda: self._set_fixed_speed_hwmon(channel, duty),
            lambda: self._set_fixed_speed_directly(channel, duty),
            "fixed speed",
        )

    def set_color(self, channel, mode, colors, **kwargs):
        # Not yet reverse engineered / implemented
        raise NotSupportedByDriver()

    def _set_tempoffset_directly(self, channel, value):
        def _set_tempoffset_ctrl_report(ctrl_report):
            temp_offset_position = self._device_info["temp_offset_ctrl"][channel]

            # Write down temp offset for channel
            put_unaligned_be16(
                value // 10,
                ctrl_report,
                temp_offset_position,
            )

        self._update_device_ctrl_report(_set_tempoffset_ctrl_report)

    def _set_tempoffset_hwmon(self, channel, value):
        self._hwmon.write_int(f"temp{channel+1}_offset", value)

    def set_tempoffset(self, channel, value, direct_access=False, **kwargs):
        channel_idx = int(channel[-1]) - 1
        final_value = int(round(clamp(value, -15, 15), 2) * 1000)

        def _hwmon_check():
            return self._hwmon.has_attribute(f"temp{channel_idx+1}_offset")

        self._perform_write(
            direct_access,
            lambda: _hwmon_check(),
            lambda: self._set_tempoffset_hwmon(channel_idx, final_value),
            lambda: self._set_tempoffset_directly(channel_idx, final_value),
            "temp offset",
        )

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
