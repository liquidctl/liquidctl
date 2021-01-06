"""Test the use of APIs from liquidctl v1.0.0.

While at the time all APIs were undocumented, we choose to support the use
cases from GKraken as that software is a substantial contribution to the
community.
"""

import pytest
from liquidctl.driver.kraken_two import KrakenTwoDriver
from liquidctl.version import __version__
from _testutils import MockHidapiDevice

SPECTRUM = [
    (235, 77, 40),
    (255, 148, 117),
    (126, 66, 45),
    (165, 87, 0),
    (56, 193, 66),
    (116, 217, 170),
    (166, 158, 255),
    (208, 0, 122)
]


@pytest.fixture
def mockDevice():
    device = MockHidapiDevice()
    dev = KrakenTwoDriver(device, 'Mock X62',
                                  device_type=KrakenTwoDriver.DEVICE_KRAKENX)

    dev.connect()
    return dev


def test_pre11_apis_find_does_not_raise():
    import liquidctl.cli
    liquidctl.cli.find_all_supported_devices()


def test_pre11_apis_connect_as_initialize(mockDevice):
    # deprecated behavior in favor of connect()
    mockDevice.initialize()


def test_pre11_apis_deprecated_super_mode(mockDevice):
    # deprecated in favor of super-fixed, super-breathing and super-wave
    mockDevice.set_color('sync', 'super', [(128, 0, 255)] + SPECTRUM, 'normal')


def test_pre11_apis_status_order(mockDevice):
    # GKraken unreasonably expects a particular ordering
    pass


def test_pre11_apis_finalize_as_connect_or_noop(mockDevice):
    # deprecated in favor of disconnect()
    mockDevice.finalize()  # should disconnect
    mockDevice.finalize()  # should be a no-op
