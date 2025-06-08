# uses the psf/black style

from struct import pack, unpack
from math import modf
from functools import reduce

import pytest
import os
import re
import random

from _testutils import MockHidapiDevice, Report
from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.razer_hanbo import (
    RazerHanbo,
    _RazerHanboCommands,
    _RazerHanboReplies,
    _REPORT_LENGTH,
    _FW_COMMAND,
    _PROFILE_MAPPING,
    _MAXIMUM_THERMAL_UNIT,
    _DEFAULT_CPU_TEMP_DEGREES_C,
    _PROFILE_MAPPING,
)
from liquidctl.driver.usb import _DEFAULT_TIMEOUT_MS

_FIRMWARE_RESPONSE_PAYLOAD = bytes.fromhex(
    "313233343536373839414243444546" "000000000000000000800001012000" "0210"
)


@pytest.fixture
def razerHanboChromaDevice():

    description = "Mock Razer Hanbo Chroma"
    device = _MockHanbo(vendor_id=0x1532, product_id=0x0F35)
    dev = RazerHanbo(device, description)

    dev.connect()
    return dev


class _MockHanbo(MockHidapiDevice):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._active_pump_profile = bytearray([_PROFILE_MAPPING["balanced"][0]])
        self._active_fan_profile = bytearray([_PROFILE_MAPPING["balanced"][0]])
        self._fan_rpm = pack(">h", random.randint(200, 2000))
        self._fan_duty = bytearray([random.randint(0, 100)])
        self._pump_rpm = pack(">h", random.randint(200, 1000))
        self._pump_duty = bytearray([random.randint(0, 100)])
        self._liquid_temp = list(modf(round(random.uniform(20, 60), 1))[::-1])
        self._packet_reply = None
        self._prev_packet_reply = None
        self._cpu_temp = None
        self._cmd_report_id = {}
        self._validate_buffer = []

        # Generate command lookup table
        for var in filter(lambda a: a[0] != "_", dir(_RazerHanboCommands)):
            self._cmd_report_id[(getattr(_RazerHanboCommands, var).header[0])] = {
                var: (getattr(_RazerHanboCommands, var).has_payload)
            }

        # Convert temperature into hex form per firmware
        self._liquid_temp[1] *= 10
        self._liquid_temp = bytearray([round(item) for item in self._liquid_temp])
        self._liquid_temp_val = int(self._liquid_temp[0]) + int(self._liquid_temp[1]) / 10

    def read(self, length, *, timeout=_DEFAULT_TIMEOUT_MS):
        assert self._packet_reply != None
        reply = bytearray(list(getattr(_RazerHanboReplies, self._packet_reply)[1:]))
        if self._packet_reply == "pump_status":
            reply += (
                self._active_pump_profile
                + self._active_pump_profile
                + self._liquid_temp
                + self._pump_rpm
                + self._pump_duty
                + self._pump_duty
            )
        if self._packet_reply == "firmware":
            reply += bytearray(_FIRMWARE_RESPONSE_PAYLOAD)
        if self._packet_reply == "fan_status":
            reply += (
                self._active_fan_profile
                + self._active_fan_profile
                + self._fan_rpm
                + self._fan_duty
                + self._fan_duty
            )

        reply = bytearray(list(reply) + ((_REPORT_LENGTH - (len(reply) + 1)) * [0]))
        return reply

    def write(self, data):
        assert data[0] in self._cmd_report_id
        var = next(iter(self._cmd_report_id[data[0]].keys()))
        if next(iter(self._cmd_report_id[data[0]].values())):
            self._prev_packet_reply = self._packet_reply
            if var == "set_pump_profile":
                self._validate_buffer = [data[2], data[3]]
                self._active_pump_profile = bytearray([data[2]])

            elif var == "set_pump_curve":
                if self._prev_packet_reply == "fan_curve":
                    self._validate_buffer += data[4:13]
                else:
                    self._validate_buffer = data[4:13]

            elif var == "set_fan_profile":
                self._validate_buffer = [data[2], data[3]]
                self._active_fan_profile = bytearray([data[2]])

            elif var == "set_ref_temp":
                self._validate_buffer = int(data[2])
                assert self._validate_buffer >= 0
                assert self._validate_buffer <= 100
                assert data[3] == 0
                assert int(data[4]) >= 0
                assert int(data[4]) <= 100
                assert data[5] == 0
                self._cpu_temp = self._validate_buffer

            elif var == "set_fan_curve":
                if self._prev_packet_reply == "pump_curve":
                    self._validate_buffer += data[4:13]
                else:
                    self._validate_buffer = data[4:13]

        elif data[1] == 0x01:
            assert reduce(lambda a, b: a + b, data[2:]) == 0

        self._packet_reply = re.sub("^[^_]*_", "", var)

    def create_sysfs_status_nodes(self, tmp_path):
        (tmp_path / "temp1_input").write_text(str(int(self._liquid_temp_val * 1000)) + "\n")
        (tmp_path / "fan1_input").write_text(str(list(unpack(">h", self._pump_rpm))[0]) + "\n")
        (tmp_path / "pwm1").write_text(str(int.from_bytes(self._pump_duty, byteorder="big")) + "\n")
        (tmp_path / "pwm1_enable").write_text(
            str(int.from_bytes(self._active_pump_profile, byteorder="big")) + "\n"
        )
        (tmp_path / "fan2_input").write_text(str(list(unpack(">h", self._fan_rpm))[0]) + "\n")
        (tmp_path / "pwm2").write_text(str(int.from_bytes(self._fan_duty, byteorder="big")) + "\n")
        (tmp_path / "pwm2_enable").write_text(
            str(int.from_bytes(self._active_fan_profile, byteorder="big")) + "\n"
        )


""" Fetch a status report
Check for correctness
"""


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True), (True, False)])
def test_razerhanbo_get_status(razerHanboChromaDevice, has_hwmon, direct_access, tmp_path):
    if has_hwmon:
        razerHanboChromaDevice._hwmon = HwmonDevice("mock_module", tmp_path)
        razerHanboChromaDevice.device.create_sysfs_status_nodes(tmp_path)

        temperature, pump_speed, pump_duty, pump_profile, fan_speed, fan_duty, fan_profile = (
            razerHanboChromaDevice.get_status(direct_access)
        )
    if not (has_hwmon == False and direct_access == False):
        assert temperature == (
            "Liquid temperature",
            razerHanboChromaDevice.device._liquid_temp_val,
            "°C",
        )
        assert pump_speed == (
            "Pump speed",
            list(unpack(">h", razerHanboChromaDevice.device._pump_rpm))[0],
            "rpm",
        )
        assert pump_duty == (
            "Pump duty",
            int.from_bytes(razerHanboChromaDevice.device._pump_duty, byteorder="big"),
            "%",
        )
        assert pump_profile == (
            "Pump profile",
            list(_PROFILE_MAPPING.keys())[
                int.from_bytes(razerHanboChromaDevice.device._active_pump_profile, byteorder="big")
                - 1
            ],
            "",
        )
        assert fan_speed == (
            "Fan speed",
            list(unpack(">h", razerHanboChromaDevice.device._fan_rpm))[0],
            "rpm",
        )
        assert fan_duty == (
            "Fan duty",
            int.from_bytes(razerHanboChromaDevice.device._fan_duty, byteorder="big"),
            "%",
        )
        assert fan_profile == (
            "Fan profile",
            list(_PROFILE_MAPPING.keys())[
                int.from_bytes(razerHanboChromaDevice.device._active_fan_profile, byteorder="big")
                - 1
            ],
            "",
        )


""" Set the CPU reference temperature
Check no out of bounds values are written
Ensure that only a "fan" type profile can issue this command.
"""


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True), (True, False)])
def test_razerhanbo_set_hardware_status(razerHanboChromaDevice, has_hwmon, direct_access, tmp_path):
    if has_hwmon:
        razerHanboChromaDevice._hwmon = HwmonDevice("mock_module", tmp_path)
        (tmp_path / "temp2_input").write_text("0")

    testval = 40

    razerHanboChromaDevice.set_hardware_status("fan", testval, direct_access)

    if not direct_access and has_hwmon:
        assert (tmp_path / "temp2_input").read_text() == str(testval * 1000)

    if direct_access:
        assert razerHanboChromaDevice.device._cpu_temp == testval

    testval = -5

    razerHanboChromaDevice.set_hardware_status("fan", testval, direct_access)

    if not direct_access and has_hwmon:
        assert (tmp_path / "temp2_input").read_text() == str(0)

    if direct_access:
        assert razerHanboChromaDevice.device._cpu_temp == 0

    testval = 7465144

    razerHanboChromaDevice.set_hardware_status("fan", testval, direct_access)

    if not direct_access and has_hwmon:
        assert (tmp_path / "temp2_input").read_text() == str((_MAXIMUM_THERMAL_UNIT * 1000))

    if direct_access:
        assert razerHanboChromaDevice.device._cpu_temp == _MAXIMUM_THERMAL_UNIT

    testval = [36]

    razerHanboChromaDevice.set_hardware_status("fan", testval, direct_access)

    if not direct_access and has_hwmon:
        assert (tmp_path / "temp2_input").read_text() == str((testval[0] * 1000))

    if direct_access:
        assert razerHanboChromaDevice.device._cpu_temp == testval[0]

    with pytest.raises(ValueError):
        razerHanboChromaDevice.set_hardware_status("pump", testval, direct_access)


""" Apply a set profile to the driver
Check for packet correctness and that a status report reflects this.

"""


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True), (True, False)])
def test_razerhanbo_set_profiles(razerHanboChromaDevice, has_hwmon, direct_access, tmp_path):
    if has_hwmon:
        razerHanboChromaDevice._hwmon = HwmonDevice("mock_module", tmp_path)
        razerHanboChromaDevice.device.create_sysfs_status_nodes(tmp_path)

    channels = ("fan", "pump")
    profiles = ("quiet", "extreme")
    razerHanboChromaDevice.set_profiles(channels, profiles, direct_access)

    if has_hwmon:
        # Python driver doesn't update sysfs, do that manually
        razerHanboChromaDevice.device._active_pump_profile = bytearray(
            [_PROFILE_MAPPING["extreme"][0]]
        )
        razerHanboChromaDevice.device._active_fan_profile = bytearray(
            [_PROFILE_MAPPING["quiet"][0]]
        )
        razerHanboChromaDevice.device.create_sysfs_status_nodes(tmp_path)

    temperature, pump_speed, pump_duty, pump_profile, fan_speed, fan_duty, fan_profile = (
        razerHanboChromaDevice.get_status(direct_access)
    )
    assert pump_profile[1] == "extreme"
    assert fan_profile[1] == "quiet"

    channels = "fan"
    profiles = "balanced"
    razerHanboChromaDevice.set_profiles(channels, profiles, direct_access)

    if has_hwmon:
        # Python driver doesn't update sysfs, do that manually
        razerHanboChromaDevice.device._active_fan_profile = bytearray(
            [_PROFILE_MAPPING["balanced"][0]]
        )
        razerHanboChromaDevice.device.create_sysfs_status_nodes(tmp_path)

    temperature, pump_speed, pump_duty, pump_profile, fan_speed, fan_duty, fan_profile = (
        razerHanboChromaDevice.get_status(direct_access)
    )
    assert fan_profile[1] == "balanced"


""" Fetch firmware report
Validates that firmware & serial number are fetched and that the
CPU reference temperature has been set
"""


def test_razerhanbo_initialize(razerHanboChromaDevice):
    s_report, f_report = razerHanboChromaDevice.initialize()
    firmware_version = "V{}.{}.{}".format(
        _FIRMWARE_RESPONSE_PAYLOAD[27],
        _FIRMWARE_RESPONSE_PAYLOAD[28] >> 4 & 0x0F,
        _FIRMWARE_RESPONSE_PAYLOAD[28] & 0x0F,
    )
    assert s_report == ("Serial number", _FIRMWARE_RESPONSE_PAYLOAD[0:15].decode("utf-8"), "")
    assert f_report == ("Firmware version", firmware_version, "")
    assert razerHanboChromaDevice.device._cpu_temp == _DEFAULT_CPU_TEMP_DEGREES_C


""" Apply custom curves to the driver
Validates internal data structures only
"""


def test_razerhanbo_set_speed_profile(razerHanboChromaDevice):

    channel = "fan"
    profile = bytes.fromhex("0014001400200025002F0032004000500064")
    razerHanboChromaDevice.set_speed_profile(channel, profile)
    assert razerHanboChromaDevice._custom_profiles["fan"] == list(profile[1::2])
    channel = "pump"
    profile = bytes.fromhex("0014001800200025002F0064006400640064")
    razerHanboChromaDevice.set_speed_profile(channel, profile)
    assert razerHanboChromaDevice._custom_profiles["pump"] == list(profile[1::2])

    profile = bytes.fromhex("0030001800200025002F0064006400640064")
    razerHanboChromaDevice.set_speed_profile(channel, profile)
    assert razerHanboChromaDevice._custom_profiles["pump"] != list(profile[1::2])


""" Apply a custom curve and check that -
In the case of direct, that dissected protocol received the correct values.
In the case of hwmon, the correct sequence was written to mock sysfs
Check the status report reflects custom mode
"""


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True), (True, False)])
def test_razerhanbo_set_profiles_curve(razerHanboChromaDevice, has_hwmon, direct_access, tmp_path):
    if has_hwmon:
        razerHanboChromaDevice._hwmon = HwmonDevice("mock_module", tmp_path)

    channels = ("fan", "pump")
    profiles = ("custom", "custom")

    razerHanboChromaDevice.set_profiles(channels, profiles, direct_access)
    if has_hwmon:
        # Python driver doesn't update sysfs, do that manually
        razerHanboChromaDevice.device._active_pump_profile = bytearray(
            [_PROFILE_MAPPING["custom"][0]]
        )
        razerHanboChromaDevice.device._active_fan_profile = bytearray(
            [_PROFILE_MAPPING["custom"][0]]
        )
        razerHanboChromaDevice.device.create_sysfs_status_nodes(tmp_path)

    if direct_access:
        assert (
            list(razerHanboChromaDevice.device._validate_buffer)
            == razerHanboChromaDevice._custom_profiles["fan"]
            + razerHanboChromaDevice._custom_profiles["pump"]
        )

    if has_hwmon and not direct_access:
        hwmon_tempate = "temp{}_auto_point{}_pwm"
        sysfs_temp = []

        for index, i in enumerate(list(("pump", "fan"))):
            for point in range(1, 10):
                sysfs_temp.append(
                    int((tmp_path / hwmon_tempate.format(index + 1, point)).read_text())
                )
            assert sysfs_temp == razerHanboChromaDevice._custom_profiles[i]
            sysfs_temp = []

    temperature, pump_speed, pump_duty, pump_profile, fan_speed, fan_duty, fan_profile = (
        razerHanboChromaDevice.get_status(direct_access)
    )
    assert pump_profile[1] == "custom"
    assert fan_profile[1] == "custom"
