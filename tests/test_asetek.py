import unittest
from liquidctl.driver.asetek import Modern690Lc, Legacy690Lc, Hydro690Lc
from _testutils import noop

class _Mock690LcDevice():
    def __init__(self, vendor_id=None, product_id=None, release_number=None,
                 serial_number=None, bus=None, address=None, port=None):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.release_numer = release_number
        self.serial_number = serial_number
        self.bus = bus
        self.address = address
        self.port = port

        self.open = noop
        self.claim = noop
        self.release = noop
        self.close = noop
        self.clear_enqueued_reports = noop
        self.ctrl_transfer = noop
        self.write = noop

    def read(self, endpoint, length, timeout=None):
        return [0] * length


class Modern690LcTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_usb = _Mock690LcDevice()
        self.device = Modern690Lc(self.mock_usb, 'Mock Modern 690LC')
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """A few reasonable example calls do not raise exceptions."""
        self.device.initialize()
        status = self.device.get_status()
        self.device.set_color(channel='led', mode='blinking', colors=iter([[3, 2, 1]]),
                       time_per_color=3, time_off=1, alert_threshold=42,
                       alert_color=[90, 80, 10])
        self.device.set_color(channel='led', mode='rainbow', colors=[], speed=5)
        self.device.set_speed_profile(channel='fan',
                               profile=iter([(20, 20), (30, 50), (40, 100)]))
        self.device.set_fixed_speed(channel='pump', duty=50)


class Legacy690LcTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_usb = _Mock690LcDevice(vendor_id=0xffff, product_id=0xb200, bus=1, port=(1,))
        self.device = Legacy690Lc(self.mock_usb, 'Mock Legacy 690LC')
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """A few reasonable example calls do not raise exceptions."""
        self.device.initialize()
        status = self.device.get_status()
        self.device.set_color(channel='led', mode='blinking', colors=iter([[3, 2, 1]]),
                       time_per_color=3, time_off=1, alert_threshold=42,
                       alert_color=[90, 80, 10])
        self.device.set_fixed_speed(channel='fan', duty=80)
        self.device.set_fixed_speed(channel='pump', duty=50)
