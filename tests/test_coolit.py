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
    )
    return dev.connect(runtime_storage=mock_storage)


def test_driver_not_totally_broken(mock_h110i_gt):
    cooler = mock_h110i_gt
    cooler.initialize()
    _ = cooler.get_status(pump_mode="extreme")
    cooler.set_fixed_speed("fan1", 42)
    cooler.set_speed_profile("fan2", [(20, 30), (40, 90)])


# Protocol byte constants for inspecting recorded mock writes.
_WRITE_ONE = 0x06
_READ_TWO = 0x09
_FAN_SELECT = 0x10
_FAN_MAX_RPM = 0x17


def _fan_select_params(sent):
    """Every FAN_SELECT(write_one) parameter byte across all sent reports."""
    return [
        r.data[3]
        for r in sent
        if len(r.data) >= 4 and r.data[1] == _WRITE_ONE and r.data[2] == _FAN_SELECT
    ]


def _max_rpm_select_params(sent):
    """FAN_SELECT params paired with a FAN_MAX_RPM read in the same report."""
    return [
        r.data[3]
        for r in sent
        if len(r.data) >= 7
        and r.data[1] == _WRITE_ONE and r.data[2] == _FAN_SELECT
        and r.data[5] == _READ_TWO and r.data[6] == _FAN_MAX_RPM
    ]


def test_set_fixed_speed_addresses_every_fan_slot(mock_commander_mini):
    """All six fan slots must be addressable (regression for fan1/else hardcode)."""
    controller = mock_commander_mini
    controller.set_fixed_speed("fan", 50)
    assert set(_fan_select_params(controller.device.sent)) >= set(range(6))


def test_set_speed_profile_reads_max_rpm_for_target_fan(mock_commander_mini):
    """Custom-profile max-RPM read must select the target fan, not fan 0."""
    controller = mock_commander_mini
    controller.set_speed_profile("fan3", [(20, 30), (40, 90)])
    assert _max_rpm_select_params(controller.device.sent) == [2]


def test_temperature_rows_are_in_ascending_label_order(mock_commander_mini):
    """Temperature rows must be listed as 1, 2, 3, 4 (silkscreen order)."""
    controller = mock_commander_mini
    status = controller.get_status()
    temp_labels = [row[0] for row in status if row[0].startswith("Temperature ")]
    assert temp_labels == ["Temperature 1", "Temperature 2", "Temperature 3", "Temperature 4"]


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
