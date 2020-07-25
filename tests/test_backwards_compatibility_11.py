"""Test compatiblitity with liquidctl 1.1.0."""

import unittest
from liquidctl.driver.kraken2 import Kraken2

SYSTEM_HAS_KRAKEN2 = len(Kraken2.find_supported_devices()) > 0

class Pre12RawPyUsbHandles(unittest.TestCase):
    @unittest.skipUnless(SYSTEM_HAS_KRAKEN2, "requires a physical/real Kraken X2")
    def test_construct_with_raw_pyusb_handle(self):
        import usb

        USB_VID_NZXT = 0x1E71
        USB_PID_KRAKENX_GEN3 = 0x170E

        pyusb_device = usb.core.find(idVendor=USB_VID_NZXT, idProduct=USB_PID_KRAKENX_GEN3)
        liquidctl_device = Kraken2(pyusb_device, 'Some device')
        self.assertEqual(liquidctl_device.device.serial_number, pyusb_device.serial_number,
                          msg='<driver instance>.device not usable')
        self.assertNotIsInstance(liquidctl_device.device, usb.core.Device,
                                 msg='<driver instance>.device not wrapped/converted')
