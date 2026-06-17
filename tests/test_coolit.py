import logging

import pytest

from _testutils import MockHidapiDevice, MockRuntimeStorage
from liquidctl.driver.coolit import Coolit

# Command bytes the variant-detection probes read back (see _DetectMockDevice).
_CMD_DEVICE_TYPE = 0x00
_CMD_TEMP_COUNT = 0x0D
_CMD_FAN_COUNT = 0x11


class MockDevice(MockHidapiDevice):
    def read(self, length, **kwargs):
        return [0] * length


class _DetectMockDevice(MockHidapiDevice):
    """Answers the READ_ONE probes _detect_variant() issues, keyed by command.

    Detection reads DEVICE_TYPE, then FAN_COUNT and TEMP_COUNT_SENSORS; each
    READ_ONE response carries its data byte at index 2. Commands without an
    answer (e.g. the unknown-variant firmware/name probes) read back zero.
    """

    def __init__(self, *, type_byte, fan_slots, temp_count, **kwargs):
        super().__init__(**kwargs)
        self._answers = {
            _CMD_DEVICE_TYPE: type_byte,
            _CMD_FAN_COUNT: fan_slots,
            _CMD_TEMP_COUNT: temp_count,
        }

    def read(self, length, **kwargs):
        buf = [0] * length
        if self.sent:
            buf[2] = self._answers.get(self.sent[-1].data[2], 0)
        return buf


def _detected(type_byte, fan_slots, temp_count):
    """Build a Coolit that auto-detects the given variant fingerprint."""
    raw = _DetectMockDevice(
        vendor_id=0xDEAD,
        product_id=0xBEEF,
        address="50",
        type_byte=type_byte,
        fan_slots=fan_slots,
        temp_count=temp_count,
    )
    storage = MockRuntimeStorage(key_prefixes=[f"detect_{type_byte:02x}"])
    return Coolit(raw, "Autodetect").connect(runtime_storage=storage)


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
_WRITE_TWO = 0x08
_READ_TWO = 0x09
_FAN_SELECT = 0x10
_FAN_FIXED_RPM = 0x14
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
        and r.data[1] == _WRITE_ONE
        and r.data[2] == _FAN_SELECT
        and r.data[5] == _READ_TWO
        and r.data[6] == _FAN_MAX_RPM
    ]


def _pump_fixed_rpm_params(sent):
    """FAN_SELECT params paired with a FAN_FIXED_RPM write in the same report."""
    return [
        r.data[3]
        for r in sent
        if len(r.data) >= 7
        and r.data[1] == _WRITE_ONE
        and r.data[2] == _FAN_SELECT
        and r.data[5] == _WRITE_TWO
        and r.data[6] == _FAN_FIXED_RPM
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


def test_connect_applies_known_no_pump_variant():
    """A recognized no-pump type byte configures the matching variant."""
    dev = _detected(0x3D, fan_slots=6, temp_count=4)
    assert dev._description == "Corsair Commander Mini"
    assert dev._has_pump is False
    assert dev._pump_index == 0
    assert dev._fan_count == 6
    assert dev._temp_count == 4


def test_connect_applies_known_pump_variant():
    """A recognized pump type byte sets pump_index and reserves a fan slot."""
    # 0x42 counts its pump within FAN_COUNT, so fan_count = fan_slots - 1.
    dev = _detected(0x42, fan_slots=3, temp_count=1)
    assert "H110i" in dev._description
    assert dev._has_pump is True
    assert dev._pump_index == 2
    assert dev._fan_count == 2
    assert dev._temp_count == 1


def test_connect_unknown_variant_falls_back_to_no_pump(caplog):
    """An unknown type byte stays pump-free and logs an actionable warning."""
    with caplog.at_level(logging.WARNING):
        dev = _detected(0x99, fan_slots=4, temp_count=2)
    assert dev._has_pump is False
    assert dev._pump_index == 0
    assert dev._fan_count == 4
    assert dev._temp_count == 2
    assert "unknown" in caplog.text.lower()
    assert "0x99" in caplog.text


def test_no_pump_variant_never_writes_pump_fixed_rpm(mock_commander_mini):
    """Setting fans on a pump-free variant must not emit a pump RPM write."""
    controller = mock_commander_mini
    controller.set_fixed_speed("fan", 50)
    assert _pump_fixed_rpm_params(controller.device.sent) == []


def test_pump_variant_writes_fixed_rpm_to_configured_index(mock_h110i_gt):
    """The pump RPM write must select the variant's configured pump index."""
    cooler = mock_h110i_gt
    cooler.set_fixed_speed("fan1", 50)
    assert _pump_fixed_rpm_params(cooler.device.sent) == [2]
