import unittest
from collections import deque
from liquidctl.driver.asetek_pro import CorsairAsetekProDriver
from _testutils import noop

class _MockAsetekProDevice():
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

        self._reset_sent()

    def read(self, endpoint, length, timeout=None):
        return [0] * length

    def write(self, endpoint, data, timeout=None):
        self._sent_xfers.append(('write', endpoint, data))

    def ctrl_transfer(self, bmRequestType, bRequest, wValue=0, wIndex=0,
                      data_or_wLength=None, timeout=None):
        self._sent_xfers.append(('ctrl_transfer', bmRequestType, bRequest,
                                 wValue, wIndex, data_or_wLength))

    def _reset_sent(self):
        self._sent_xfers = deque()

class CorsairAsetekProDriverTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_usb = _MockAsetekProDevice()
        self.device = CorsairAsetekProDriver(self.mock_usb, 'Mock Corsair Asetek Pro Driver')
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """A few reasonable example calls do not raise exceptions."""
        self.device.initialize()
        self.device.get_status()
        self.device.set_color(channel='led', mode='blinking', colors=iter([[3, 2, 1]]),
                       time_per_color=3, time_off=1, alert_threshold=42,
                       alert_color=[90, 80, 10])
        self.device.set_color(channel='led', mode='rainbow', colors=[], speed=2)
        self.device.set_speed_profile(channel='fan',
                               profile=iter([(20, 20), (30, 50), (40, 100)]))
        self.device.set_speed_profile(channel='fan2',
                               profile=iter([(20, 20), (30, 50), (40, 100)]))
        self.device.set_fixed_speed(channel='pump', duty=50)

    def test_setting_speed_on_single_fan_3(self):
        self.device.initialize()
        self.device.set_fixed_speed('fan3', 100)
        _begin, fan2_message = self.mock_usb._sent_xfers
        assert fan2_message == ('write', 1, [0x40, 0x02, 0x00, 0x3b, 0x3c, 0x3c, 0x3c,
            0x3c, 0x3c, 0x64, 0x64, 0x64, 0x64, 0x64, 0x64, 0x64])
