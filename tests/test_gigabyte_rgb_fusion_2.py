from _testutils import *

import unittest

from liquidctl.driver.gigabyte_rgb_fusion import RGBFusion2Driver

_INIT_REPLY_SAMPLE = bytes.fromhex(
    'cc01000701000a00000000004954353730322d47494741425954452056312e30'
    '2e31302e30000000000102000200010002000100000102000001025700000000'
)


class _MockRGBFusion2(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0xffff, product_id=0x5702, address=r'/generic\#123!&')
        self.fw_version = (1, 0, 10, 0)


class GigabyteRGBFusionTestCase(unittest.TestCase):
    def setUp(self):
        description = 'Mock Gigabyte RGB Fusion 2.0 ITE 0x5702'
        kwargs = {'speed_channel_count': 0, 'color_channel_count': 7}
        self.mock_hid = _MockRGBFusion2()
        self.device = RGBFusion2Driver(self.mock_hid, description, **kwargs)
        self.device.connect()
        self.report_id = 0xcc


    def tearDown(self):
        self.device.disconnect()


    def test_command_format(self):
        self.mock_hid.preload_read(Report(0xcc, _INIT_REPLY_SAMPLE))
        self.device.initialize()
        # driver does not support get_status
        # self.device.get_status()
        # driver does not support fans:
        # self.device.set_fixed_speed(channel='fan', duty=100)
        # self.device.set_speed_profile(channel='fan', profile=[])
        self.device.set_color(channel='sync', mode='off', colors=[])
        self.assertEqual(len(self.mock_hid.sent), 22)
        for i, (report, data) in enumerate(self.mock_hid.sent):
            self.assertEqual(report, self.report_id)


    def test_get_status(self):
        pass


    def test_initialize_status(self):
        self.mock_hid.preload_read(Report(0xcc, _INIT_REPLY_SAMPLE))
        (_, fw_version, ) = self.device.initialize()
        self.assertEqual(fw_version[1], '%d.%d.%d.%d' % self.mock_hid.fw_version)


    def test_address_leds(self):
        colors = [[255,0,128]]
        self.device.set_color(channel='led3', mode='pulse', colors=iter(colors), speed='faster')
        # check color values
        self.assertEqual(self.mock_hid.sent[2].data[13], 0x80 )
        self.assertEqual(self.mock_hid.sent[2].data[14], 0x00 )
        self.assertEqual(self.mock_hid.sent[2].data[15], 0xff )
        # check speed values
        self.assertEqual(self.mock_hid.sent[2].data[21:27], [0xe8, 0x03, 0xe8, 0x03, 0xf4, 0x01] )
        self.assertEqual(len(self.mock_hid.sent), 4)


    def test_address_components(self):
        colors = [[255,0,128]]
        self.device.set_color(channel='sync', mode='static', colors=iter(colors))
        # check mode = 1 (static)
        self.assertEqual(self.mock_hid.sent[2].data[10], 0x01 )
        # check if 22 commands were sent
        self.assertEqual(len(self.mock_hid.sent), 22)


    def test_leds_off(self):
        self.device.set_color(channel='sync', mode='off', colors=iter([]))
        # check mode = 1 (static)
        self.assertEqual(self.mock_hid.sent[2].data[10], 0x01 )
        self.assertEqual(self.mock_hid.sent[2].data[11], 0x00 )
        # check if 22 commands were sent
        self.assertEqual(len(self.mock_hid.sent), 22)


    def test_invalid_color_modes(self):
        self.assertRaises(Exception, self.device.set_color, channel='led1',
                          mode='invalid', colors=[])
        self.assertRaises(Exception, self.device.set_color, channel='led1',
                          mode='static', colors=[])
        self.assertRaises(Exception, self.device.set_color, channel='sync',
                          mode='invalid', colors=[])
        self.assertRaises(Exception, self.device.set_color, channel='invalid',
                          mode='off', colors=[])
