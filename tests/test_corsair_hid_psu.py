import unittest
from liquidctl.driver.corsair_hid_psu import CorsairHidPsu
from liquidctl.driver.corsair_hid_psu import _CORSAIR_12V_OCP_MODE
from liquidctl.driver.corsair_hid_psu import _CORSAIR_FAN_CONTROL_MODE
from _testutils import MockHidapiDevice, Report


class _MockPsuDevice(MockHidapiDevice):
    def write(self, data):
        super().write(data)
        data = data[1:]  # skip unused report ID

        reply = bytearray(64)
        if data[1] in [_CORSAIR_12V_OCP_MODE, _CORSAIR_FAN_CONTROL_MODE]:
            reply[2] = 1  # just a valid mode
        self.preload_read(Report(0, reply))


class CorsairHidPsuTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_hid = _MockPsuDevice()
        self.device = CorsairHidPsu(self.mock_hid, 'Mock Corsair HID PSU')
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """A few reasonable example calls do not raise exceptions."""
        self.device.initialize()
        self.device.get_status()

    def test_dont_inject_report_ids(self):
        self.device.set_fixed_speed(channel='fan', duty=50)
        report_id, report_data = self.mock_hid.sent[0]
        assert report_id == 0
        assert len(report_data) == 64
