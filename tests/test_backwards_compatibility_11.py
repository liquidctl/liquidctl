"""Test backwards compatibility with liquidctl 1.1.0."""

from liquidctl.driver.kraken2 import Kraken2
from liquidctl.driver.usb import hid, HidapiDevice
import usb
import pytest


class _MockPyUsbHandle(usb.core.Device):
    def __init__(self, serial_number):
        self.idVendor = 0x1e71
        self.idProduct = 0x170e
        self._serial_number = serial_number

        class MockResourceManager():
            def dispose(self, *args, **kwargs):
                pass

        self._ctx = MockResourceManager()


def _mock_enumerate(vendor_id=0, product_id=0):
    return [
        {'vendor_id': vendor_id, 'product_id': product_id, 'serial_number': '987654321'},
        {'vendor_id': vendor_id, 'product_id': product_id, 'serial_number': '123456789'}
    ]


def test_construct_with_raw_pyusb_handle(monkeypatch):
    monkeypatch.setattr(hid, 'enumerate', _mock_enumerate)
    pyusb_handle = _MockPyUsbHandle(serial_number='123456789')
    liquidctl_device = Kraken2(pyusb_handle, 'Some device')
    assert liquidctl_device.device.vendor_id == pyusb_handle.idVendor, \
        '<driver instance>.device points to incorrect physical device'
    assert liquidctl_device.device.product_id == pyusb_handle.idProduct, \
        '<driver instance>.device points to incorrect physical device'
    assert liquidctl_device.device.serial_number == pyusb_handle.serial_number, \
        '<driver instance>.device points to different physical unit'
    assert isinstance(liquidctl_device.device, HidapiDevice), \
        '<driver instance>.device not properly converted to HidapiDevice instance'
