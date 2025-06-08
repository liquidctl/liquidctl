"""liquidctl driver for the Razer Hanbo Chroma series of AIO liquid coolers

Supported devices
-----------------

- Razer Hanbo Chroma 360mm

Supported features
------------------

- General monitoring
- Pump profile support
- Fan profile support
- Hwmon offloading with direct-mode fallback

A defining feature of the Razer Hanbo is the lack of direct PWM modes.
Instead the fan and pump can select from a set of three built-in
profiles and one custom profile - the fan and pump profiles operate
independently. All pump profiles use the coolant temperature measured
internally as a reference and do not need user interaction once enabled.
Fan profiles however rely on an external reference temperature being
updated in order traverse its curve. Without it the AIO will
continue using whatever duty cycle is allocated to the default CPU
temperature which is nominated to be 30°C.

When setting a custom profile, be aware that the temperature points in the
curve are fixed. For this reason any temperatures provided to input curves
will be ignored but must be present for the purposes of parsing. Duty cycles
will be processed in order and allocated to the following temperatures

20, 30, 40, 50, 60, 70 ,80, 90, 100.

Copyright Joseph East
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import logging

from collections import namedtuple
from functools import reduce

from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver
from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.util import clamp, u16be_from

_LOGGER = logging.getLogger(__name__)

_FW_COMMAND = namedtuple("_FW_COMMAND", "header has_payload")

_REPORT_LENGTH = 64
_MAX_DUTIES = 9
_MAX_READ_RETRIES = 5

_HWMON_CTRL_MAPPING = {"pump": 1, "fan": 2}
_CUSTOM_PROFILE_ID = 4
_PROFILE_MAPPING = {
    "quiet": (0x01, 0x14),
    "balanced": (0x02, 0x32),
    "extreme": (0x03, 0x50),
    "custom": (_CUSTOM_PROFILE_ID,),
}

_MINIMUM_THERMAL_UNIT = 20
_MAXIMUM_THERMAL_UNIT = 100
_DEFAULT_CPU_TEMP_DEGREES_C = 30

_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_PUMP_PROFILE = "Pump profile"
_STATUS_FAN_SPEED = "Fan speed"
_STATUS_FAN_DUTY = "Fan duty"
_STATUS_FAN_PROFILE = "Fan profile"


class _RazerHanboCommands:
    get_firmware = _FW_COMMAND((0x01, 0x01), False)
    get_pump_status = _FW_COMMAND((0x12, 0x01), False)
    set_pump_profile = _FW_COMMAND((0x14, 0x01), True)
    set_pump_curve = _FW_COMMAND((0x18, 0x01, 0x01, 0x00), True)
    get_fan_status = _FW_COMMAND((0x20, 0x01), False)
    set_fan_profile = _FW_COMMAND((0x22, 0x01), True)
    set_ref_temp = _FW_COMMAND((0xC0, 0x01), True)
    set_fan_curve = _FW_COMMAND((0xC8, 0x01, 0x00, 0x00), True)


class _RazerHanboReplies:
    firmware = (34, 0x02, 0x02)
    pump_status = (11, 0x13, 0x02, 0x01)
    pump_profile = (3, 0x15, 0x02, 0x01)
    pump_curve = (3, 0x19, 0x02, 0x01)
    fan_status = (10, 0x21, 0x02, 0x02, 0x01)
    fan_profile = (3, 0x23, 0x02, 0x01)
    bright = (4, 0x71, 0x02)
    bright_status = (4, 0x73, 0x02)
    rgb = (2, 0x81, 0x02, 0x01)
    rgb_state = (4, 0x83, 0x02)
    ref_temp = (3, 0xC1, 0x02, 0x01)
    fan_curve = (3, 0xC9, 0x02, 0x01)


class RazerHanbo(UsbHidDriver):
    """liquidctl driver for the Razer Hanbo Chroma cooler"""

    _custom_profiles = {
        "pump": [0x14, 0x28, 0x3C, 0x50, 0x64, 0x64, 0x64, 0x64, 0x64],
        "fan": [0x18, 0x1E, 0x28, 0x30, 0x3C, 0x51, 0x64, 0x64, 0x64],
    }
    _MATCHES = [
        (
            0x1532,
            0x0F35,
            "Razer Hanbo Chroma",
            {},
        ),
    ]
    HAS_AUTOCONTROL = True
    _active_profile = {"pump": 0, "fan": 0}

    """ Unimplemented or unsupported features """

    def set_color(self, channel, mode, colors, **kwargs):
        raise NotSupportedByDriver()

    def set_screen(self, channel, mode, value, **kwargs):
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        raise NotSupportedByDevice()

    def _hanbo_hid_read_validate_report(self, signature):
        """For a received packet, validate the format before
        returning. As there could be multiple users of the AIO
        (e.g. ARGB) we could be receiving a report triggered by
        someone else. In such case we ignore it and wait until
        the reply to our request is seen. This is limited to
        _MAX_READ_RETRIES as there shouldn't many concurrent
        users and the HidapiDevice class manages timeouts on
        the bus.
        """

        # Generate the expected header
        header = bytearray(signature[1:])

        i = 0
        array = [[] for _ in range(_MAX_READ_RETRIES)]

        while i < _MAX_READ_RETRIES:
            array[i] = self._read()
            if array[i] != None and header == array[i][0 : len(header)]:
                if reduce(lambda a, b: a + b, array[i][signature[0] :]) == 0:
                    return array[i]
            i += 1
        raise ValueError(
            f"Unable to catch report, expected type {signature[1:]}. Packet dump {array}"
        )

    def initialize(self, direct_access=False, **kwargs):
        """Initialize the device and the driver.
        The Hanbo does not require initialization but we do some housekeeping
        * If hwmon does not exist, set the default CPU reference temperature
        * Print the firmware and serial number
        """
        self._write(_RazerHanboCommands.get_firmware.header)
        array = self._hanbo_hid_read_validate_report(_RazerHanboReplies.firmware)

        if not self._hwmon:
            self.set_hardware_status(list(_HWMON_CTRL_MAPPING)[1], _DEFAULT_CPU_TEMP_DEGREES_C)
            self._hanbo_hid_read_validate_report(_RazerHanboReplies.ref_temp)

        firmware_version = "V{}.{}.{}".format(array[29], array[30] >> 4 & 0x0F, array[30] & 0x0F)

        return [
            ("Serial number", (array[2:17]).decode("utf-8"), ""),
            ("Firmware version", firmware_version, ""),
        ]

    def _get_status_directly(self):

        self._write(_RazerHanboCommands.get_pump_status.header)
        array = self._hanbo_hid_read_validate_report(_RazerHanboReplies.pump_status)
        if array == None:
            _LOGGER.warning(
                "No matching pump reports after requesting them "
                "Something is spamming the interface or there's a failure"
            )
        status_readings = [
            (_STATUS_TEMPERATURE, array[5] + (array[6] / 10), "°C"),
            (_STATUS_PUMP_SPEED, u16be_from(array, offset=7), "rpm"),
            (_STATUS_PUMP_DUTY, array[10], "%"),
            (
                _STATUS_PUMP_PROFILE,
                (
                    list(_PROFILE_MAPPING)[array[3] - 1]
                    if self._active_profile["pump"] != "custom"
                    else "custom"
                ),
                "",
            ),
        ]

        # Status is acquired from two commands, the pump and fan respectively.
        self._write(_RazerHanboCommands.get_fan_status.header)
        array = self._hanbo_hid_read_validate_report(_RazerHanboReplies.fan_status)

        if array == None:
            _LOGGER.warning(
                "No matching fan reports after requesting them"
                "Something is spamming the interface or there's a failure"
            )
        status_readings.append((_STATUS_FAN_SPEED, u16be_from(array, offset=6), "rpm"))
        status_readings.append((_STATUS_FAN_DUTY, array[9], "%"))
        status_readings.append(
            (
                _STATUS_FAN_PROFILE,
                (
                    list(_PROFILE_MAPPING)[array[4] - 1]
                    if self._active_profile["fan"] != "custom"
                    else "custom"
                ),
                "",
            )
        )
        return status_readings

    def _get_status_from_hwmon(self):
        status_readings = [
            (_STATUS_TEMPERATURE, round(self._hwmon.read_int("temp1_input") * 1e-3, 1), "°C"),
            (_STATUS_PUMP_SPEED, self._hwmon.read_int("fan1_input"), "rpm"),
            (_STATUS_PUMP_DUTY, self._hwmon.read_int("pwm1"), "%"),
            (
                _STATUS_PUMP_PROFILE,
                list(_PROFILE_MAPPING)[self._hwmon.read_int("pwm1_enable") - 1],
                "",
            ),
            (_STATUS_FAN_SPEED, self._hwmon.read_int("fan2_input"), "rpm"),
            (_STATUS_FAN_DUTY, self._hwmon.read_int("pwm2"), "%"),
            (
                _STATUS_FAN_PROFILE,
                list(_PROFILE_MAPPING)[self._hwmon.read_int("pwm2_enable") - 1],
                "",
            ),
        ]

        """ PWM readings from hwmon are approximate due to lm-sensor scaling.
        This is not the case when reading the values directly.
        """
        return status_readings

    def get_status(self, direct_access=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        if self._hwmon and not direct_access:
            _LOGGER.info("bound to %s kernel driver, reading status from hwmon", self._hwmon.driver)
            return self._get_status_from_hwmon()

        else:
            if self._hwmon:
                _LOGGER.warning(
                    "directly reading the status despite %s kernel driver", self._hwmon.driver
                )
            return self._get_status_directly()

    def set_hardware_status(self, channels, T, direct_access=True, **kwargs):
        if channels != list(_HWMON_CTRL_MAPPING)[1]:
            _LOGGER.info(f"{channels} is invalid for this operation")
            raise ValueError(f"{channels} is invalid for this operation")

        if type(T) == list:
            T = T[0]

        if self._hwmon and not direct_access:
            _LOGGER.info(
                "bound to %s kernel driver, writing reference temp to hwmon", self._hwmon.driver
            )
            self._hwmon.write_int(f"temp2_input", clamp(int(T), 0, 100) * 1000)

        else:
            if self._hwmon:
                _LOGGER.warning(
                    "directly writing reference temp despite %s kernel driver", self._hwmon.driver
                )
            header = _RazerHanboCommands.set_ref_temp.header
            """ The last 3 bytes presumably relate to an unused GPU temp monitoring function.
            A fixed temperature of 30 degrees C is provided with every update.
            """
            self._write(header + (clamp(int(T), 0, 100), 0x00, 0x1E, 0x00))

    def set_profiles(self, channels, profiles, direct_access=True, **kwargs):
        """
        Set custom or device preset fan curve for multiple channels.

        NOTE: Fan curves require setting and updating a reference
        temperature via device.set_cpu_status() to function.
        Pump curves are autonomous.
        """
        args = ((channels, profiles),)
        if isinstance(channels, tuple) and isinstance(profiles, tuple):
            if len(channels) == len(profiles):
                args = zip(channels, profiles)
            else:
                _LOGGER.warning("Unbalanced channel/profile arguments")
                return
        for ch, prof in args:
            if (
                ch in self._custom_profiles and prof in _PROFILE_MAPPING
            ):  # Which happens to have all channels, so a good sanity checker
                # First, switch between hwmon or direct modes
                if self._hwmon and not direct_access:
                    _LOGGER.info(
                        "bound to %s kernel driver, setting profiles from hwmon", self._hwmon.driver
                    )
                    # Do hwmon routines here
                    if _PROFILE_MAPPING[prof][0] == _CUSTOM_PROFILE_ID:
                        hwmon_tempate = "temp{}_auto_point{}_pwm"
                        for index, point in enumerate(self._custom_profiles[ch]):
                            self._hwmon.write_int(
                                hwmon_tempate.format(_HWMON_CTRL_MAPPING[ch], index + 1), point
                            )
                        self._hwmon.write_int(
                            f"pwm{_HWMON_CTRL_MAPPING[ch]}_enable", _PROFILE_MAPPING[prof][0]
                        )
                        self._active_profile[ch] = prof
                else:
                    if self._hwmon:
                        _LOGGER.warning(
                            "directly setting profiles despite %s kernel driver",
                            self._hwmon.driver,
                        )
                    if _PROFILE_MAPPING[prof][0] == _CUSTOM_PROFILE_ID:
                        command = getattr(_RazerHanboCommands, f"set_{ch}_curve").header
                        command += tuple(self._custom_profiles[ch])
                        self._active_profile[ch] = prof
                    else:
                        command = getattr(_RazerHanboCommands, f"set_{ch}_profile").header
                        command += _PROFILE_MAPPING[prof]
                        self._active_profile[ch] = prof
                    self._write(command)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Sets and sanity checks a curve profile. It does not
        upload it to the AIO, that happens using set_profiles().
        """
        profile = list(profile)
        if channel in self._custom_profiles:
            if len(profile) == _MAX_DUTIES * 2:
                new_curve = profile[1::2]  # Ignore temperatures as hardware does not use them.
                new_curve = sorted(new_curve)
                if (
                    min(new_curve) >= _MINIMUM_THERMAL_UNIT
                    and max(new_curve) == _MAXIMUM_THERMAL_UNIT
                ):
                    self._custom_profiles[channel] = new_curve
                else:
                    _LOGGER.warning(
                        "Curve is not monotonically increasing or has"
                        "values outside valid range of 20-100 duty. Not applying"
                    )

    @staticmethod
    def _make_buffer(array, fill=0, total_size=_REPORT_LENGTH):
        return bytearray(list(array) + ((total_size - (len(array) + 1)) * [fill]))

    def _write(self, array, fill=0, total_size=_REPORT_LENGTH):
        self.device.clear_enqueued_reports()
        return self.device.write(self._make_buffer(array, fill, total_size))

    def _read(self, size=_REPORT_LENGTH):
        try:
            return bytearray(self.device.read(size))
        except:
            _LOGGER.info("USB timeout occurred")
            return None
