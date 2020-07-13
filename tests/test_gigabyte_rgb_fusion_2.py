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
        self.assertEqual(len(self.mock_hid.sent), 1 + 8)
        for i, (report, data) in enumerate(self.mock_hid.sent):
            self.assertEqual(report, self.report_id)
            self.assertEqual(len(data), 63)  # TODO double check, more likely to be 64

    def test_get_status(self):
        self.assertEqual(self.device.get_status(), [])

    def test_initialize_status(self):
        self.mock_hid.preload_read(_INIT_REPLY_SAMPLE)
        name, fw_version, led_channels = self.device.initialize()
        self.assertEqual(name[1], "IT5702-GIGABYTE V1.0.10.0")
        self.assertEqual(fw_version[1], '1.0.10.0')
        self.assertEqual(led_channels[1], 7)

    def test_off_with_some_channel(self):
        colors = [[0xff, 0, 0x80]]  # should be ignored
        self.device.set_color(channel='led2', mode='off', colors=iter(colors))
        set_color, execute = self.mock_hid.sent
        self.assertEqual(set_color.data[0:2], [0x21, 0x02], "incorrect channel")
        self.assertEqual(set_color.data[10], 0x01, "wrong mode value")
        self.assertEqual(max(set_color.data[13:16]), 0, "incorrect color")
        self.assertEqual(max(set_color.data[21:27]), 0, "incorrect speed values")

    def test_static_with_some_channel(self):
        colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
        self.device.set_color(channel='led7', mode='static', colors=iter(colors))
        set_color, execute = self.mock_hid.sent
        self.assertEqual(set_color.data[0:2], [0x26, 0x40], "incorrect channel")
        self.assertEqual(set_color.data[10], 0x01, "wrong mode value")
        self.assertEqual(set_color.data[13:16], [0x80, 0x00, 0xff], "incorrect color encoding")
        self.assertEqual(max(set_color.data[21:27]), 0, "incorrect speed values")

    def test_pulse_with_some_channel_and_speed(self):
        colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
        self.device.set_color(channel='led3', mode='pulse', colors=iter(colors), speed='faster')
        set_color, execute = self.mock_hid.sent
        self.assertEqual(set_color.data[0:2], [0x22, 0x04], "incorrect channel")
        self.assertEqual(set_color.data[10], 0x02, "wrong mode value")
        self.assertEqual(set_color.data[13:16], [0x80, 0x00, 0xff], "incorrect color encoding")
        self.assertEqual(set_color.data[21:27], [0xe8, 0x03, 0xe8, 0x03, 0xf4, 0x01],
                         "incorrect speed values")

    def test_flash_with_some_channel_and_speed(self):
        colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
        self.device.set_color(channel='led6', mode='flash', colors=iter(colors), speed='slowest')
        set_color, execute = self.mock_hid.sent
        self.assertEqual(set_color.data[0:2], [0x25, 0x20], "incorrect channel")
        self.assertEqual(set_color.data[10], 0x03, "wrong mode value")
        self.assertEqual(set_color.data[13:16], [0x80, 0x00, 0xff], "incorrect color encoding")
        self.assertEqual(set_color.data[21:27], [0x64, 0x00, 0x64, 0x00, 0x60, 0x09],
                         "incorrect speed values")

    def test_double_flash_with_some_channel_and_speed_and_uppercase(self):
        colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
        self.device.set_color(channel='LED5', mode='DOUBLE-FLASH', colors=iter(colors),
                              speed='LUDICROUS')
        set_color, execute = self.mock_hid.sent
        self.assertEqual(set_color.data[0:2], [0x24, 0x10], "incorrect channel")
        self.assertEqual(set_color.data[10], 0x03, "wrong mode value")
        self.assertEqual(set_color.data[13:16], [0x80, 0x00, 0xff], "incorrect color encoding")
        self.assertEqual(set_color.data[21:27], [0x64, 0x00, 0x64, 0x00, 0x40, 0x06],
                         "incorrect speed values")

    def test_color_cycle_with_some_channel_and_speed(self):
        colors = [[0xff, 0, 0x80]]  # should be ignored
        self.device.set_color(channel='led4', mode='color-cycle', colors=iter(colors),
                              speed='fastest')
        set_color, execute = self.mock_hid.sent
        self.assertEqual(set_color.data[0:2], [0x23, 0x08], "incorrect channel")
        self.assertEqual(set_color.data[10], 0x04, "wrong mode value")
        self.assertEqual(max(set_color.data[13:16]), 0, "incorrect color")
        self.assertEqual(set_color.data[21:27], [0x26, 0x02, 0xc2, 0x01, 0x00, 0x00],
                         "incorrect speed values")
        # TODO brightness

    def test_common_behavior_in_all_set_color_writes(self):
        colors = [[0xff, 0, 0x80]]
        for mode in ['off', 'static', 'pulse', 'flash', 'double-flash', 'color-cycle']:
            self.mock_hid.sent = deque()
            self.device.set_color(channel='led1', mode=mode, colors=iter(colors))
            set_color, execute = self.mock_hid.sent
            self.assertEqual(execute.data[0:2], [0x28, 0xff], "incorrect execute payload")
            self.assertEqual(max(execute.data[2:]), 0, "incorrect execute padding")

    def test_sync_channel(self):
        colors = [[0xff, 0, 0x80]]
        self.device.set_color(channel='sync', mode='static', colors=iter(colors))
        self.assertEqual(len(self.mock_hid.sent), 8)  # 7*set + execute

    def test_reset_all_channels(self):
        self.device.reset_all_channels()
        for addr, report in enumerate(self.mock_hid.sent[:-1], 0x20):
            self.assertEqual(report.data[0:2], [addr, 0], "invalid payload")
            self.assertEqual(max(report.data[2:]), 0, "invalid padding")
        execute = self.mock_hid.sent[-1]
        self.assertEqual(execute.data[0:2], [0x28, 0xff], "incorrect execute payload")
        self.assertEqual(max(execute.data[2:]), 0, "incorrect execute padding")

    def test_invalid_set_color_arguments(self):
        self.assertRaises(Exception, self.device.set_color, channel='invalid',
                          mode='off', colors=[])
        self.assertRaises(Exception, self.device.set_color, channel='led1',
                          mode='invalid', colors=[])
        self.assertRaises(Exception, self.device.set_color, channel='led1',
                          mode='static', colors=[])
        self.assertRaises(Exception, self.device.set_color, channel='led1',
                          mode='pulse', colors=[[0xff, 0, 0x80]], speed='invalid')
