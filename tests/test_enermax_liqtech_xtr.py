# Copyright 2024  liquidctl contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from liquidctl.driver.enermax_liqtech_xtr import EnermaxLiqtechXtr
from liquidctl.error import NotSupportedByDriver
from tests._testutils import MockHidapiDevice

# Report-buffer constants (matching the driver source)
REPORT_ID = 0x20


def _decode_field(report, offset):
    """Return the 16-bit big-endian value at buf[offset:offset+2], where
    buf[0] is the report ID and report.data starts at buf[1].
    """
    data_off = offset - 1
    return (report.data[data_off] << 8) | report.data[data_off + 1]


@pytest.fixture
def device():
    mock = MockHidapiDevice(vendor_id=0x2e3c, product_id=0x0a12, address='addr')
    drv = EnermaxLiqtechXtr(mock, 'Enermax Liqtech XTR')
    drv.connect()
    return drv


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------

class TestInitialize:
    def test_returns_device_description(self, device):
        result = device.initialize()
        assert result == [('Device', 'Enermax Liqtech XTR', '')]

    def test_writes_zero_to_all_fields(self, device):
        device.device.sent.clear()
        device.initialize()
        # 4 writes: cpu (0x01), cpu2 (0x02), gpu (0x04), pump (0x10)
        assert len(device.device.sent) == 4
        cmds = {r.data[0] for r in device.device.sent}
        assert cmds == {0x01, 0x02, 0x04, 0x10}

    def test_all_writes_use_report_id_0x20(self, device):
        device.device.sent.clear()
        device.initialize()
        for r in device.device.sent:
            assert r.number == REPORT_ID

    def test_all_field_values_are_zero(self, device):
        device.device.sent.clear()
        device.initialize()
        for r in device.device.sent:
            # Every byte after the command byte must be 0x00
            assert all(b == 0 for b in r.data[1:]), f'non-zero bytes in report cmd=0x{r.data[0]:02x}'


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_returns_empty_list(self, device):
        assert device.get_status() == []

    def test_does_not_write_to_device(self, device):
        device.device.sent.clear()
        device.get_status()
        assert device.device.sent == []


# ---------------------------------------------------------------------------
# set_screen — CPU channel
# ---------------------------------------------------------------------------

class TestSetScreenCpu:
    def test_cpu_writes_two_reports(self, device):
        device.device.sent.clear()
        device.set_screen('cpu', 'temperature', 45)
        assert len(device.device.sent) == 2

    def test_cpu_primary_field_cmd(self, device):
        device.device.sent.clear()
        device.set_screen('cpu', 'temperature', 45)
        primary = next(r for r in device.device.sent if r.data[0] == 0x01)
        assert _decode_field(primary, 5) == 45

    def test_cpu_secondary_field_cmd(self, device):
        device.device.sent.clear()
        device.set_screen('cpu', 'temperature', 45)
        secondary = next(r for r in device.device.sent if r.data[0] == 0x02)
        assert _decode_field(secondary, 6) == 45

    def test_cpu_both_reports_use_report_id_0x20(self, device):
        device.device.sent.clear()
        device.set_screen('cpu', 'temperature', 45)
        for r in device.device.sent:
            assert r.number == REPORT_ID

    def test_cpu_value_zero(self, device):
        device.device.sent.clear()
        device.set_screen('cpu', 'temperature', 0)
        primary = next(r for r in device.device.sent if r.data[0] == 0x01)
        assert _decode_field(primary, 5) == 0

    def test_cpu_value_max(self, device):
        device.device.sent.clear()
        device.set_screen('cpu', 'temperature', 9999)
        primary = next(r for r in device.device.sent if r.data[0] == 0x01)
        assert _decode_field(primary, 5) == 9999

    def test_cpu_channel_case_insensitive(self, device):
        device.device.sent.clear()
        device.set_screen('CPU', 'temperature', 55)
        assert len(device.device.sent) == 2


# ---------------------------------------------------------------------------
# set_screen — GPU channel
# ---------------------------------------------------------------------------

class TestSetScreenGpu:
    def test_gpu_writes_one_report(self, device):
        device.device.sent.clear()
        device.set_screen('gpu', 'temperature', 2065)
        assert len(device.device.sent) == 1

    def test_gpu_cmd_byte(self, device):
        device.device.sent.clear()
        device.set_screen('gpu', 'temperature', 2065)
        r = device.device.sent[0]
        assert r.data[0] == 0x04

    def test_gpu_value_offset(self, device):
        device.device.sent.clear()
        device.set_screen('gpu', 'temperature', 2065)
        assert _decode_field(device.device.sent[0], 8) == 2065

    def test_gpu_id_encoding_b70_1(self, device):
        """GPU #1 at 57 °C → 1057."""
        device.device.sent.clear()
        device.set_screen('gpu', 'temperature', 1057)
        assert _decode_field(device.device.sent[0], 8) == 1057

    def test_gpu_id_encoding_nvidia(self, device):
        """GPU #9 (3080) at 72 °C → 9072."""
        device.device.sent.clear()
        device.set_screen('gpu', 'temperature', 9072)
        assert _decode_field(device.device.sent[0], 8) == 9072

    def test_gpu_report_id(self, device):
        device.device.sent.clear()
        device.set_screen('gpu', 'temperature', 50)
        assert device.device.sent[0].number == REPORT_ID


# ---------------------------------------------------------------------------
# set_screen — PUMP channel
# ---------------------------------------------------------------------------

class TestSetScreenPump:
    def test_pump_writes_one_report(self, device):
        device.device.sent.clear()
        device.set_screen('pump', 'rpm', 2900)
        assert len(device.device.sent) == 1

    def test_pump_cmd_byte(self, device):
        device.device.sent.clear()
        device.set_screen('pump', 'rpm', 2900)
        assert device.device.sent[0].data[0] == 0x10

    def test_pump_value_offset(self, device):
        device.device.sent.clear()
        device.set_screen('pump', 'rpm', 2900)
        assert _decode_field(device.device.sent[0], 11) == 2900

    def test_pump_report_id(self, device):
        device.device.sent.clear()
        device.set_screen('pump', 'rpm', 2900)
        assert device.device.sent[0].number == REPORT_ID


# ---------------------------------------------------------------------------
# set_screen — report length
# ---------------------------------------------------------------------------

class TestReportLength:
    def test_report_is_65_bytes_total(self, device):
        """Report ID + 64 data bytes = 65 total."""
        device.device.sent.clear()
        device.set_screen('cpu', 'temperature', 40)
        for r in device.device.sent:
            # MockHidapiDevice stores report.data = buf[1:], so data length = 64
            assert len(r.data) == 64

    def test_non_value_bytes_are_zero(self, device):
        """All bytes except the command byte and the two value bytes must be 0x00."""
        device.device.sent.clear()
        device.set_screen('pump', 'rpm', 2900)
        r = device.device.sent[0]
        # cmd=0x10, value at data[10:12] (offset 11-12 in full buf)
        for i, b in enumerate(r.data):
            if i == 0:       # command byte
                assert b == 0x10
            elif i in (10, 11):  # value bytes
                pass  # checked separately
            else:
                assert b == 0, f'data[{i}] = 0x{b:02x}, expected 0x00'


# ---------------------------------------------------------------------------
# set_screen — validation
# ---------------------------------------------------------------------------

class TestSetScreenValidation:
    def test_unknown_channel_raises(self, device):
        with pytest.raises(ValueError, match='unknown channel'):
            device.set_screen('fan', 'rpm', 1000)

    def test_unknown_mode_raises(self, device):
        with pytest.raises(ValueError, match='unknown mode'):
            device.set_screen('cpu', 'duty', 50)

    def test_value_below_zero_raises(self, device):
        with pytest.raises(ValueError, match='out of range'):
            device.set_screen('cpu', 'temperature', -1)

    def test_value_above_9999_raises(self, device):
        with pytest.raises(ValueError, match='out of range'):
            device.set_screen('gpu', 'temperature', 10000)

    def test_value_exactly_zero_is_valid(self, device):
        device.set_screen('pump', 'rpm', 0)  # must not raise

    def test_value_exactly_9999_is_valid(self, device):
        device.set_screen('gpu', 'temperature', 9999)  # must not raise


# ---------------------------------------------------------------------------
# Unsupported methods
# ---------------------------------------------------------------------------

class TestUnsupportedMethods:
    def test_set_color_raises(self, device):
        with pytest.raises(NotSupportedByDriver):
            device.set_color('led', 'static', [(255, 0, 0)])

    def test_set_fixed_speed_raises(self, device):
        with pytest.raises(NotSupportedByDriver):
            device.set_fixed_speed('pump', 50)

    def test_set_speed_profile_raises(self, device):
        with pytest.raises(NotSupportedByDriver):
            device.set_speed_profile('pump', [(20, 50), (40, 80)])
