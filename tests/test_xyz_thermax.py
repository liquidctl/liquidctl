# uses the psf/black style

import pytest
from _testutils import MockHidapiDevice

from liquidctl.driver.xyz_thermax import XyzThermax


@pytest.fixture
def mock_thermax():
    device = MockHidapiDevice(vendor_id=0x5131, product_id=0x2007, address="addr")
    dev = XyzThermax(device, "mock XYZ Thermax display")
    dev.connect()
    return dev


def test_initialize_does_not_touch_the_device(mock_thermax):
    assert mock_thermax.initialize() == []
    assert mock_thermax.device.sent == []


def test_get_status_is_empty(mock_thermax):
    assert mock_thermax.get_status() == []
    assert mock_thermax.device.sent == []


def test_set_screen_celsius_cpu_only(mock_thermax):
    mock_thermax.set_screen("lcd", "celsius", "54")

    (report,) = mock_thermax.device.sent
    assert report.number == 0x00
    assert len(report.data) == 64
    assert report.data[0] == 0x40
    assert report.data[1] == 54
    assert report.data[9] == 0
    assert report.data[29] == (0x40 + 54) & 0xFF
    assert not any(report.data[2:9]) and not any(report.data[10:29]) and not any(report.data[30:])


def test_set_screen_cpu_and_gpu(mock_thermax):
    mock_thermax.set_screen("lcd", "celsius", "54,49")

    (report,) = mock_thermax.device.sent
    assert report.data[1] == 54
    assert report.data[9] == 49
    assert report.data[29] == 0xA7  # 0x40 + 0x36 + 0x31


def test_set_screen_fahrenheit_sends_celsius_with_flag(mock_thermax):
    mock_thermax.set_screen("lcd", "fahrenheit", "54,49")

    (report,) = mock_thermax.device.sent
    assert report.data[1] == 54 | 0x80
    assert report.data[9] == 49 | 0x80
    assert report.data[29] == (0x40 + (54 | 0x80) + (49 | 0x80)) & 0xFF


@pytest.mark.parametrize("value", ["", "hot", "-1", "128", "1,2,3", "40,"])
def test_set_screen_rejects_bad_values(mock_thermax, value):
    with pytest.raises(ValueError):
        mock_thermax.set_screen("lcd", "celsius", value)
    assert mock_thermax.device.sent == []


def test_set_screen_rejects_bad_channel_and_mode(mock_thermax):
    with pytest.raises(ValueError):
        mock_thermax.set_screen("display", "celsius", "40")
    with pytest.raises(ValueError):
        mock_thermax.set_screen("lcd", "kelvin", "40")
    assert mock_thermax.device.sent == []
