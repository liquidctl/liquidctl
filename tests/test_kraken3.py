# uses the psf/black style

import pytest
import os

from _testutils import MockHidapiDevice, MockPyusbDevice, Report

from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.kraken3 import KrakenX3, KrakenZ3
from liquidctl.driver.kraken3 import (
    _COLOR_CHANNELS_KRAKENX,
    _SPEED_CHANNELS_KRAKENX,
    _COLOR_CHANNELS_KRAKENZ,
    _SPEED_CHANNELS_KRAKENZ,
    _HWMON_CTRL_MAPPING_KRAKENX,
    _HWMON_CTRL_MAPPING_KRAKENZ,
)
from test_krakenz3_response import krakenz3_response

from liquidctl.util import HUE2_MAX_ACCESSORIES_IN_CHANNEL as MAX_ACCESSORIES
from liquidctl.util import Hue2Accessory


# https://github.com/liquidctl/liquidctl/issues/160#issuecomment-664044103
X3_SAMPLE_STATUS = bytes.fromhex(
    "7502200036000B51535834353320012101A80635350000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)
# https://github.com/liquidctl/liquidctl/issues/160#issue-665781804
X3_FAULTY_STATUS = bytes.fromhex(
    "7502200036000B5153583435332001FFFFCC0A64640000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)

Z3_SAMPLE_STATUS = bytes.fromhex(
    "75012E0018001051393434363731011803690314140102000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)

test_curve_final_pwm = [
    30,
    32,
    34,
    36,
    38,
    40,
    42,
    44,
    46,
    48,
    50,
    58,
    65,
    72,
    80,
    82,
    83,
    85,
    87,
    88,
    90,
    91,
    92,
    93,
    94,
    95,
    96,
    97,
    98,
    99,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
]


@pytest.fixture
def mock_krakenx3():
    raw = MockKraken(raw_led_channels=len(_COLOR_CHANNELS_KRAKENX) - 1)
    dev = KrakenX3(
        raw,
        "Mock Kraken X73",
        speed_channels=_SPEED_CHANNELS_KRAKENX,
        color_channels=_COLOR_CHANNELS_KRAKENX,
        hwmon_ctrl_mapping=_HWMON_CTRL_MAPPING_KRAKENX,
    )

    dev.connect()
    return dev


@pytest.fixture
def mock_krakenz3():
    raw = MockKraken(raw_led_channels=1)
    dev = MockKrakenZ3(
        raw,
        "Mock Kraken Z73",
        speed_channels=_SPEED_CHANNELS_KRAKENZ,
        color_channels=_COLOR_CHANNELS_KRAKENZ,
        hwmon_ctrl_mapping=_HWMON_CTRL_MAPPING_KRAKENZ,
    )

    dev.connect()
    return dev


class MockKraken(MockHidapiDevice):
    def __init__(self, raw_led_channels):
        super().__init__()
        self.raw_led_channels = raw_led_channels

    def write(self, data):
        reply = bytearray(64)
        if data[0:2] == [0x10, 0x01]:
            reply[0:2] = [0x11, 0x01]
        elif data[0:2] == [0x20, 0x03]:
            reply[0:2] = [0x21, 0x03]
            reply[14] = self.raw_led_channels
            if self.raw_led_channels > 1:
                reply[15 + 1 * MAX_ACCESSORIES] = Hue2Accessory.KRAKENX_GEN4_RING.value
                reply[15 + 2 * MAX_ACCESSORIES] = Hue2Accessory.KRAKENX_GEN4_LOGO.value
        elif data[0:2] == [0x30, 0x01]:
            reply[0:2] = [0x31, 0x01]
            reply[0x18] = 50  # lcd brightness
            reply[0x1A] = 0  # lcd orientation
        elif data[0:2] == [0x32, 0x1]:  # setup bucket
            reply[14] = 0x1
        elif data[0:2] == [0x32, 0x2]:  # delete bucker
            reply[0:2] = [0x33, 0x02]
            reply[14] = 0x1
        elif data[0:2] == [0x38, 0x1]:  # switch bucket
            reply[14] = 0x1

        self.preload_read(Report(0, reply))
        return super().write(data)


class MockKrakenZ3(KrakenZ3):
    def __init__(self, device, description, speed_channels, color_channels, **kwargs):
        KrakenX3.__init__(self, device, description, speed_channels, color_channels, **kwargs)

        self.bulk_device = MockPyusbDevice(0x1E71, 0x3008)
        self.bulk_device.close_winusb_device = self.bulk_device.release

        self.orientation = 0
        self.brightness = 50

        self.screen_mode = None

    def set_screen(self, channel, mode, value, **kwargs):
        self.screen_mode = mode
        self.hid_data_index = 0
        self.bulk_data_index = 0

        super().set_screen(channel, mode, value, **kwargs)

        assert self.hid_data_index == len(
            krakenz3_response[self.screen_mode + "_hid"]
        ), f"Incorrect number of hid messages sent for mode: {mode}"

        if mode == "static" or mode == "gif":
            assert (
                self.bulk_data_index == 801
                if mode == "static"
                else len(krakenz3_response[self.screen_mode + "_bulk"])
            ), f"Incorrect number of bulk messages sent for mode: {mode}"

    def _write(self, data):
        if self.screen_mode:
            assert (
                data == krakenz3_response[self.screen_mode + "_hid"][self.hid_data_index]
            ), f"HID write failed, wrong data for mode: {self.screen_mode}, data index: {self.hid_data_index}"
            self.hid_data_index += 1
        return super()._write(data)

    def _bulk_write(self, data):
        fixed_data_index = self.bulk_data_index
        if (
            self.screen_mode == "static" and self.bulk_data_index > 1
        ):  # the rest of the message should be identical to index 1
            fixed_data_index = 1

        assert (
            data == krakenz3_response[self.screen_mode + "_bulk"][fixed_data_index]
        ), f"Bulk write failed, wrong data for mode: {self.screen_mode}, data index: {self.bulk_data_index}"
        self.bulk_data_index += 1
        return super()._bulk_write(data)


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True), (True, False)])
def test_krakenx3_initializes(mock_krakenx3, has_hwmon, direct_access, tmp_path):
    if has_hwmon:
        mock_krakenx3._hwmon = HwmonDevice("mock_module", tmp_path)

    # TODO check the result
    _ = mock_krakenx3.initialize(direct_access=direct_access)

    writes = len(mock_krakenx3.device.sent)
    if not has_hwmon or direct_access:
        assert writes == 4
    else:
        assert writes == 2


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_krakenx3_reads_status_directly(mock_krakenx3, has_hwmon, direct_access):
    if has_hwmon:
        mock_krakenx3._hwmon = HwmonDevice(None, None)

    mock_krakenx3.device.preload_read(Report(0, X3_SAMPLE_STATUS))

    temperature, pump_speed, pump_duty = mock_krakenx3.get_status(direct_access=direct_access)

    assert temperature == ("Liquid temperature", 33.1, "°C")
    assert pump_speed == ("Pump speed", 1704, "rpm")
    assert pump_duty == ("Pump duty", 53, "%")


def test_krakenx3_reads_status_from_hwmon(mock_krakenx3, tmp_path):
    mock_krakenx3._hwmon = HwmonDevice("mock_module", tmp_path)
    (tmp_path / "temp1_input").write_text("33100\n")
    (tmp_path / "fan1_input").write_text("1704\n")
    (tmp_path / "pwm1").write_text("135\n")

    temperature, pump_speed, pump_duty = mock_krakenx3.get_status()

    assert temperature == ("Liquid temperature", 33.1, "°C")
    assert pump_speed == ("Pump speed", 1704, "rpm")
    assert pump_duty == ("Pump duty", pytest.approx(53, rel=1.0 / 255), "%")


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_krakenx3_set_fixed_speeds_directly(mock_krakenx3, has_hwmon, direct_access, tmp_path):
    """For both test cases only direct access should be used"""

    if has_hwmon:
        mock_krakenx3._hwmon = HwmonDevice("mock_module", tmp_path)
        (tmp_path / "pwm1").write_text("0")
        (tmp_path / "pwm1_enable").write_text("0")

    mock_krakenx3.set_fixed_speed("pump", 84, direct_access=direct_access)

    pump_report = mock_krakenx3.device.sent[0]

    assert pump_report.number == 0x72
    assert pump_report.data[3:43] == [84 for i in range(0, 39)] + [100]

    # Assert that hwmon wasn't touched
    if has_hwmon:
        assert (tmp_path / "pwm1_enable").read_text() == "0"
        assert (tmp_path / "pwm1").read_text() == "0"


@pytest.mark.parametrize("has_support", [False, True])
def test_krakenx3_set_fixed_speeds_hwmon(mock_krakenx3, has_support, tmp_path):
    mock_krakenx3._hwmon = HwmonDevice("mock_module", tmp_path)

    if has_support:
        (tmp_path / "pwm1").write_text("0\n")
        (tmp_path / "pwm1_enable").write_text("0\n")

    mock_krakenx3.set_fixed_speed("pump", 84)

    if has_support:
        assert (tmp_path / "pwm1_enable").read_text() == "1"
        assert (tmp_path / "pwm1").read_text() == "214"
    else:
        # Assert fallback to direct access
        pump_report = mock_krakenx3.device.sent[0]

        assert pump_report.number == 0x72
        assert pump_report.data[3:43] == [84 for i in range(0, 39)] + [100]


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_krakenx3_set_speed_profile_directly(mock_krakenx3, has_hwmon, direct_access, tmp_path):
    """For both test cases only direct access should be used"""

    if has_hwmon:
        mock_krakenx3._hwmon = HwmonDevice("mock_module", tmp_path)
        (tmp_path / "pwm1").write_text("0")
        (tmp_path / "pwm1_enable").write_text("0")
        for i in range(1, 40 + 1):
            (tmp_path / f"temp1_auto_point{i}_pwm").write_text("0")

    curve_profile = zip([20, 30, 34, 40, 50], [30, 50, 80, 90, 100])

    mock_krakenx3.set_speed_profile("pump", curve_profile, direct_access=direct_access)

    pump_report = mock_krakenx3.device.sent[0]

    assert pump_report.number == 0x72
    assert pump_report.data[3:43] == test_curve_final_pwm

    # Assert that hwmon wasn't touched
    if has_hwmon:
        assert (tmp_path / "pwm1_enable").read_text() == "0"
        assert (tmp_path / "pwm1").read_text() == "0"
        for i in range(1, 40):
            assert (tmp_path / f"temp1_auto_point{i}_pwm").read_text() == "0"


@pytest.mark.parametrize("has_support", [False, True])
def test_krakenx3_set_speed_profile_hwmon(mock_krakenx3, has_support, tmp_path):
    mock_krakenx3._hwmon = HwmonDevice("mock_module", tmp_path)

    if has_support:
        (tmp_path / "pwm1_enable").write_text("0\n")
        for i in range(1, 40 + 1):
            (tmp_path / f"temp1_auto_point{i}_pwm").write_text("0")

    curve_profile = zip([20, 30, 34, 40, 50], [30, 50, 80, 90, 100])

    mock_krakenx3.set_speed_profile("pump", curve_profile)

    if has_support:
        assert (tmp_path / "pwm1_enable").read_text() == "2"
        for i in range(1, 40 + 1):
            assert int((tmp_path / f"temp1_auto_point{i}_pwm").read_text()) == (
                test_curve_final_pwm[i - 1] * 255 // 100
            )
    else:
        # Assert fallback to direct access
        pump_report = mock_krakenx3.device.sent[0]

        assert pump_report.number == 0x72
        assert pump_report.data[3:43] == test_curve_final_pwm


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_krakenx3_warns_on_faulty_temperature(mock_krakenx3, has_hwmon, direct_access, caplog):
    if has_hwmon:
        mock_krakenx3._hwmon = HwmonDevice(None, None)

    mock_krakenx3.device.preload_read(Report(0, X3_FAULTY_STATUS))

    _ = mock_krakenx3.get_status(direct_access=direct_access)
    assert "unexpected temperature reading" in caplog.text


def test_krakenx3_not_totally_broken(mock_krakenx3):
    """Reasonable example calls to untested APIs do not raise exceptions."""
    mock_krakenx3.initialize()
    mock_krakenx3.set_color(channel="ring", mode="fixed", colors=iter([[3, 2, 1]]), speed="fastest")
    mock_krakenx3.set_speed_profile(channel="pump", profile=iter([(20, 20), (30, 50), (40, 100)]))
    mock_krakenx3.set_fixed_speed(channel="pump", duty=50)


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_krakenz3_reads_status_directly(mock_krakenz3, has_hwmon, direct_access):
    if has_hwmon:
        mock_krakenz3._hwmon = HwmonDevice(None, None)

    mock_krakenz3.device.preload_read(Report(0, Z3_SAMPLE_STATUS))

    temperature, pump_speed, pump_duty, fan_speed, fan_duty = mock_krakenz3.get_status(
        direct_access=direct_access
    )

    assert temperature == ("Liquid temperature", 24.3, "°C")
    assert pump_speed == ("Pump speed", 873, "rpm")
    assert pump_duty == ("Pump duty", 20, "%")
    assert fan_speed == ("Fan speed", 0, "rpm")
    assert fan_duty == ("Fan duty", 0, "%")


def test_krakenz3_reads_status_from_hwmon(mock_krakenz3, tmp_path):
    mock_krakenz3._hwmon = HwmonDevice("mock_module", tmp_path)
    (tmp_path / "temp1_input").write_text("33100\n")
    (tmp_path / "fan1_input").write_text("1704\n")
    (tmp_path / "pwm1").write_text("135\n")
    (tmp_path / "fan2_input").write_text("1704\n")
    (tmp_path / "pwm2").write_text("135\n")

    temperature, pump_speed, pump_duty, fan_speed, fan_duty = mock_krakenz3.get_status()

    assert temperature == ("Liquid temperature", 33.1, "°C")
    assert pump_speed == ("Pump speed", 1704, "rpm")
    assert pump_duty == ("Pump duty", pytest.approx(53, rel=1.0 / 255), "%")
    assert fan_speed == ("Fan speed", 1704, "rpm")
    assert fan_duty == ("Fan duty", pytest.approx(53, rel=1.0 / 255), "%")


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_krakenz3_set_fixed_speeds_directly(mock_krakenz3, has_hwmon, direct_access, tmp_path):
    """For both test cases only direct access should be used"""

    if has_hwmon:
        mock_krakenz3._hwmon = HwmonDevice("mock_module", tmp_path)
        (tmp_path / "pwm1").write_text("0")
        (tmp_path / "pwm1_enable").write_text("0")
        (tmp_path / "pwm2").write_text("0")
        (tmp_path / "pwm2_enable").write_text("0")

    mock_krakenz3.set_fixed_speed("pump", 84, direct_access=direct_access)
    mock_krakenz3.set_fixed_speed("fan", 50, direct_access=direct_access)

    pump_report, fan_report = mock_krakenz3.device.sent

    assert pump_report.number == 0x72
    assert pump_report.data[3:43] == [84 for i in range(0, 39)] + [100]
    assert fan_report.number == 0x72
    assert fan_report.data[3:43] == [50 for i in range(0, 39)] + [100]

    # Assert that hwmon wasn't touched
    if has_hwmon:
        assert (tmp_path / "pwm1_enable").read_text() == "0"
        assert (tmp_path / "pwm1").read_text() == "0"
        assert (tmp_path / "pwm2_enable").read_text() == "0"
        assert (tmp_path / "pwm2").read_text() == "0"


@pytest.mark.parametrize("has_support", [False, True])
def test_krakenz3_set_fixed_speeds_hwmon(mock_krakenz3, has_support, tmp_path):
    mock_krakenz3._hwmon = HwmonDevice("mock_module", tmp_path)

    if has_support:
        (tmp_path / "pwm1").write_text("0\n")
        (tmp_path / "pwm1_enable").write_text("0\n")
        (tmp_path / "pwm2").write_text("0\n")
        (tmp_path / "pwm2_enable").write_text("0\n")

    mock_krakenz3.set_fixed_speed("pump", 84)
    mock_krakenz3.set_fixed_speed("fan", 50)

    if has_support:
        assert (tmp_path / "pwm1_enable").read_text() == "1"
        assert (tmp_path / "pwm1").read_text() == "214"
        assert (tmp_path / "pwm2_enable").read_text() == "1"
        assert (tmp_path / "pwm2").read_text() == "127"
    else:
        # Assert fallback to direct access
        pump_report, fan_report = mock_krakenz3.device.sent

        assert pump_report.number == 0x72
        assert pump_report.data[3:43] == [84 for i in range(0, 39)] + [100]
        assert fan_report.number == 0x72
        assert fan_report.data[3:43] == [50 for i in range(0, 39)] + [100]


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_krakenz3_set_speed_profile_directly(mock_krakenz3, has_hwmon, direct_access, tmp_path):
    """For both test cases only direct access should be used"""

    if has_hwmon:
        mock_krakenz3._hwmon = HwmonDevice("mock_module", tmp_path)
        (tmp_path / "pwm1").write_text("0")
        (tmp_path / "pwm1_enable").write_text("0")
        (tmp_path / "pwm2").write_text("0")
        (tmp_path / "pwm2_enable").write_text("0")
        for i in range(1, 40 + 1):
            (tmp_path / f"temp1_auto_point{i}_pwm").write_text("0")
            (tmp_path / f"temp2_auto_point{i}_pwm").write_text("0")

    mock_krakenz3.set_speed_profile(
        "pump", zip([20, 30, 34, 40, 50], [30, 50, 80, 90, 100]), direct_access=direct_access
    )
    mock_krakenz3.set_speed_profile(
        "fan", zip([20, 30, 34, 40, 50], [30, 50, 80, 90, 100]), direct_access=direct_access
    )

    pump_report, fan_report = mock_krakenz3.device.sent

    assert pump_report.number == 0x72
    assert pump_report.data[3:43] == test_curve_final_pwm
    assert fan_report.number == 0x72
    assert fan_report.data[3:43] == test_curve_final_pwm

    # Assert that hwmon wasn't touched
    if has_hwmon:
        assert (tmp_path / "pwm1_enable").read_text() == "0"
        assert (tmp_path / "pwm1").read_text() == "0"
        assert (tmp_path / "pwm2_enable").read_text() == "0"
        assert (tmp_path / "pwm2").read_text() == "0"
        for i in range(1, 40):
            assert (tmp_path / f"temp1_auto_point{i}_pwm").read_text() == "0"
            assert (tmp_path / f"temp2_auto_point{i}_pwm").read_text() == "0"


@pytest.mark.parametrize("has_support", [False, True])
def test_krakenz3_set_speed_profile_hwmon(mock_krakenz3, has_support, tmp_path):
    mock_krakenz3._hwmon = HwmonDevice("mock_module", tmp_path)

    if has_support:
        (tmp_path / "pwm1_enable").write_text("0\n")
        (tmp_path / "pwm2_enable").write_text("0\n")
        for i in range(1, 40 + 1):
            (tmp_path / f"temp1_auto_point{i}_pwm").write_text("0")
            (tmp_path / f"temp2_auto_point{i}_pwm").write_text("0")

    mock_krakenz3.set_speed_profile("pump", zip([20, 30, 34, 40, 50], [30, 50, 80, 90, 100]))
    mock_krakenz3.set_speed_profile("fan", zip([20, 30, 34, 40, 50], [30, 50, 80, 90, 100]))

    if has_support:
        assert (tmp_path / "pwm1_enable").read_text() == "2"
        for i in range(1, 40 + 1):
            assert int((tmp_path / f"temp1_auto_point{i}_pwm").read_text()) == (
                test_curve_final_pwm[i - 1] * 255 // 100
            )
            assert int((tmp_path / f"temp2_auto_point{i}_pwm").read_text()) == (
                test_curve_final_pwm[i - 1] * 255 // 100
            )
    else:
        # Assert fallback to direct access
        pump_report, fan_report = mock_krakenz3.device.sent

        assert pump_report.number == 0x72
        assert pump_report.data[3:43] == test_curve_final_pwm
        assert fan_report.number == 0x72
        assert fan_report.data[3:43] == test_curve_final_pwm


def test_krakenz3_not_totally_broken(mock_krakenz3):
    """Reasonable example calls to untested APIs do not raise exceptions."""
    mock_krakenz3.initialize()
    mock_krakenz3.device.preload_read(Report(0, Z3_SAMPLE_STATUS))
    _ = mock_krakenz3.get_status()
    mock_krakenz3.set_speed_profile(channel="fan", profile=iter([(20, 20), (30, 50), (40, 100)]))
    mock_krakenz3.set_fixed_speed(channel="pump", duty=50)

    # set_screen should be the last set of functions called
    mock_krakenz3.set_screen("lcd", "liquid", None)
    mock_krakenz3.set_screen("lcd", "brightness", "60")
    mock_krakenz3.set_screen("lcd", "orientation", "90")
    mock_krakenz3.set_screen(
        "lcd", "static", os.path.join(os.path.dirname(os.path.abspath(__file__)), "yellow.jpg")
    )
    mock_krakenz3.set_screen(
        "lcd", "gif", os.path.join(os.path.dirname(os.path.abspath(__file__)), "rgb.gif")
    )
