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
        "Mock H110i GT",
        has_pump=True,
        fan_count=2,
        temp_count=1,
        rgb_fans=False,
    )
    return dev.connect(runtime_storage=mock_storage)


@pytest.fixture
def mock_commander_mini():
    mock_raw_dev = MockDevice(vendor_id=0xDEAD, product_id=0xBEEF, address="43")
    mock_storage = MockRuntimeStorage(key_prefixes=["mock_commander_mini"])
    dev = Coolit(
        mock_raw_dev,
        "Mock Commander Mini",
        has_pump=False,
        fan_count=6,
        temp_count=4,
        rgb_fans=False,
    )
    return dev.connect(runtime_storage=mock_storage)


def test_driver_not_totally_broken(mock_h110i_gt):
    cooler = mock_h110i_gt
    cooler.initialize()
    _ = cooler.get_status(pump_mode="extreme")
    cooler.set_fixed_speed("fan1", 42)
    cooler.set_speed_profile("fan2", [(20, 30), (40, 90)])


def test_commander_mini_not_totally_broken(mock_commander_mini):
    controller = mock_commander_mini
    controller.initialize()
    status = controller.get_status()
    # 6 fan rows shown, no pump row, no temp rows (mock returns all zeros so
    # the disconnected-sentinel hides nothing here, but bare minimum: no crash
    # and the right structural shape).
    labels = [row[0] for row in status]
    assert "Pump speed" not in labels
    assert sum(1 for label in labels if label.startswith("Fan ")) == 6
    controller.set_fixed_speed("fan6", 75)
    controller.set_speed_profile("fan", [(20, 30), (40, 90)])
