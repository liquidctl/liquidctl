# uses the psf/black style

import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.smart_device import SmartDevice2

# https://github.com/liquidctl/liquidctl/issues/292#issuecomment-786876335
# (adapted: set control mode for connected fan to PWM)
SAMPLE_STATUS = bytes.fromhex(
    "67023a003f00185732533230312003000200000000000000fc03000000000000"
    "0000000000000000322828000000000032282800000000003000000000000000"
)


class MockSmart2(MockHidapiDevice):
    def __init__(self, raw_speed_channels, raw_led_channels):
        super().__init__()
        self.raw_speed_channels = raw_speed_channels
        self.raw_led_channels = raw_led_channels

    def write(self, data):
        reply = bytearray(64)
        if data[0:2] == [0x10, 0x01]:
            reply[0:2] = [0x11, 0x01]
        elif data[0:2] == [0x20, 0x03]:
            reply[0:2] = [0x21, 0x03]
            reply[14] = self.raw_led_channels
            if self.raw_led_channels > 1:
                reply[15 + 1 * 6] = 0x10
                reply[15 + 2 * 6] = 0x11
        self.preload_read(Report(reply[0], reply[1:]))
        return super().write(data)


@pytest.fixture
def mock_smart2():
    raw = MockSmart2(raw_speed_channels=3, raw_led_channels=2)
    dev = SmartDevice2(raw, "Mock Smart Device V2", speed_channel_count=3, color_channel_count=2)
    dev.connect()
    return dev


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True), (True, False)])
def test_initializes(mock_smart2, has_hwmon, direct_access, tmp_path):
    if has_hwmon:
        mock_smart2._hwmon = HwmonDevice("mock_module", tmp_path)

    # TODO check the result
    _ = mock_smart2.initialize(direct_access=direct_access)

    writes = len(mock_smart2.device.sent)
    if not has_hwmon or direct_access:
        assert writes == 4
    else:
        assert writes == 2


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_reads_status_directly(mock_smart2, has_hwmon, direct_access):
    if has_hwmon:
        mock_smart2._hwmon = HwmonDevice(None, None)

    mock_smart2.device.preload_read(Report(0, SAMPLE_STATUS))

    expected = [
        ("Fan 1 speed", 1020, "rpm"),
        ("Fan 1 duty", 50, "%"),
        ("Fan 1 control mode", "PWM", ""),
        ("Fan 2 speed", 0, "rpm"),
        ("Fan 2 duty", 40, "%"),
        ("Fan 2 control mode", None, ""),
        ("Fan 3 speed", 0, "rpm"),
        ("Fan 3 duty", 40, "%"),
        ("Fan 3 control mode", None, ""),
        ("Noise level", 48, "dB"),
    ]

    got = mock_smart2.get_status(direct_access=direct_access)

    assert sorted(got) == sorted(expected)


def test_reads_status_from_hwmon(mock_smart2, tmp_path):
    mock_smart2._hwmon = HwmonDevice("mock_module", tmp_path)
    (tmp_path / "pwm1_enable").write_text("1\n")
    (tmp_path / "pwm2_enable").write_text("0\n")
    (tmp_path / "pwm3_enable").write_text("0\n")
    (tmp_path / "pwm1_mode").write_text("1\n")
    (tmp_path / "pwm2_mode").write_text("0\n")
    (tmp_path / "pwm3_mode").write_text("0\n")
    (tmp_path / "pwm1").write_text("127\n")
    (tmp_path / "pwm2").write_text("102\n")
    (tmp_path / "pwm3").write_text("102\n")
    (tmp_path / "fan1_input").write_text("1020\n")
    (tmp_path / "fan2_input").write_text("0\n")
    (tmp_path / "fan3_input").write_text("0\n")

    expected = [
        ("Fan 1 speed", 1020, "rpm"),
        ("Fan 1 duty", pytest.approx(50, rel=1.0 / 255), "%"),
        ("Fan 1 control mode", "PWM", ""),
        ("Fan 2 speed", 0, "rpm"),
        ("Fan 2 duty", pytest.approx(40, rel=1.0 / 255), "%"),
        ("Fan 2 control mode", "DC", ""),
        ("Fan 3 speed", 0, "rpm"),
        ("Fan 3 duty", pytest.approx(40, rel=1.0 / 255), "%"),
        ("Fan 3 control mode", "DC", ""),
    ]

    got = mock_smart2.get_status()

    assert sorted(got) == sorted(expected)


def test_constructor_sets_up_all_channels(mock_smart2):
    assert mock_smart2._speed_channels == {
        "fan1": (0, 0, 100),
        "fan2": (1, 0, 100),
        "fan3": (2, 0, 100),
    }
    assert mock_smart2._color_channels == {
        "led1": (0b001),
        "led2": (0b010),
        "sync": (0b011),
    }


def test_not_totally_broken(mock_smart2):
    _ = mock_smart2.initialize()
    mock_smart2.device.preload_read(Report(0, [0x67, 0x02] + [0] * 62))
    _ = mock_smart2.get_status()
    mock_smart2.set_color(
        channel="led1", mode="breathing", colors=iter([[142, 24, 68]]), speed="fastest"
    )
    mock_smart2.set_fixed_speed(channel="fan3", duty=50)
