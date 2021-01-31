import pytest
from _testutils import MockHidapiDevice, Report

from collections import deque

from liquidctl.driver.rgb_fusion2 import RgbFusion2

# Sample data for 5702 controller from a Gigabyte Z490 Vision D
# https://github.com/liquidctl/liquidctl/issues/151#issuecomment-663213956
_INIT_5702_DATA = bytes.fromhex(
    'cc01000701000a00000000004954353730322d47494741425954452056312e30'
    '2e31302e30000000000102000200010002000100000102000001025700000000'
)
_INIT_5702_SAMPLE = Report(_INIT_5702_DATA[0], _INIT_5702_DATA[1:])

# Sample data for 8297 controller from a Gigabyte X570 Aorus Elite rev 1.0
# https://github.com/liquidctl/liquidctl/issues/151#issuecomment-663247422
# (note: original data had a trailing 0x61 byte, but that seems to be an artifact)
_INIT_8297_DATA = bytes.fromhex(
    '00010001010006000000000049543832393742582d4742583537300000000000'
    '0000000000000000000000000200010002000100000102000001978200000000'
)
_INIT_8297_SAMPLE = Report(_INIT_8297_DATA[0], _INIT_8297_DATA[1:])


@pytest.fixture
def mockRgbFusion2_5702Device():
    device = MockHidapiDevice(vendor_id=0x048d, product_id=0x5702, address='addr')
    dev = RgbFusion2(device, 'mock 5702 Controller')

    dev.connect()
    return dev


class Mock8297HidInterface(MockHidapiDevice):
    def get_feature_report(self, report_id, length):
        """Get a feature report emulating out of spec behavior of the device."""
        return super().get_feature_report(0, length)


@pytest.fixture
def mockRgbFusion2_8297Device():
    device = Mock8297HidInterface(vendor_id=0x048d, product_id=0x8297, address='addr')
    dev = RgbFusion2(device, 'mock 8297 Controller')

    dev.connect()
    return dev


def test_fusion2_5702_device_command_format(mockRgbFusion2_5702Device):
    mockRgbFusion2_5702Device.device.preload_read(_INIT_5702_SAMPLE)
    mockRgbFusion2_5702Device.initialize()
    mockRgbFusion2_5702Device.set_color(channel='sync', mode='off', colors=[])
    assert len(mockRgbFusion2_5702Device.device.sent) == 1 + 8 + 1

    for i, (report, data) in enumerate(mockRgbFusion2_5702Device.device.sent):
        assert report == 0xcc
        assert len(data) == 63  # TODO double check, more likely to be 64


def test_fusion2_5702_device_get_status(mockRgbFusion2_5702Device):
    assert mockRgbFusion2_5702Device.get_status() == []


def test_fusion2_5702_device_initialize_status(mockRgbFusion2_5702Device):
    mockRgbFusion2_5702Device.device.preload_read(_INIT_5702_SAMPLE)
    name, fw_version = mockRgbFusion2_5702Device.initialize()
    assert name[1] == "IT5702-GIGABYTE V1.0.10.0"
    assert fw_version[1] == '1.0.10.0'


def test_fusion2_5702_device_off_with_some_channel(mockRgbFusion2_5702Device):
    colors = [[0xff, 0, 0x80]]  # should be ignored
    mockRgbFusion2_5702Device.set_color(channel='led8', mode='off', colors=iter(colors))
    set_color, execute = mockRgbFusion2_5702Device.device.sent
    assert set_color.data[0:2] == [0x27, 0x80]
    assert set_color.data[10] == 0x01
    assert max(set_color.data[13:16]) == 0
    assert max(set_color.data[21:27]) == 0


def test_fusion2_5702_device_fixed_with_some_channel(mockRgbFusion2_5702Device):
    colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
    mockRgbFusion2_5702Device.set_color(channel='led7', mode='fixed', colors=iter(colors))
    set_color, execute = mockRgbFusion2_5702Device.device.sent
    assert set_color.data[0:2] == [0x26, 0x40]
    assert set_color.data[10] == 0x01
    assert set_color.data[13:16] == [0x80, 0x00, 0xff]
    assert max(set_color.data[21:27]) == 0


def test_fusion2_5702_device_pulse_with_some_channel_and_speed(mockRgbFusion2_5702Device):
    colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
    mockRgbFusion2_5702Device.set_color(channel='led3', mode='pulse', colors=iter(colors), speed='faster')
    set_color, execute = mockRgbFusion2_5702Device.device.sent

    assert set_color.data[0:2] == [0x22, 0x04]
    assert set_color.data[10] == 0x02
    assert set_color.data[13:16] == [0x80, 0x00, 0xff]
    assert set_color.data[21:27] == [0xe8, 0x03, 0xe8, 0x03, 0xf4, 0x01]


def test_fusion2_5702_device_flash_with_some_channel_and_speed(mockRgbFusion2_5702Device):
    colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
    mockRgbFusion2_5702Device.set_color(channel='led6', mode='flash', colors=iter(colors), speed='slowest')
    set_color, execute = mockRgbFusion2_5702Device.device.sent

    assert set_color.data[0:2] == [0x25, 0x20]
    assert set_color.data[10] == 0x03
    assert set_color.data[13:16] == [0x80, 0x00, 0xff]
    assert set_color.data[21:27] == [0x64, 0x00, 0x64, 0x00, 0x60, 0x09]


def test_fusion2_5702_device_double_flash_with_some_channel_and_speed_and_uppercase(mockRgbFusion2_5702Device):
    colors = [[0xff, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
    mockRgbFusion2_5702Device.set_color(channel='led5', mode='double-flash', colors=iter(colors),
                                        speed='ludicrous')
    set_color, execute = mockRgbFusion2_5702Device.device.sent

    assert set_color.data[0:2] == [0x24, 0x10]
    assert set_color.data[10] == 0x03
    assert set_color.data[13:16] == [0x80, 0x00, 0xff]
    assert set_color.data[21:27] == [0x64, 0x00, 0x64, 0x00, 0x40, 0x06]


def test_fusion2_5702_device_color_cycle_with_some_channel_and_speed(mockRgbFusion2_5702Device):
    colors = [[0xff, 0, 0x80]]  # should be ignored
    mockRgbFusion2_5702Device.set_color(channel='led4', mode='color-cycle', colors=iter(colors),
                                        speed='fastest')
    set_color, execute = mockRgbFusion2_5702Device.device.sent

    assert set_color.data[0:2] == [0x23, 0x08]
    assert set_color.data[10] == 0x04
    assert max(set_color.data[13:16]) == 0
    assert set_color.data[21:27] == [0x26, 0x02, 0xc2, 0x01, 0x00, 0x00]
    # TODO brightness


def test_fusion2_5702_device_common_behavior_in_all_set_color_writes(mockRgbFusion2_5702Device):
    colors = [[0xff, 0, 0x80]]
    for mode in ['off', 'fixed', 'pulse', 'flash', 'double-flash', 'color-cycle']:
        mockRgbFusion2_5702Device.device.sent = deque()
        mockRgbFusion2_5702Device.set_color(channel='led1', mode=mode, colors=iter(colors))
        set_color, execute = mockRgbFusion2_5702Device.device.sent

        assert execute.data[0:2] == [0x28, 0xff]
        assert max(execute.data[2:]) == 0


def test_fusion2_5702_device_sync_channel(mockRgbFusion2_5702Device):
    colors = [[0xff, 0, 0x80]]
    mockRgbFusion2_5702Device.set_color(channel='sync', mode='fixed', colors=iter(colors))
    assert len(mockRgbFusion2_5702Device.device.sent) == 8 + 1  # 8 × set + execute


def test_fusion2_5702_device_reset_all_channels(mockRgbFusion2_5702Device):
    mockRgbFusion2_5702Device.reset_all_channels()
    for addr, report in enumerate(mockRgbFusion2_5702Device.device.sent[:-1], 0x20):
        assert report.data[0:2] == [addr, 0]
        assert max(report.data[2:]) == 0
    execute = mockRgbFusion2_5702Device.device.sent[-1]
    assert execute.data[0:2] == [0x28, 0xff]
    assert max(execute.data[2:]) == 0


def test_fusion2_5702_device_invalid_set_color_arguments(mockRgbFusion2_5702Device):

    with pytest.raises(KeyError):
        mockRgbFusion2_5702Device.set_color('invalid', 'off', [])

    with pytest.raises(KeyError):
        mockRgbFusion2_5702Device.set_color('led1', 'invalid', [])

    with pytest.raises(ValueError):
        mockRgbFusion2_5702Device.set_color('led1', 'fixed', [])

    with pytest.raises(KeyError):
        mockRgbFusion2_5702Device.set_color('led1', 'pulse', [[0xff, 0, 0x80]], speed='invalid')


def test_fusion2_8297_device_initialize_status(mockRgbFusion2_8297Device):
    mockRgbFusion2_8297Device.device.preload_read(_INIT_8297_SAMPLE)
    name, fw_version = mockRgbFusion2_8297Device.initialize()

    assert name[1] == "IT8297BX-GBX570"
    assert fw_version[1] == '1.0.6.0'

    # other tests skipped, see Controller5702TestCase
