# uses the psf/black style

import pytest
from _testutils import MockPyusbDevice, Report

from liquidctl.driver.krakenz3 import KrakenZ3
from liquidctl.driver.krakenz3 import (
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
def mock_krakenz3():
    raw = MockKraken(raw_led_channels=len(_COLOR_CHANNELS_KRAKENZ))
    dev = KrakenZ3(
        raw,
        "Mock Kraken Z53",
        speed_channels=_SPEED_CHANNELS_KRAKENZ,
        color_channels=_COLOR_CHANNELS_KRAKENZ,
    )

    dev.connect()
    return dev

class MockKraken(MockPyusbDevice):
    def __init__(self, raw_led_channels):
        super().__init__()
        self.raw_led_channels = raw_led_channels
        self.vendor_id = 0x1E71
        self.product_id = 0x3008

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


def test_krakenz3_initializes(mock_krakenz3):

    # TODO check the result
    _ = mock_krakenz3.initialize()

    writes = len(mock_krakenz3.device.sent)
    assert writes == 4


def test_krakenx3_reads_status_directly(mock_krakenz3):

    mock_krakenz3.device.preload_read(Report(0, SAMPLE_STATUS))

    temperature, pump_speed, pump_duty = mock_krakenz3.get_status()

    assert temperature == ("Liquid temperature", 33.1, "°C")
    assert pump_speed == ("Pump speed", 1704, "rpm")
    assert pump_duty == ("Pump duty", 53, "%")


def test_krakenx3_warns_on_faulty_temperature(mock_krakenz3, caplog):
    mock_krakenz3.device.preload_read(Report(0, FAULTY_STATUS))

    _ = mock_krakenz3.get_status()
    assert "unexpected temperature reading" in caplog.text


def test_krakenz3_not_totally_broken(mock_krakenz3):
    """Reasonable example calls to untested APIs do not raise exceptions."""
    mock_krakenz3.initialize()
    mock_krakenz3.set_color(channel="ring", mode="fixed", colors=iter([[3, 2, 1]]), speed="fastest")
    mock_krakenz3.set_speed_profile(channel="pump", profile=iter([(20, 20), (30, 50), (40, 100)]))
    mock_krakenz3.set_fixed_speed(channel="pump", duty=50)
