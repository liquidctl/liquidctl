import unittest
from liquidctl.driver.kraken2 import Kraken2
from _testutils import MockHidapiDevice


class _MockKraken(MockHidapiDevice):
    def __init__(self, fw_version):
        super().__init__(vendor_id=0xffff, product_id=0x1e71)
        self.fw_version = fw_version
        self.temperature = 30.9
        self.fan_speed = 1499
        self.pump_speed = 2702

    def read(self, length):
        pre = super().read(length)
        if pre:
            return pre
        buf = bytearray(64)
        buf[1:3] = divmod(int(self.temperature * 10), 10)
        buf[3:5] = self.fan_speed.to_bytes(length=2, byteorder='big')
        buf[5:7] = self.pump_speed.to_bytes(length=2, byteorder='big')
        major, minor, patch = self.fw_version
        buf[0xb] = major
        buf[0xc:0xe] = minor.to_bytes(length=2, byteorder='big')
        buf[0xe] = patch
        return buf[:length]


class _TestCase(unittest.TestCase):
    def _prepare(self):
        raise NotImplementedError

    def setUp(self):
        self._prepare()
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()


class CurrentX2TestCase(_TestCase):
    def _prepare(self):
        self.mock_hid = _MockKraken(fw_version=(6, 0, 2))
        self.device = Kraken2(self.mock_hid, 'Mock X62', device_type=Kraken2.DEVICE_KRAKENX)

    def test_get_status(self):
        fan, fw_ver, temp, pump = sorted(self.device.get_status())
        self.assertEqual(fw_ver[1], '%d.%d.%d' % self.mock_hid.fw_version)
        self.assertAlmostEqual(temp[1], self.mock_hid.temperature, places=1)
        self.assertEqual(fan[1], self.mock_hid.fan_speed)
        self.assertEqual(pump[1], self.mock_hid.pump_speed)

    def test_not_totally_broken(self):
        """Reasonable example calls to untested APIs do not raise exceptions."""
        self.device.initialize()
        self.device.set_color(channel='ring', mode='loading', colors=iter([[90, 80, 0]]),
                              speed='slowest')
        self.device.set_speed_profile(channel='fan',
                                      profile=iter([(20, 20), (30, 40), (40, 100)]))
        self.device.set_fixed_speed(channel='pump', duty=50)
        self.device.set_instantaneous_speed(channel='pump', duty=50)


class OldX2WithoutProfilesTestCase(_TestCase):
    def _prepare(self):
        self.mock_hid = _MockKraken(fw_version=(2, 5, 8))
        self.device = Kraken2(self.mock_hid, 'Mock X62', device_type=Kraken2.DEVICE_KRAKENX)

    def test_set_fixed_speeds(self):
        self.device.set_fixed_speed(channel='fan', duty=42)
        self.device.set_fixed_speed(channel='pump', duty=84)
        fan_report, pump_report = self.mock_hid.sent
        self.assertEqual(fan_report.number, 2)
        self.assertEqual(fan_report.data[0:4], [0x4d, 0, 0, 42])
        self.assertEqual(pump_report.number, 2)
        self.assertEqual(pump_report.data[0:4], [0x4d, 0x40, 0, 84])

    def test_speed_profiles_not_supported(self):
        self.assertRaises(Exception, self.device.set_speed_profile, 'fan', [(20, 42)])
        self.assertRaises(Exception, self.device.set_speed_profile, 'pump', [(20, 84)])


class M22TestCase(_TestCase):
    def _prepare(self):
        self.mock_hid = _MockKraken(fw_version=(6, 0, 2))
        self.device = Kraken2(self.mock_hid, 'Mock M22', device_type=Kraken2.DEVICE_KRAKENM)

    def test_get_status(self):
        (fw_ver,) = self.device.get_status()
        self.assertEqual(fw_ver[1], '%d.%d.%d' % self.mock_hid.fw_version)

    def test_speed_control_not_supported(self):
        self.assertRaises(Exception, self.device.set_fixed_speed, 'fan', 42)
        self.assertRaises(Exception, self.device.set_fixed_speed, 'pump', 84)
        self.assertRaises(Exception, self.device.set_speed_profile, 'fan', [(20, 42)])
        self.assertRaises(Exception, self.device.set_speed_profile, 'pump', [(20, 84)])

    def test_not_totally_broken(self):
        """Reasonable example calls to untested APIs do not raise exceptions."""
        self.device.initialize()
        self.device.set_color(channel='ring', mode='loading', colors=iter([[90, 80, 0]]),
                              speed='slowest')
