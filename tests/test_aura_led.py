import pytest
from _testutils import MockHidapiDevice, Report

from collections import deque

from liquidctl.driver.aura_led import AuraLed

# Sample data for Aura LED controller from ASUS ProArt Z690-Creator WiFi
_INIT_19AF_FIRMWARE_DATA = bytes.fromhex(
    "ec0241554c41332d415233322d30323037000000000000000000000000000000"
    "000000000000000000000000000000000000000000000000000000000000000000"
)
_INIT_19AF_FIRMWARE = Report(_INIT_19AF_FIRMWARE_DATA[0], _INIT_19AF_FIRMWARE_DATA[1:])

_INIT_19AF_CONFIG_DATA = bytes.fromhex(
    "ec3000001e9f03010000783c00010000783c00010000783c0000000000000001"
    "040201f40000000000000000000000000000000000000000000000000000000000"
)
_INIT_19AF_CONFIG = Report(_INIT_19AF_CONFIG_DATA[0], _INIT_19AF_CONFIG_DATA[1:])


@pytest.fixture
def mockAuraLed_19AFDevice():
    device = MockHidapiDevice(vendor_id=0x0B05, product_id=0x19AF, address="addr")
    dev = AuraLed(device, "mock Aura LED Controller")
    dev.connect()
    return dev


def test_aura_led_19AF_device_command_format(mockAuraLed_19AFDevice):
    mockAuraLed_19AFDevice.device.preload_read(_INIT_19AF_FIRMWARE)
    mockAuraLed_19AFDevice.device.preload_read(_INIT_19AF_CONFIG)
    mockAuraLed_19AFDevice.initialize()  # should perform 3 writes
    mockAuraLed_19AFDevice.set_color(
        channel="sync", mode="off", colors=[]
    )  # should perform 14 writes
    assert len(mockAuraLed_19AFDevice.device.sent) == 2 + 14
    for i, (report, data) in enumerate(mockAuraLed_19AFDevice.device.sent):
        assert report == 0xEC
        assert len(data) == 64


def test_aura_led_19AF_device_get_status(mockAuraLed_19AFDevice):
    mockAuraLed_19AFDevice.device.preload_read(_INIT_19AF_CONFIG)
    assert mockAuraLed_19AFDevice.get_status() != []


def test_aura_led_19AF_device_initialize_status(mockAuraLed_19AFDevice):
    mockAuraLed_19AFDevice.device.preload_read(_INIT_19AF_FIRMWARE)
    mockAuraLed_19AFDevice.device.preload_read(_INIT_19AF_CONFIG)
    status_list = mockAuraLed_19AFDevice.initialize()
    firmware_tuple = status_list[0]
    assert firmware_tuple[1] == "AULA3-AR32-0207"


def test_aura_led_19AF_device_off_with_some_channel(mockAuraLed_19AFDevice):
    colors = [[0xFF, 0, 0x80]]  # should be ignored
    mockAuraLed_19AFDevice.set_color(channel="led2", mode="off", colors=iter(colors))
    assert len(mockAuraLed_19AFDevice.device.sent) == 5
    data1 = mockAuraLed_19AFDevice.device.sent[0].data
    data2 = mockAuraLed_19AFDevice.device.sent[1].data
    assert data1[1] == 0x01  # key for led2
    assert data1[4] == 0x00  # off
    assert data2[2] == 0x02  # channel led2
    assert data2[7:10] == [0x00, 0x00, 0x00]


def test_aura_led_19AF_static_with_some_channel(mockAuraLed_19AFDevice):
    colors = [[0xFF, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
    mockAuraLed_19AFDevice.set_color(channel="led2", mode="static", colors=iter(colors))
    assert len(mockAuraLed_19AFDevice.device.sent) == 5
    data1 = mockAuraLed_19AFDevice.device.sent[0].data
    data2 = mockAuraLed_19AFDevice.device.sent[1].data
    assert data1[1] == 0x01  # key for led2
    assert data1[4] == 0x01  # static mode
    assert data2[2] == 0x02  # channel led2
    assert data2[7:10] == [0xFF, 0x00, 0x80]


def test_aura_led_19AF_spectrum_cycle_with_some_channel(mockAuraLed_19AFDevice):
    colors = [[0xFF, 0, 0x80], [0x30, 0x30, 0x30]]  # second color should be ignored
    mockAuraLed_19AFDevice.set_color(channel="led3", mode="spectrum_cycle", colors=iter(colors))
    assert len(mockAuraLed_19AFDevice.device.sent) == 5
    data1 = mockAuraLed_19AFDevice.device.sent[0].data
    data2 = mockAuraLed_19AFDevice.device.sent[1].data
    assert data1[1] == 0x01  # key for led3
    assert data1[4] == 0x04  # spectrum cycle
    assert data2[2] == 0x04  # channel led3
    assert data2[7:10] == [0x00, 0x00, 0x00]


def test_aura_led_19AF_device_sync_channel(mockAuraLed_19AFDevice):
    colors = [[0xFF, 0, 0x80]]
    mockAuraLed_19AFDevice.set_color(channel="sync", mode="static", colors=iter(colors))
    assert len(mockAuraLed_19AFDevice.device.sent) == 14  # 14 writes


def test_aura_led_19AF_device_invalid_set_color_arguments(mockAuraLed_19AFDevice):

    with pytest.raises(KeyError):
        mockAuraLed_19AFDevice.set_color("invalid", "off", [])

    with pytest.raises(KeyError):
        mockAuraLed_19AFDevice.set_color("led2", "invalid", [])

    with pytest.raises(ValueError):
        mockAuraLed_19AFDevice.set_color("led3", "static", [])


def test_aura_led_19AF_device_initialize_status(mockAuraLed_19AFDevice):
    mockAuraLed_19AFDevice.device.preload_read(_INIT_19AF_FIRMWARE)
    mockAuraLed_19AFDevice.device.preload_read(_INIT_19AF_CONFIG)
    status_list = mockAuraLed_19AFDevice.initialize()
    firmware_tuple = status_list[0]
    assert firmware_tuple[1] == "AULA3-AR32-0207"
