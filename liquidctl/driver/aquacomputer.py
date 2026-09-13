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

import colorsys, logging, time, errno

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDriver, NotSupportedByDevice
from liquidctl.util import u16be_from, clamp, interpolate_profile, mkCrcFun, normalize_profile

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
_AQC_FAN_SOURCE_OFFSET = 0x03

# Fan controller types; the "direct percent" value is what _set_fixed_speed_directly
# selects, and the curve type makes the device follow the stored temperature/power
# points instead
_AQC_FAN_TYPE_PERCENT = 0x00
_AQC_FAN_TYPE_CURVE = 0x02

# Each fan controller stores a fixed number of (temperature, power) points, with
# temperatures in centidegrees Celsius and powers in centipercent
_AQC_CURVE_POINT_COUNT = 16
_AQC_CURVE_TEMP_OFFSET = 0x15
_AQC_CURVE_POWER_OFFSET = 0x35

# Octo RGBpx lighting: the control report holds a fixed number of LED controller
# records, each covering a range of LEDs on one of the strips
_AQC_LED_CTRL_SIZE = 0x46
_AQC_LED_STRIP_ID_OFFSET = 0x00
_AQC_LED_START_OFFSET = 0x01
_AQC_LED_COUNT_OFFSET = 0x02
_AQC_LED_MODE_OFFSET = 0x03
_AQC_LED_COLOR_OFFSET = 0x2E

_AQC_LED_MODE_UNUSED = 0x00
_AQC_LED_MODE_FIXED = 0x01

# Colors are stored as HSV, with the hue scaled to [0, _AQC_LED_MAX_HUE] rather
# than to degrees
_AQC_LED_MAX_HUE = 1535


def put_unaligned_be16(value, data, offset):
    value_be = bytearray(value.to_bytes(2, "big"))
    data[offset], data[offset + 1] = value_be[0], value_be[1]


class Aquacomputer(UsbHidDriver):
    _DEVICE_D5NEXT = "D5 Next"
    _DEVICE_FARBWERK = "Farbwerk"
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
            "fan_speed_label": ["Pump speed", "Fan speed"],
            "fan_power_label": ["Pump power", "Fan power"],
            "fan_voltage_label": ["Pump voltage", "Fan voltage"],
            "fan_current_label": ["Pump current", "Fan current"],
            "status_report_length": 0x9E,
            "ctrl_report_length": 0x329,
            "fan_ctrl": {"pump": 0x96, "fan": 0x41},
            "hwmon_ctrl_mapping": {"pump": "pwm1", "fan": "pwm2"},
        },
        _DEVICE_FARBWERK: {
            "type": _DEVICE_FARBWERK,
            "temp_sensors": [0x2F, 0x31, 0x33, 0x35],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "status_report_length": 0xB6,
        },
        _DEVICE_FARBWERK360: {
            "type": _DEVICE_FARBWERK360,
            "temp_sensors": [0x32, 0x34, 0x36, 0x38],
            "virt_temp_sensors": [0x3A + offset * 2 for offset in range(0, 16)],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "virt_temp_sensors_label": [f"Soft. Sensor {num}" for num in range(1, 16 + 1)],
            "status_report_length": 0xB6,
        },
        _DEVICE_OCTO: {
            "type": _DEVICE_OCTO,
            "fan_sensors": [0x7D, 0x8A, 0x97, 0xA4, 0xB1, 0xBE, 0xCB, 0xD8],
            "temp_sensors": [0x3D, 0x3F, 0x41, 0x43],
            "virt_temp_sensors": [0x45 + offset * 2 for offset in range(0, 16)],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "virt_temp_sensors_label": [f"Soft. Sensor {num}" for num in range(1, 16 + 1)],
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
            "led_ctrl": {
                f"led{num}": 0x307 + (num - 1) * _AQC_LED_CTRL_SIZE for num in range(1, 12 + 1)
            },
        },
        _DEVICE_QUADRO: {
            "type": _DEVICE_QUADRO,
            "fan_sensors": [0x70, 0x7D, 0x8A, 0x97],
            "temp_sensors": [0x34, 0x36, 0x38, 0x3A],
            "virt_temp_sensors": [0x3C + offset * 2 for offset in range(0, 16)],
            "temp_sensors_label": ["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"],
            "virt_temp_sensors_label": [f"Soft. Sensor {num}" for num in range(1, 16 + 1)],
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
            0xF00A,
            "Aquacomputer Farbwerk",
            {"device_info": _DEVICE_INFO[_DEVICE_FARBWERK]},
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
        def _read_temp_sensors(offsets_key, labels_key):
            for idx, temp_sensor_offset in enumerate(self._device_info.get(offsets_key, [])):
                temp_sensor_value = u16be_from(msg, temp_sensor_offset)
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
        _read_temp_sensors("temp_sensors", "temp_sensors_label")

        # Read virtual temp sensor values
        _read_temp_sensors("virt_temp_sensors", "virt_temp_sensors_label")

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
        def _read_temp_sensors(offsets_key, labels_key, idx_add=0):
            encountered_errors = False

            for idx, temp_sensor_offset in enumerate(self._device_info.get(offsets_key, [])):
                try:
                    hwmon_val = self._hwmon.read_int(f"temp{idx + 1 + idx_add}_input") * 1e-3
                except OSError as os_error:
                    # For reference, the driver returns ENODATA when a sensor is unset/empty. ENOENT means that the
                    # current driver version does not support virtual sensors, warn the user later
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

    def set_speed_profile(
        self, channel, profile, temperature_sensor=None, direct_access=False, **kwargs
    ):
        """Set a fan to follow a speed profile.

        Valid channel values are 'fanN', where N >= 1 is the fan number.

        The profile is a sequence of (temperature, duty) pairs, with
        temperatures in Celsius and duties in percent.  The device stores a
        fixed number of points, so the profile is resampled onto an evenly
        spaced temperature axis that spans it; supplying more or fewer points
        than the device stores is therefore fine.

        The fan is also switched to the curve control type, so that the device
        follows the stored points instead of a fixed duty.
        """

        if self._device_info["type"] in [self._DEVICE_FARBWERK360, self._DEVICE_FARBWERK]:
            raise NotSupportedByDevice()

        if self._device_info["type"] not in [self._DEVICE_OCTO, self._DEVICE_QUADRO]:
            # Not yet reverse engineered / implemented
            raise NotSupportedByDriver()

        if channel not in self._device_info["fan_ctrl"]:
            channels = ", ".join(self._device_info["fan_ctrl"].keys())
            raise ValueError(f"unknown channel, should be one of: {channels}")

        if self._hwmon and not direct_access:
            _LOGGER.warning(
                "required speed profile functionality is not available in %s kernel driver, "
                "falling back to direct access",
                self._hwmon.driver,
            )

        profile = list(profile)
        if not profile:
            raise ValueError("profile must have at least one point")

        # Enforce a monotonic profile, and a failsafe at the highest temperature
        # the user asked for, so the resampling below cannot invent a dip
        critical_temp = max(temp for temp, _ in profile)
        profile = normalize_profile(profile, critical_temp)

        # The device stores a fixed number of points; spread them evenly between
        # the first and last temperatures of the profile and interpolate the
        # duties, which preserves the shape the user asked for
        first_temp, last_temp = profile[0][0], profile[-1][0]
        steps = _AQC_CURVE_POINT_COUNT - 1
        span = last_temp - first_temp

        points = []
        for i in range(_AQC_CURVE_POINT_COUNT):
            temp = first_temp + (span * i / steps if span else 0)
            duty = clamp(interpolate_profile(profile, temp), 0, 100)
            points.append((temp, duty))

        _LOGGER.debug("setting %s curve to %r", channel, points)

        # Request an up to date ctrl report
        report_length = self._device_info["ctrl_report_length"]
        ctrl_settings = self.device.get_feature_report(_AQC_CTRL_REPORT_ID, report_length)

        fan_ctrl_offset = self._device_info["fan_ctrl"][channel]

        # Set fan to follow its stored curve
        ctrl_settings[fan_ctrl_offset + _AQC_FAN_TYPE_OFFSET] = _AQC_FAN_TYPE_CURVE
        if temperature_sensor is not None:
            temp_sensor_count = len(self._device_info["temp_sensors"])
            temperature_sensor = clamp(temperature_sensor, 1, temp_sensor_count)
            put_unaligned_be16(
                temperature_sensor - 1,
                ctrl_settings,
                fan_ctrl_offset + _AQC_FAN_SOURCE_OFFSET,
            )

        for i, (temp, duty) in enumerate(points):
            # Centidegrees Celsius and centipercent
            put_unaligned_be16(
                round(temp * 100), ctrl_settings, fan_ctrl_offset + _AQC_CURVE_TEMP_OFFSET + i * 2
            )
            put_unaligned_be16(
                round(duty * 100), ctrl_settings, fan_ctrl_offset + _AQC_CURVE_POWER_OFFSET + i * 2
            )

        self._write_ctrl_report(ctrl_settings)

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
        # Request an up to date ctrl report
        report_length = self._device_info["ctrl_report_length"]
        ctrl_settings = self.device.get_feature_report(_AQC_CTRL_REPORT_ID, report_length)

        fan_ctrl_offset = self._device_info["fan_ctrl"][channel]

        # Set fan to direct percent-value mode
        ctrl_settings[fan_ctrl_offset + _AQC_FAN_TYPE_OFFSET] = 0

        # Write down duty for channel
        put_unaligned_be16(
            duty * 100,  # Centi-percent
            ctrl_settings,
            fan_ctrl_offset + _AQC_FAN_PERCENT_OFFSET,
        )

        self._write_ctrl_report(ctrl_settings)

    def _write_ctrl_report(self, ctrl_settings):
        """Update the report's checksum and send it to the device."""

        report_length = self._device_info["ctrl_report_length"]

        # Update checksum value at the end of the report
        crc16usb_func = mkCrcFun("crc-16-usb")

        checksum_part = bytes(ctrl_settings[0x01 : report_length - 3 + 1])
        checksum_bytes = crc16usb_func(checksum_part)
        put_unaligned_be16(checksum_bytes, ctrl_settings, report_length - 2)

        # Some devices (Octo, Quadro and Aquaero) can not accept reports in quick succession, so slow down a bit
        time.sleep(0.2)

        self.device.send_feature_report(ctrl_settings)

    def set_fixed_speed(self, channel, duty, direct_access=False, **kwargs):
        if self._device_info["type"] == self._DEVICE_FARBWERK360:
            raise NotSupportedByDevice()

        # Clamp duty between 0 and 100
        duty = clamp(duty, 0, 100)

        if self._hwmon:
            hwmon_pwm_name, hwmon_pwm_enable_name = self._fan_name_to_hwmon_names(channel)

            # pwmX and pwmX_enable attributes are required in order to set the PWM value,
            # as well as the channel mode to "direct PWM value". Without pwmX_enable,
            # we can't guarantee that the PWM value will at all be used, as the channel
            # could be in a different mode (PID, curve, fan follow).
            if self._hwmon.has_attribute(hwmon_pwm_name) and self._hwmon.has_attribute(
                hwmon_pwm_enable_name
            ):
                # They are, and if we have to use direct access, warn that we are sidestepping the kernel driver
                if direct_access:
                    _LOGGER.warning(
                        "directly writing fixed speed despite %s kernel driver having support",
                        self._hwmon.driver,
                    )
                    return self._set_fixed_speed_directly(channel, duty)

                _LOGGER.info(
                    "bound to %s kernel driver, writing fixed speed to hwmon", self._hwmon.driver
                )
                return self._set_fixed_speed_hwmon(channel, duty)
            elif not direct_access:
                _LOGGER.warning(
                    "required PWM functionality is not available in %s kernel driver, falling back to direct access",
                    self._hwmon.driver,
                )

        self._set_fixed_speed_directly(channel, duty)

    def _rgb_to_hsv(self, color):
        """Convert an 8-bit RGB color to the device's HSV representation."""

        hue, sat, val = colorsys.rgb_to_hsv(color[0] / 255, color[1] / 255, color[2] / 255)

        # the hue is stored scaled to _AQC_LED_MAX_HUE, not in degrees
        return (
            round(hue * _AQC_LED_MAX_HUE) % (_AQC_LED_MAX_HUE + 1),
            round(sat * 255),
            round(val * 255),
        )

    def set_color(self, channel, mode, colors, **kwargs):
        """Set the color of one of the LED controllers.

        Valid channel values are 'ledN', where N is the LED controller number,
        as shown by the device's own configuration software.  Each controller
        covers a range of LEDs on one of the RGBpx strips.

        The 'fixed' mode lights the controller's range in a single color, and
        'off' disables it.  Other lighting modes the device supports are not
        yet reverse engineered.
        """

        if "led_ctrl" not in self._device_info:
            raise NotSupportedByDevice()

        if channel not in self._device_info["led_ctrl"]:
            raise ValueError(f"unknown channel, should be one of: {self._get_led_channels()}")

        colors = list(colors)

        if mode == "off":
            led_mode = _AQC_LED_MODE_UNUSED
            color = (0, 0, 0)
        elif mode == "fixed":
            led_mode = _AQC_LED_MODE_FIXED
            if len(colors) != 1:
                raise ValueError("fixed mode requires exactly one color")
            color = self._rgb_to_hsv(colors[0])
        else:
            raise ValueError("unsupported mode, should be one of: fixed, off")

        # Request an up to date ctrl report
        report_length = self._device_info["ctrl_report_length"]
        ctrl_settings = self.device.get_feature_report(_AQC_CTRL_REPORT_ID, report_length)

        led_ctrl_offset = self._device_info["led_ctrl"][channel]

        ctrl_settings[led_ctrl_offset + _AQC_LED_MODE_OFFSET] = led_mode

        hue, sat, val = color
        put_unaligned_be16(hue, ctrl_settings, led_ctrl_offset + _AQC_LED_COLOR_OFFSET)
        ctrl_settings[led_ctrl_offset + _AQC_LED_COLOR_OFFSET + 2] = sat
        ctrl_settings[led_ctrl_offset + _AQC_LED_COLOR_OFFSET + 3] = val

        self._write_ctrl_report(ctrl_settings)

    def _get_led_channels(self):
        return ", ".join(self._device_info["led_ctrl"].keys())

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
