"""Test the use of APIs from liquidctl v1.0.0.

While at the time all APIs were undocumented, we choose to support the use
cases from GKraken as that software is a substantial contribution to the
community.
"""

import unittest
from liquidctl.driver.kraken_two import KrakenTwoDriver
from liquidctl.version import __version__
from _testutils import MockHidapiDevice

SPECTRUM = [
    (235,77,40),
    (255,148,117),
    (126,66,45),
    (165,87,0),
    (56,193,66),
    (116,217,170),
    (166,158,255),
    (208,0,122)
]


class Pre11CliApisUsedByGkraken(unittest.TestCase):
    def test_find_does_not_raise(self):
        import liquidctl.cli
        devices = liquidctl.cli.find_all_supported_devices()


class Pre11KrakenApisUsedByGkraken(unittest.TestCase):
    def setUp(self):
        self.mock_hid = MockHidapiDevice()
        self.device = KrakenTwoDriver(self.mock_hid, 'Mock X62',
                                      device_type=KrakenTwoDriver.DEVICE_KRAKENX)
        self.device.connect()

    def tearDown(self):
        self.device.disconnect()

    def test_connect_as_initialize(self):
        # deprecated behavior in favor of connect()
        self.device.initialize()

    def test_deprecated_super_mode(self):
        # deprecated in favor of super-fixed, super-breathing and super-wave
        self.device.set_color('sync', 'super', [(128,0,255)] + SPECTRUM, 'normal')

    def test_status_order(self):
        # GKraken unreasonably expects a particular ordering
        pass

    def test_finalize_as_connect_or_noop(self):
        # deprecated in favor of disconnect()
        self.device.finalize()  # should disconnect
        self.device.finalize()  # should be a no-op
