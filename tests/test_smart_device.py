import pytest
from liquidctl.driver.smart_device import SmartDevice
from _testutils import MockHidapiDevice, Report


@pytest.fixture
def mockSmartDevice():
    device = MockHidapiDevice(vendor_id=0x1e71, product_id=0x1714, address='addr')
    return SmartDevice(device, 'mock NZXT Smart Device V1', speed_channel_count=3, color_channel_count=1)


# class methods
def test_smart_device_constructor(mockSmartDevice):

    assert mockSmartDevice._speed_channels == {
            'fan1': (0, 0, 100),
            'fan2': (1, 0, 100),
            'fan3': (2, 0, 100),
        }

    assert mockSmartDevice._color_channels == {'led': (0), }


def test_smart_device_not_totally_broken(mockSmartDevice):
    dev = mockSmartDevice

    for i in range(3):
        dev.device.preload_read(Report(0, bytes(63)))

    dev.initialize()
    dev.get_status()

    dev.set_color(channel='led', mode='breathing', colors=iter([[142, 24, 68]]),
                  speed='fastest')

    dev.set_fixed_speed(channel='fan3', duty=50)
