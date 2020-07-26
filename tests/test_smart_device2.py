import unittest
from liquidctl.driver.smart_device import SmartDevice2
from liquidctl.util import Hue2Accessory
from liquidctl.util import HUE2_MAX_ACCESSORIES_IN_CHANNEL as MAX_ACCESSORIES
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
                reply[15 + 1 * MAX_ACCESSORIES] = Hue2Accessory.KRAKENX_GEN4_RING.value
                reply[15 + 2 * MAX_ACCESSORIES] = Hue2Accessory.KRAKENX_GEN4_LOGO.value
        self.preload_read(Report(reply[0], reply[1:]))


class SmartDevice2TestCase(unittest.TestCase):
    def setUp(self):
        self.mock_hid = _MockSmartDevice2(raw_speed_channels=3, raw_led_channels=2)
        self.device = SmartDevice2(self.mock_hid, 'Mock Smart Device V2',
                                   speed_channel_count=3,
                                   color_channel_count=2)
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """A few reasonable example calls do not raise exceptions."""
        self.device.initialize()
        self.mock_hid.preload_read(Report(0, [0x67, 0x02] + [0] * 62))
        status = self.device.get_status()
        self.device.set_color(channel='led1', mode='breathing', colors=iter([[142, 24, 68]]),
                              speed='fastest')
        self.device.set_fixed_speed(channel='fan3', duty=50)
