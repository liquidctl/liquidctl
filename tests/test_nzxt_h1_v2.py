# uses the psf/black style

import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.smart_device import H1V2

SAMPLE_STATUS = bytes.fromhex(
    "75021320020d85bcabab94188f5f010000a00f0032020284021e1e02f9066464"
    "0000000000000000000000000000000000000000000000000000000000000005"
)


class MockH1V2(MockHidapiDevice):
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
    raw = MockH1V2(raw_speed_channels=2, raw_led_channels=0)
    dev = H1V2(raw, "Mock H1 V2", speed_channel_count=2, color_channel_count=0)
    dev.connect()
    return dev


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True), (True, False)])
def test_initializes(mock_smart2, has_hwmon, direct_access, tmp_path):
    if has_hwmon:
        mock_smart2._hwmon = HwmonDevice("mock_module", tmp_path)

    _ = mock_smart2.initialize(direct_access=direct_access)

    writes = len(mock_smart2.device.sent)
    if not has_hwmon or direct_access:
        assert writes == 4
    else:
        assert writes == 2


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (False, True), (True, True)])
def test_reads_status(mock_smart2, has_hwmon, direct_access):
    if has_hwmon:
        mock_smart2._hwmon = HwmonDevice(None, None)

    mock_smart2.device.preload_read(Report(0, SAMPLE_STATUS))

    expected = [
        ("Fan 1 control mode", "PWM", ""),
        ("Fan 1 duty", 30, "%"),
        ("Fan 1 speed", 644, "rpm"),
        ("Fan 2 control mode", "PWM", ""),
        ("Fan 2 duty", 100, "%"),
        ("Fan 2 speed", 1785, "rpm"),
        ("Pump speed", 4000, "rpm"),
    ]

    got = mock_smart2.get_status(direct_access=direct_access)

    assert sorted(got) == sorted(expected)


def test_constructor_sets_up_all_channels(mock_smart2):
    assert mock_smart2._speed_channels == {
        "fan1": (0, 0, 100),
        "fan2": (1, 0, 100),
    }


def test_not_totally_broken(mock_smart2):
    _ = mock_smart2.initialize()
    mock_smart2.device.preload_read(Report(0, [0x75, 0x02] + [0] * 62))
    _ = mock_smart2.get_status()
    mock_smart2.set_fixed_speed(channel="fan2", duty=50)
