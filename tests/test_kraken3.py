import unittest

from liquidctl.driver.kraken3 import KrakenX3, KrakenZ3
from liquidctl.driver.kraken3 import _COLOR_CHANNELS_KRAKENX
from liquidctl.driver.kraken3 import _SPEED_CHANNELS_KRAKENX
from liquidctl.driver.kraken3 import _SPEED_CHANNELS_KRAKENZ
from liquidctl.util import Hue2Accessory
from liquidctl.util import HUE2_MAX_ACCESSORIES_IN_CHANNEL as MAX_ACCESSORIES

from _testutils import MockHidapiDevice, Report

# https://github.com/jonasmalacofilho/liquidctl/issues/160#issuecomment-664044103
_SAMPLE_STATUS = bytes.fromhex(
    '7502200036000b51535834353320012101a80635350000000000000000000000'
    '0000000000000000000000000000000000000000000000000000000000000000'
)

class _MockKrakenDevice(MockHidapiDevice):
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
        self.preload_read(Report(0, reply))


class KrakenX3TestCase(unittest.TestCase):
    def setUp(self):
        self.mock_hid = _MockKrakenDevice(raw_led_channels=len(_COLOR_CHANNELS_KRAKENX) - 1)
        self.device = KrakenX3(self.mock_hid, 'Mock Kraken X73',
                               speed_channels=_SPEED_CHANNELS_KRAKENX,
                               color_channels=_COLOR_CHANNELS_KRAKENX)
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_parses_status_fields(self):
        self.mock_hid.preload_read(Report(0, _SAMPLE_STATUS))
        temperature, pump_speed, pump_duty = self.device.get_status()
        assert temperature == ('Liquid temperature', 33.1, '°C')
        assert pump_speed == ('Pump speed', 1704, 'rpm')
        assert pump_duty == ('Pump duty', 53, '%')

    def test_not_totally_broken(self):
        """Reasonable example calls to untested APIs do not raise exceptions."""
        infos = self.device.initialize()
        self.device.set_color(channel='ring', mode='fixed', colors=iter([[3, 2, 1]]),
                              speed='fastest')
        self.device.set_speed_profile(channel='pump',
                                      profile=iter([(20, 20), (30, 50), (40, 100)]))
        self.device.set_fixed_speed(channel='pump', duty=50)


class KrakenZ3TestCase(unittest.TestCase):
    def setUp(self):
        self.mock_hid = _MockKrakenDevice(raw_led_channels=0)
        self.device = KrakenZ3(self.mock_hid, 'Mock Kraken Z73',
                               speed_channels=_SPEED_CHANNELS_KRAKENZ,
                               color_channels={})
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """Reasonable example calls to untested APIs do not raise exceptions."""
        infos = self.device.initialize()
        self.mock_hid.preload_read(Report(0, _SAMPLE_STATUS))
        status = self.device.get_status()
        self.device.set_speed_profile(channel='fan',
                                      profile=iter([(20, 20), (30, 50), (40, 100)]))
        self.device.set_fixed_speed(channel='pump', duty=50)
