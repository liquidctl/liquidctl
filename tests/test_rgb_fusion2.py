import unittest
from collections import deque
from liquidctl.driver.rgb_fusion2 import RgbFusion2
from _testutils import MockHidapiDevice, Report

# Sample data for 5702 controller from a Gigabyte Z490 Vision D
# https://github.com/jonasmalacofilho/liquidctl/issues/151#issuecomment-663213956
_INIT_5702_DATA = bytes.fromhex(
    'cc01000701000a00000000004954353730322d47494741425954452056312e30'
    '2e31302e30000000000102000200010002000100000102000001025700000000'
)
_INIT_5702_SAMPLE = Report(_INIT_5702_DATA[0], _INIT_5702_DATA[1:])

# Sample data for 8297 controller from a Gigabyte X570 Aorus Elite rev 1.0
# https://github.com/jonasmalacofilho/liquidctl/issues/151#issuecomment-663247422
# (note: original data had a trailing 0x61 byte, but that seems to be an artifact)
_INIT_8297_DATA = bytes.fromhex(
    '00010001010006000000000049543832393742582d4742583537300000000000'
    '0000000000000000000000000200010002000100000102000001978200000000'
)
_INIT_8297_SAMPLE = Report(_INIT_8297_DATA[0], _INIT_8297_DATA[1:])


class Controller5702TestCase(unittest.TestCase):
    def setUp(self):
        description = 'Mock 5702 Controller'
        self.mock_hid = MockHidapiDevice()
        self.device = RgbFusion2(self.mock_hid, description)
        self.device.connect()
        self.report_id = 0xcc

    def tearDown(self):
        self.device.disconnect()

    def test_command_format(self):
        self.mock_hid.preload_read(_INIT_5702_SAMPLE)
        self.device.initialize()
        self.device.set_color(channel='sync', mode='off', colors=[])
        self.assertEqual(len(self.mock_hid.sent), 1 + 8 + 1)
        for i, (report, data) in enumerate(self.mock_hid.sent):
            self.assertEqual(report, self.report_id)
            self.assertEqual(len(data), 63)  # TODO double check, more likely to be 64

    def test_get_status(self):
        self.assertEqual(self.device.get_status(), [])

    def test_initialize_status(self):
        self.mock_hid.preload_read(_INIT_5702_SAMPLE)
        name, fw_version = self.device.initialize()
        self.assertEqual(name[1], "IT5702-GIGABYTE V1.0.10.0")
        self.assertEqual(fw_version[1], '1.0.10.0')

    def test_off_with_some_channel(self):
        colors = [[0xff, 0, 0x80]]  # should be ignored
        self.device.set_color(channel='led8', mode='off', colors=iter(colors))
        set_color, execute = self.mock_hid.sent
        self.assertEqual(set_color.data[0:2], [0x27, 0x80], "incorrect channel")
        self.assertEqual(set_color.data[10], 0x01, "wrong mode value")
        self.assertEqual(max(set_color.data[13:16]), 0, "incorrect color")
        self.assertEqual(max(set_color.data[21:27]), 0, "incorrect speed values")

    def test_fixed_with_some_channel(self):
        colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
        self.device.set_color(channel='led7', mode='fixed', colors=iter(colors))
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
        for mode in ['off', 'fixed', 'pulse', 'flash', 'double-flash', 'color-cycle']:
            self.mock_hid.sent = deque()
            self.device.set_color(channel='led1', mode=mode, colors=iter(colors))
            set_color, execute = self.mock_hid.sent
            self.assertEqual(execute.data[0:2], [0x28, 0xff], "incorrect execute payload")
            self.assertEqual(max(execute.data[2:]), 0, "incorrect execute padding")

    def test_sync_channel(self):
        colors = [[0xff, 0, 0x80]]
        self.device.set_color(channel='sync', mode='fixed', colors=iter(colors))
        self.assertEqual(len(self.mock_hid.sent), 8 + 1)  # 8 × set + execute

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
                          mode='fixed', colors=[])
        self.assertRaises(Exception, self.device.set_color, channel='led1',
                          mode='pulse', colors=[[0xff, 0, 0x80]], speed='invalid')


class Mock8297HidInterface(MockHidapiDevice):
    def get_feature_report(self, report_id, length):
        """Get a feature report emulating out of spec behavior of the device."""
        return super().get_feature_report(0, length)


class Controller8297TestCase(unittest.TestCase):
    def setUp(self):
        description = 'Mock 8297 Controller'
        self.mock_hid = Mock8297HidInterface()
        self.device = RgbFusion2(self.mock_hid, description)
        self.device.connect()
        self.report_id = 0xcc

    def test_initialize_status(self):
        self.mock_hid.preload_read(_INIT_8297_SAMPLE)
        name, fw_version = self.device.initialize()
        self.assertEqual(name[1], "IT8297BX-GBX570")
        self.assertEqual(fw_version[1], '1.0.6.0')

    # other tests skipped, see Controller5702TestCase
