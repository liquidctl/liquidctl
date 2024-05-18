import pytest

from _testutils import MockHidapiDevice, MockRuntimeStorage
from liquidctl.driver.coolit import Coolit


class MockDevice(MockHidapiDevice):
    def read(self, length, **kwargs):
        return [0] * length


@pytest.fixture
def mock_h110i_gt():
    mock_raw_dev = MockDevice(vendor_id=0xDEAD, product_id=0xBEEF, address="42")
    mock_storage = MockRuntimeStorage(key_prefixes=["mock_h110i_gt"])
    dev = Coolit(
        mock_raw_dev,
        "Mock H100i GT",
        fan_count=2,
        rgb_fans=False,
    )
    return dev.connect(runtime_storage=mock_storage)


def test_driver_not_totally_broken(mock_h110i_gt):
    cooler = mock_h110i_gt
    cooler.initialize()
    _ = cooler.get_status(pump_mode="extreme")
    cooler.set_fixed_speed("fan1", 42)
    cooler.set_speed_profile("fan2", [(20, 30), (40, 90)])
