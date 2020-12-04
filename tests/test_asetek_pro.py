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

        self._reset()

    def read(self, endpoint, length, timeout=None):
        if len(self._responses):
            return self._responses.popleft()
        return [0] * length

    def write(self, endpoint, data, timeout=None):
        self._sent_xfers.append(('write', endpoint, data))

    def ctrl_transfer(self, bmRequestType, bRequest, wValue=0, wIndex=0,
                      data_or_wLength=None, timeout=None):
        self._sent_xfers.append(('ctrl_transfer', bmRequestType, bRequest,
                                 wValue, wIndex, data_or_wLength))

    def _reset(self):
        self._sent_xfers = deque()
        self._responses = deque()

class CorsairAsetekProDriverTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_usb = _MockAsetekProDevice()
        self.device = CorsairAsetekProDriver(self.mock_usb, 'Mock Corsair Asetek Pro Driver',
            fan_count=2)
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """A few reasonable example calls do not raise exceptions."""
        self.device.initialize()
        self.device.get_status()
        self.device.set_color(channel='pump', mode='blinking', colors=iter([[3, 2, 1]]))
        self.device.set_color(channel='pump', mode='rainbow', colors=[], speed='normal')
        self.device.set_speed_profile(channel='fan',
                               profile=iter([(20, 20), (30, 50), (40, 100)]))
        self.device.set_speed_profile(channel='fan1',
                               profile=iter([(20, 20), (30, 50), (40, 100)]))
        self.device.set_fixed_speed(channel='fan', duty=50)

    def test_initialize_with_pump_mode(self):
        self.device.initialize(pump_mode='BaLanced')
        _begin, set_pump = self.mock_usb._sent_xfers
        assert set_pump == ('write', 1, [0x32, 0x01])

    def test_set_profile_of_all_fans(self):
        # When setting the speed of all fans the driver first gets the speed of all fans
        # to work out how many fans are present. Set 2 valid responses to simulate a setup
        # with 2 fans present.
        # The first response is for the pump setup in the initialize function
        self.device.initialize()
        self.device.set_speed_profile(channel='fan', profile=[(0, 10), (25, 50), (40, 100)])
        _begin, _set_pump, set_fan_1, set_fan_2 = self.mock_usb._sent_xfers
        assert set_fan_1 == ('write', 1, [0x40, 0x00, 0x00, 0x19, 0x28, 0x3c, 0x3c, 0x3c, 0x3c,
            0x0a, 0x32, 0x64, 0x64, 0x64, 0x64, 0x64])
        assert set_fan_2 == ('write', 1, [0x40, 0x01, 0x00, 0x19, 0x28, 0x3c, 0x3c, 0x3c, 0x3c,
            0x0a, 0x32, 0x64, 0x64, 0x64, 0x64, 0x64])

    def test_setting_speed_on_single_fan_2(self):
        self.device.initialize()
        self.device.set_fixed_speed('fan2', 100)
        _begin, _set_pump, fan2_message = self.mock_usb._sent_xfers
        assert fan2_message == ('write', 1, [0x42, 0x01, 0x64])

    def test_set_pump_to_rainbow_mode(self):
        self.device.initialize()
        self.device.set_color(channel='pump', mode='rainbow', colors=iter([]), speed='slower')
        _begin, _set_pump, color_mode_message, end_message = self.mock_usb._sent_xfers
        assert color_mode_message == ('write', 1, [0x53, 0x30])
        assert end_message == ('write', 1, [0x55, 0x01])

    def test_set_pump_to_fixed_color(self):
        self.device.initialize()
        self.device.set_color(channel='pump', mode='fixed', colors=iter([[0xff, 0x88, 0x44]]))
        _begin, _set_pump, color_change_message, end_message = self.mock_usb._sent_xfers
        assert color_change_message == ('write', 1, [0x56, 0x02, 0xff, 0x88, 0x44, 0xff, 0x88, 0x44])
        assert end_message == ('write', 1, [0x55, 0x01])

    def test_set_pump_to_blinking_mode(self):
        self.device.initialize()
        self.device.set_color(channel='pump', mode='blinking', speed='normal',
            colors=iter([[0xff, 0x88, 0x44], [0xff, 0xff, 0xff], [0x00, 0x00, 0x00]]))
        _begin, _set_pump, color_change_message, color_mode_message, end_message = self.mock_usb._sent_xfers
        assert color_change_message == ('write', 1, [0x56, 0x03, 0xff, 0x88, 0x44, 0xff, 0xff, 0xff,
            0x00, 0x00, 0x00])
        assert color_mode_message == ('write', 1, [0x53, 0x0A])
        assert end_message == ('write', 1, [0x58, 0x01])
