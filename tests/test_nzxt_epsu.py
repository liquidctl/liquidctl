import unittest
from liquidctl.driver.nzxt_epsu import NzxtEPsu
from liquidctl.driver.nzxt_epsu import _SEASONIC_READ_FIRMWARE_VERSION
from liquidctl.pmbus import CommandCode
from _testutils import MockHidapiDevice, Report


class _MockPsuDevice(MockHidapiDevice):
    def write(self, data):
        super().write(data)
        data = data[1:]  # skip unused report ID
        reply = bytearray(64)
        reply[0:2] = (0xaa, data[2])
        if data[5] == CommandCode.PAGE_PLUS_READ:
            reply[2] = data[2] - 2
        elif data[5] == _SEASONIC_READ_FIRMWARE_VERSION:
            reply[2:4] = (0x11, 0x41)
        self.preload_read(Report(0, reply[0:]))


class NzxtEPsuTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_hid = _MockPsuDevice()
        self.device = NzxtEPsu(self.mock_hid, 'Mock NZXT E PSU')
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_not_totally_broken(self):
        """A few reasonable example calls do not raise exceptions."""
        self.device.initialize()
        status = self.device.get_status()

        fw = next(filter(lambda x: x[0] == 'Firmware version', status))
        assert fw == ('Firmware version', 'A017/40983', '')

    def test_dont_inject_report_ids(self):
        status = self.device.get_status()
        get_fw = self.mock_hid.sent[0]
        assert get_fw == Report(0, [0xad, 0, 3, 1, 0x60, 0xfc] + 58*[0])

