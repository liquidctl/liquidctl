import pytest

from liquidctl.driver.usb import UsbDriver, UsbHidDriver

from _testutils import MockHidapiDevice


@pytest.fixture
def emulated_hid_device():
    hiddev = MockHidapiDevice()
    return UsbHidDriver(hiddev, 'Test')


@pytest.fixture
def emulated_usb_device():
    usbdev = MockHidapiDevice()  # hack, should mock PyUsbDevice
    dev = UsbDriver(usbdev, 'Test')

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


def test_hid_disconnect(emulated_hid_device):
    dev = emulated_hid_device

    def mock_close():
        nonlocal opened
        opened = False

    dev.device.close = mock_close
    opened = True

    dev.disconnect()
    assert not opened


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


def test_usb_disconnect(emulated_usb_device):
    dev = emulated_usb_device

    def mock_close():
        nonlocal opened
        opened = False

    dev.device.close = mock_close
    opened = True

    dev.disconnect()
    assert not opened
