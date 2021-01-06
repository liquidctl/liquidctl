import pytest
from liquidctl.driver.smart_device import SmartDevice2
from _testutils import MockHidapiDevice, Report


class _MockSmartDevice2(MockHidapiDevice):
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


@pytest.fixture
def mockSmartDevice2():
    device = _MockSmartDevice2(raw_speed_channels=3, raw_led_channels=2)
    dev = SmartDevice2(device, 'mock NZXT Smart Device V2', speed_channel_count=3, color_channel_count=2)
    dev.connect()
    return dev


# class methods
def test_smart_device2_constructor(mockSmartDevice2):

    assert mockSmartDevice2._speed_channels == {
            'fan1': (0, 0, 100),
            'fan2': (1, 0, 100),
            'fan3': (2, 0, 100),
        }

    assert mockSmartDevice2._color_channels == {
            'led1': (0b001),
            'led2': (0b010),
            'sync': (0b011),
        }


def test_smart_device2_not_totally_broken(mockSmartDevice2):
    dev = mockSmartDevice2

    dev.initialize()
    dev.device.preload_read(Report(0, [0x67, 0x02] + [0] * 62))
    dev.get_status()

    dev.set_color(channel='led1', mode='breathing', colors=iter([[142, 24, 68]]),
                  speed='fastest')

    dev.set_fixed_speed(channel='fan3', duty=50)
