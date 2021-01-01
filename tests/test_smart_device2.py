import pytest
from liquidctl.driver.smart_device import SmartDevice2
from _testutils import MockHidapiDevice, Report


@pytest.fixture
def mockSmartDevice2():
    device = MockHidapiDevice(vendor_id=0x1e71, product_id=0x2006, address='addr')
    return SmartDevice2(device, 'mock NZXT Smart Device V2', speed_channel_count=3, color_channel_count=2)


##### class methods
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


def test_smart_device2_ot_totally_broken(mockSmartDevice2):

    frimwareData = bytearray(64)
    lightingData = bytearray(64)

    frimwareData[0:2] = [0x11, 0x01]
    lightingData[0:2] = [0x21, 0x03]
    lightingData[14] = 2
    lightingData[15 + 1 * 6] = 0x10
    lightingData[15 + 2 * 6] = 0x11

    replys = [
        bytearray(64),
        bytearray(64),
        frimwareData,
        lightingData,
        [0] + [0x67, 0x02] + [0] * 62,
        bytearray(64),
        bytearray(64),
    ]
    for reply in replys:
        mockSmartDevice2.device.preload_read(Report(reply[0], reply[1:]))

    mockSmartDevice2.connect()

    mockSmartDevice2.initialize()
    status = mockSmartDevice2.get_status()

    mockSmartDevice2.set_color(channel='led1', mode='breathing', colors=iter([[142, 24, 68]]),
                          speed='fastest')

    mockSmartDevice2.set_fixed_speed(channel='fan3', duty=50)
