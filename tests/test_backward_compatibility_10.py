"""Test API backward compatibility with liquidctl 1.0.x.

While at the time all APIs were undocumented, we choose to support the use
cases from GKraken as that software is a substantial contribution to the
community.
"""

import pytest
from _testutils import MockHidapiDevice
from test_kraken2 import _MockKrakenDevice
from test_kraken2 import mockKrakenXDevice as mockConnectedDevice

from liquidctl.driver.kraken_two import KrakenTwoDriver
from liquidctl.version import __version__

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


def test_pre11_apis_find_does_not_raise():
    import liquidctl.cli
    liquidctl.cli.find_all_supported_devices()


def test_pre11_apis_deprecated_super_mode(mockConnectedDevice):
    # deprecated in favor of super-fixed, super-breathing and super-wave
    mockConnectedDevice.set_color('sync', 'super', [(128, 0, 255)] + SPECTRUM, 'normal')


def test_pre11_apis_status_order(mockConnectedDevice):
    # GKraken unreasonably expects a particular ordering
    pass


@pytest.fixture(params=[False, True], ids=['not connected', 'connected'])
def mockDevice(request):
    device = _MockKrakenDevice(fw_version=(6, 0, 2))
    dev = KrakenTwoDriver(device, 'Mock X62', device_type=KrakenTwoDriver.DEVICE_KRAKENX)

    if request.param:
        dev.connect()
    return dev


def test_pre11_apis_connect_with_initialize(mockDevice):
    # deprecated behavior in favor of connect()
    mockDevice.initialize()


def test_pre11_apis_disconnect_with_finalize(mockDevice):
    # deprecated in favor of disconnect()
    mockDevice.finalize()
