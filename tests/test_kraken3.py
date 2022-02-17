# uses the psf/black style

import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.kraken3 import KrakenX3, KrakenZ3
from liquidctl.driver.kraken3 import (
    _COLOR_CHANNELS_KRAKENX,
    _SPEED_CHANNELS_KRAKENX,
    _COLOR_CHANNELS_KRAKENZ,
    _SPEED_CHANNELS_KRAKENZ,
)
from liquidctl.util import HUE2_MAX_ACCESSORIES_IN_CHANNEL as MAX_ACCESSORIES
from liquidctl.util import Hue2Accessory


# https://github.com/liquidctl/liquidctl/issues/160#issuecomment-664044103
SAMPLE_STATUS = bytes.fromhex(
    "7502200036000B51535834353320012101A80635350000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)
# https://github.com/liquidctl/liquidctl/issues/160#issue-665781804
FAULTY_STATUS = bytes.fromhex(
    "7502200036000B5153583435332001FFFFCC0A64640000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)


@pytest.fixture
def mock_krakenx3():
    raw = MockKraken(raw_led_channels=len(_COLOR_CHANNELS_KRAKENX) - 1)
    dev = KrakenX3(
        raw,
        "Mock Kraken X73",
        speed_channels=_SPEED_CHANNELS_KRAKENX,
        color_channels=_COLOR_CHANNELS_KRAKENX,
    )

    dev.connect()
    return dev


@pytest.fixture
def mock_krakenz3():
    raw = MockKraken(raw_led_channels=1)
    dev = KrakenZ3(
        raw,
        "Mock Kraken Z73",
        speed_channels=_SPEED_CHANNELS_KRAKENZ,
        color_channels=_COLOR_CHANNELS_KRAKENZ,
    )

    dev.connect()
    return dev


class MockKraken(MockHidapiDevice):
    def __init__(self, raw_led_channels):
        super().__init__()
        self.raw_led_channels = raw_led_channels

    def write(self, data):
        reply = bytearray(64)
        if data[0:2] == [0x10, 0x01]:
            reply[0:2] = [0x11, 0x01]
        elif data[0:2] == [0x20, 0x03]:
            reply[0:2] = [0x21, 0x03]
            reply[14] = self.raw_led_channels
            if self.raw_led_channels > 1:
                reply[15 + 1 * MAX_ACCESSORIES] = Hue2Accessory.KRAKENX_GEN4_RING.value
                reply[15 + 2 * MAX_ACCESSORIES] = Hue2Accessory.KRAKENX_GEN4_LOGO.value
        self.preload_read(Report(0, reply))
        return super().write(data)


def test_krakenx3_parses_status_fields(mock_krakenx3):
    mock_krakenx3.device.preload_read(Report(0, SAMPLE_STATUS))

    temperature, pump_speed, pump_duty = mock_krakenx3.get_status()

    assert temperature == ("Liquid temperature", 33.1, "°C")
    assert pump_speed == ("Pump speed", 1704, "rpm")
    assert pump_duty == ("Pump duty", 53, "%")


def test_krakenx3_warns_if_faulty_temperature(mock_krakenx3, caplog):
    mock_krakenx3.device.preload_read(Report(0, FAULTY_STATUS))

    _ = mock_krakenx3.get_status()
    assert "unexpected temperature reading" in caplog.text


def test_krakenx3_not_totally_broken(mock_krakenx3):
    """Reasonable example calls to untested APIs do not raise exceptions."""
    mock_krakenx3.initialize()
    mock_krakenx3.set_color(channel="ring", mode="fixed", colors=iter([[3, 2, 1]]), speed="fastest")
    mock_krakenx3.set_speed_profile(channel="pump", profile=iter([(20, 20), (30, 50), (40, 100)]))
    mock_krakenx3.set_fixed_speed(channel="pump", duty=50)


def test_krakenz3_not_totally_broken(mock_krakenz3):
    """Reasonable example calls to untested APIs do not raise exceptions."""
    mock_krakenz3.initialize()
    mock_krakenz3.device.preload_read(Report(0, SAMPLE_STATUS))
    _ = mock_krakenz3.get_status()
    mock_krakenz3.set_speed_profile(channel="fan", profile=iter([(20, 20), (30, 50), (40, 100)]))
    mock_krakenz3.set_fixed_speed(channel="pump", duty=50)
