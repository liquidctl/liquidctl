from _testutils import *

import unittest

from liquidctl.driver.gigabyte_rgb_fusion import RGBFusion2Driver

_INIT_REPLY_SAMPLE_DATA = bytes.fromhex(
    '01000701000a00000000004954353730322d47494741425954452056312e30e2'
    '2e31302e300000000001020002000100020001000001020000010257000000'
)
_INIT_REPLY_SAMPLE = Report(0xcc, _INIT_REPLY_SAMPLE_DATA)


class GigabyteRGBFusionTestCase(unittest.TestCase):
    def setUp(self):
        description = 'Mock 5702 Controller'
        self.mock_hid = MockHidapiDevice()
        self.device = RGBFusion2Driver(self.mock_hid, description)
        self.device.connect()
        self.report_id = 0xcc

    def tearDown(self):
        self.device.disconnect()

    def test_command_format(self):
        self.mock_hid.preload_read(_INIT_REPLY_SAMPLE)
        self.device.initialize()
        self.device.set_color(channel='sync', mode='off', colors=[])
        self.assertEqual(len(self.mock_hid.sent), 1 + 22)
        for i, (report, data) in enumerate(self.mock_hid.sent):
            self.assertEqual(report, self.report_id)
            # TODO no common structure expected in `data` to test here?

    def test_get_status(self):
        self.assertEqual(self.device.get_status(), [])

    def test_initialize_status(self):
        self.mock_hid.preload_read(_INIT_REPLY_SAMPLE)
        name, fw_version, led_channels = self.device.initialize()
        self.assertEqual(name[1], "IT5702-GIGABYTE V1.0.10.0")
        self.assertEqual(fw_version[1], '1.0.10.0')
        self.assertEqual(led_channels[1], 7)


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
