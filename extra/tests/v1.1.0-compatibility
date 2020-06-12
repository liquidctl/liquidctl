#!/usr/bin/env python

"""Test compatiblitity with liquidctl 1.1.0."""

import logging
import unittest


class CompatibleWith1_1(unittest.TestCase):
    def test_construct_with_usb_handle(self):
        import usb
        from liquidctl.driver.kraken_two import KrakenTwoDriver

        USB_VID_NZXT = 0x1E71
        USB_PID_KRAKENX_GEN3 = 0x170E

        pyusb_device = usb.core.find(idVendor=USB_VID_NZXT, idProduct=USB_PID_KRAKENX_GEN3)
        liquidctl_device = KrakenTwoDriver(pyusb_device, 'Some device')
        self.assertEqual(liquidctl_device.device.serial_number, pyusb_device.serial_number,
                          msg='<driver instance>.device not usable')
        self.assertNotIsInstance(liquidctl_device.device, usb.core.Device,
                                 msg='<driver instance>.device not wrapped/converted')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s: %(message)s')
    unittest.main()
