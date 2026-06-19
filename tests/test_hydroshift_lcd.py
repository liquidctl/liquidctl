import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver
from liquidctl.driver.hydroshift_lcd import HydroShiftLCD


@pytest.fixture
def mockHydroShift():
    device = MockHidapiDevice(vendor_id=0x0416, product_id=0x7398, address="addr")
    dev = HydroShiftLCD(device, "mock HydroShift LCD 360S")
    dev.connect()
    return dev


# -- firmware version response packets (64 bytes each) --
# Part 1: "N9,01,HS,SQ,HydroShift,V3.0C.013,1.3" (36 bytes, data_len=0x24)
_FW_REPORT_PART1 = bytes.fromhex(
    "0186000000244e392c30312c48532c53512c487964726f53686966742c56332e"
    "30432e3031332c312e3300000000000000000000000000000000000000000000"
)

# Part 2: "Oct 22 2024,10:39:15" (20 bytes, data_len=0x14, pkt_num=1)
_FW_REPORT_PART2 = bytes.fromhex(
    "0186000001144f637420323220323032342c31303a33393a313500000000000000"
    "000000000000000000000000000000000000000000000000000000000000000000"
)[:64]

# Handshake response: fan_rpm=1440 (0x05A0), pump_rpm=2670 (0x0A6E),
# temp_valid=1, temp_int=37 (0x25), temp_frac=8 -> 37.8C
_STATUS_REPORT = bytes.fromhex(
    "01810000000705a00a6e01250800000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
)


def _preload_fw_and_status(dev):
    """Preload firmware + handshake responses for initialize()."""
    dev.device.preload_read(Report(0, _FW_REPORT_PART1))
    dev.device.preload_read(Report(0, _FW_REPORT_PART2))
    dev.device.preload_read(Report(0, _STATUS_REPORT))


def test_initialize(mockHydroShift):
    _preload_fw_and_status(mockHydroShift)
    status = mockHydroShift.initialize()

    # Should have sent firmware query (0x86) and handshake (0x81)
    assert len(mockHydroShift.device.sent) == 2
    assert mockHydroShift.device.sent[0].data[0] == 0x86  # firmware query
    assert mockHydroShift.device.sent[1].data[0] == 0x81  # handshake

    # Check firmware version in status
    fw_entries = [s for s in status if s[0] == "Firmware version"]
    assert len(fw_entries) == 1

    # Check that C-command mode was detected (version 1.3 >= 1.2)
    assert mockHydroShift._use_c_cmd is True


def test_initialize_old_firmware(mockHydroShift):
    # Firmware version "1.1" -> should NOT use C-command
    fw_v1_1 = bytearray(64)
    fw_v1_1[0] = 0x01
    fw_v1_1[1] = 0x86
    fw_v1_1[5] = 3
    fw_v1_1[6:9] = b"1.1"

    fw_date = bytearray(64)
    fw_date[0] = 0x01
    fw_date[1] = 0x86
    fw_date[3] = 0x00
    fw_date[4] = 0x01
    fw_date[5] = 4
    fw_date[6:10] = b"date"

    mockHydroShift.device.preload_read(Report(0, bytes(fw_v1_1)))
    mockHydroShift.device.preload_read(Report(0, bytes(fw_date)))
    mockHydroShift.device.preload_read(Report(0, _STATUS_REPORT))
    mockHydroShift.initialize()

    assert mockHydroShift._use_c_cmd is False


def test_get_status(mockHydroShift):
    mockHydroShift._use_c_cmd = False
    mockHydroShift.device.preload_read(Report(0, _STATUS_REPORT))
    status = mockHydroShift.get_status()

    assert len(status) == 5

    temp = [s for s in status if s[0] == "Liquid temperature"][0]
    assert temp[1] == 37.8

    fan = [s for s in status if s[0] == "Fan speed"][0]
    assert fan[1] == 1440

    pump = [s for s in status if s[0] == "Pump speed"][0]
    assert pump[1] == 2670


def test_get_handshake_drops_stale_reports(mockHydroShift):
    # Regression: a leftover B/C-command response (report ID 0x02) sitting in
    # the HID input queue from a prior LCD operation must not be read in place
    # of the handshake reply, otherwise _read_a_cmd raises
    # ValueError('unexpected report ID: 0x02').
    mockHydroShift._use_c_cmd = False

    # Wire the mock's clear_enqueued_reports to actually drain the read queue.
    mockHydroShift.device.clear_enqueued_reports = mockHydroShift.device._read.clear

    # Stale report (B-command response, report ID 0x02) sitting in the queue.
    stale = bytearray(64)
    stale[0] = 0x02
    mockHydroShift.device.preload_read(Report(0, bytes(stale)))

    # Real handshake reply lands only after the handshake write goes out.
    real_write = mockHydroShift.device.write
    def write_then_respond(data):
        result = real_write(data)
        if data[1] == 0x81:  # _CMD_HANDSHAKE
            mockHydroShift.device.preload_read(Report(0, _STATUS_REPORT))
        return result
    mockHydroShift.device.write = write_then_respond

    handshake = mockHydroShift._get_handshake()

    assert handshake["fan_rpm"] == 1440
    assert handshake["pump_rpm"] == 2670
    assert handshake["temperature"] == 37.8


def test_set_fan_speed(mockHydroShift):
    mockHydroShift.set_fixed_speed(channel="fan", duty=50)
    report = mockHydroShift.device.sent[0]
    # Mock write stores Report(data[0], data[1:])
    # So report[0] = report.number = pkt[0] (report ID)
    #    report.data[N] = pkt[N+1]
    assert report[0] == 0x01       # report ID
    assert report.data[0] == 0x8B  # command byte (pkt[1])
    assert report.data[4] == 0x02  # data_len=2 (pkt[5])
    assert report.data[5] == 0x00  # first data byte (pkt[6])
    assert report.data[6] == 50    # PWM duty (pkt[7])


def test_set_pump_speed(mockHydroShift):
    mockHydroShift.set_fixed_speed(channel="pump", duty=75)
    report = mockHydroShift.device.sent[0]
    assert report[0] == 0x01
    assert report.data[0] == 0x8A  # pump PWM command
    assert report.data[6] == 75


def test_set_speed_clamped(mockHydroShift):
    mockHydroShift.set_fixed_speed(channel="fan", duty=150)
    report = mockHydroShift.device.sent[0]
    assert report.data[6] == 100

    mockHydroShift.device.sent.clear()
    mockHydroShift.set_fixed_speed(channel="fan", duty=-10)
    report = mockHydroShift.device.sent[0]
    assert report.data[6] == 0


def test_set_speed_invalid_channel(mockHydroShift):
    with pytest.raises(NotSupportedByDevice):
        mockHydroShift.set_fixed_speed(channel="invalid", duty=50)


def test_set_color_fan(mockHydroShift):
    mockHydroShift.set_color(
        channel="fan",
        mode="static",
        colors=[(0xFF, 0x00, 0x00), (0x00, 0xFF, 0x00)],
        speed="normal",
        direction="forward",
    )
    report = mockHydroShift.device.sent[0]
    assert report[0] == 0x01
    assert report.data[0] == 0x85  # fan light command (pkt[1])
    # report.data[5..24] = req[0..19] (the 20-byte payload starts at pkt[6])
    assert report.data[5] == 0x03  # static mode (req[0])
    assert report.data[6] == 0x04  # brightness max (req[1])
    assert report.data[7] == 0x02  # normal speed (req[2])

    # color 1: red (req[3:6])
    assert report.data[8] == 0xFF
    assert report.data[9] == 0x00
    assert report.data[10] == 0x00

    # color 2: green (req[6:9])
    assert report.data[11] == 0x00
    assert report.data[12] == 0xFF
    assert report.data[13] == 0x00

    assert report.data[24] == 24  # LED count (req[19])


def test_set_color_invalid_channel(mockHydroShift):
    with pytest.raises(NotSupportedByDevice):
        mockHydroShift.set_color(channel="pump", mode="static", colors=[(255, 0, 0)])


def test_set_color_invalid_mode(mockHydroShift):
    with pytest.raises(ValueError, match="unknown lighting mode"):
        mockHydroShift.set_color(channel="fan", mode="nonexistent", colors=[(255, 0, 0)])


def test_speed_profile_not_supported(mockHydroShift):
    with pytest.raises(NotSupportedByDevice):
        mockHydroShift.set_speed_profile(channel="fan", profile=[(20, 30), (30, 50)])


def test_set_screen_invalid_channel(mockHydroShift):
    mockHydroShift._use_c_cmd = False
    with pytest.raises(NotSupportedByDevice):
        mockHydroShift.set_screen(channel="invalid", mode="brightness", value=50)


def test_set_screen_brightness(mockHydroShift):
    mockHydroShift._use_c_cmd = False
    mockHydroShift.set_screen(channel="lcd", mode="brightness", value=80)
    report = mockHydroShift.device.sent[0]
    # B-command: report.number = 0x02, report.data = pkt[1:]
    # pkt layout: [0x02, 0x0C, 0,0,0,0, 0,0,0, 0x00, 0x08, <8 bytes payload>]
    #   pkt[0]=report_id, pkt[1]=cmd, pkt[2:6]=total_size, pkt[6:9]=pkt_num
    #   pkt[9:11]=payload_len, pkt[11:19]=payload
    # payload = [lcd_mode=1, brightness=80, rotation=0, 0, 0, 0, 0, fps=24]
    assert report[0] == 0x02       # B-command report ID
    assert report.data[0] == 0x0C  # LCD control command (pkt[1])
    assert report.data[10] == 1    # lcd_mode = APPLICATION (pkt[11])
    assert report.data[11] == 80   # brightness (pkt[12])


def test_set_screen_orientation(mockHydroShift):
    mockHydroShift._use_c_cmd = False
    mockHydroShift._rotation = 0
    mockHydroShift.set_screen(channel="lcd", mode="orientation", value=90)
    # Orientation is stored and applied client-side when sending images
    assert mockHydroShift._rotation == 90
    assert len(mockHydroShift.device.sent) == 0  # no packet sent


def test_set_screen_invalid_orientation(mockHydroShift):
    mockHydroShift._use_c_cmd = False
    with pytest.raises(ValueError, match="unsupported rotation"):
        mockHydroShift.set_screen(channel="lcd", mode="orientation", value=45)


def test_set_screen_invalid_mode(mockHydroShift):
    mockHydroShift._use_c_cmd = False
    with pytest.raises(ValueError, match="unknown screen mode"):
        mockHydroShift.set_screen(channel="lcd", mode="nonexistent", value=None)
