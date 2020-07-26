import unittest
from liquidctl.driver.smart_device import SmartDevice
from _testutils import MockHidapiDevice, Report


class SmartDeviceTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_hid = MockHidapiDevice()
        self.device = SmartDevice(self.mock_hid, 'Mock Smart Device',
                                  speed_channel_count=3,
                                  color_channel_count=1)
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """A few reasonable example calls do not raise exceptions."""
        for i in range(3):
            self.mock_hid.preload_read(Report(0, bytes(63)))
        self.device.initialize()
        status = self.device.get_status()
        self.device.set_color(channel='led', mode='breathing', colors=iter([[142, 24, 68]]),
                              speed='fastest')
        self.device.set_fixed_speed(channel='fan3', duty=50)
