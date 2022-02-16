# uses the psf/black style

import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.smart_device import SmartDevice2


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
