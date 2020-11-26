import pytest

from liquidctl.driver.usb import UsbDriver, UsbHidDriver

from _testutils import MockHidapiDevice


@pytest.fixture
def emulated_hid_device():
    hiddev = MockHidapiDevice()
    dev = UsbHidDriver(hiddev, 'Test')

    return dev


def test_hid_connects(emulated_hid_device):
    dev = emulated_hid_device

    def mock_open():
        nonlocal opened
        opened = True

    dev.device.open = mock_open
    opened = False

    with dev.connect() as cm:
        assert cm == dev
        assert opened


@pytest.fixture
def emulated_usb_device():
    usbdev = MockHidapiDevice()  # hack, should mock PyUsbDevice
    dev = UsbDriver(usbdev, 'Test')

    return dev


def test_usb_connects(emulated_usb_device):
    dev = emulated_usb_device

    def mock_open():
        nonlocal opened
        opened = True

    dev.device.open = mock_open
    opened = False

    with dev.connect() as cm:
        assert cm == dev
        assert opened
