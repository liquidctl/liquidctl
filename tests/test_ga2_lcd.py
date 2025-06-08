import pytest
from _testutils import MockHidapiDevice, Report

from collections import deque

from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver
from liquidctl.driver.ga2_lcd import GA2LCD

@pytest.fixture
def mockGA2LCD():
    device = MockHidapiDevice(vendor_id=0x0416, product_id=0x7395, address="addr")
    dev = GA2LCD(device, "mock GA II LCD")
    dev.connect()
    return dev


def test_ga2_lcd_initialize(mockGA2LCD):
    _FW_REPORT_PART1 = bytes.fromhex(
        "0186000000324e392c30312c48532c53512c43415f49492d566973696f6e2c56"
        "322e30312e3032452c312e340000000000000000000000000000000000000000"
    )

    _FW_REPORT_PART2 = bytes.fromhex(
        "01860000011b4f637420323220323032342c31303a33393a3135000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
    )

    mockGA2LCD.device.preload_read(Report(0, _FW_REPORT_PART1))
    mockGA2LCD.device.preload_read(Report(0, _FW_REPORT_PART2))
    status = mockGA2LCD.initialize()  # should perform 3 writes
    assert len(mockGA2LCD.device.sent) == 1
    inq = mockGA2LCD.device.sent[0]
    assert inq[0] == 0x01  # report ID
    assert inq.data[0] == 0x86
    assert inq.data[1] == 0x00
    assert inq.data[2] == 0x00
    assert inq.data[3] == 0x00
    assert status[0][0] == "Firmware version"
    assert status[0][1] == "N9,01,HS,SQ,CA_II-Vision,V2.01.02E,1.4Oct 22 2024,10:39:15"

def test_ga2_lcd_initialize_bad_version(mockGA2LCD):
    mockGA2LCD.device.preload_read(Report(0, bytes.fromhex("0186000000320000000000000000000000000000000000000000000000000000")))
    mockGA2LCD.device.preload_read(Report(0, bytes.fromhex("0186000000320000000000000000000000000000000000000000000000000000")))
    with pytest.raises(NotSupportedByDriver, match="Device firmware version does not match"):
        mockGA2LCD.initialize()

def test_ga2_lcd_initialize_no_response(mockGA2LCD):
    with pytest.raises(ValueError, match="Device not responding"):
        mockGA2LCD.initialize()

def test_ga2_lcd_initialize_bad_response(mockGA2LCD):
    mockGA2LCD.device.preload_read(Report(0, bytes.fromhex("018600")))
    with pytest.raises(ValueError, match="Unexpected response from device"):
        mockGA2LCD.initialize()

def test_ga2_lcd_get_status(mockGA2LCD):
    _STATUS_REPORT = bytes.fromhex(
        "01810000000705a00a6e01250800000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
    )
    mockGA2LCD.device.preload_read(Report(0, _STATUS_REPORT))
    status = mockGA2LCD.get_status()
    inq = mockGA2LCD.device.sent[0]

    assert inq[0] == 0x01
    assert inq.data[0] == 0x81
    assert inq.data[1] == 0x00
    assert inq.data[2] == 0x00
    assert inq.data[3] == 0x00

    assert len(status) == 4
    assert status[1][0] == "Fan speed"
    assert status[1][1] == 1440
    assert status[2][0] == "Pump speed"
    assert status[2][1] == 2670
    assert status[0][0] == "Liquid temperature"
    assert status[0][1] == 37.8
    assert status[3][0] == "Pump duty"
    assert status[3][1] == pytest.approx(74.1, 74.2)

def test_ga2_lcd_fan_speed(mockGA2LCD):
    mockGA2LCD.set_fixed_speed(channel='fan', duty=50)
    report = mockGA2LCD.device.sent[0]
    assert report[0] == 0x01  # report ID
    assert report.data[0] == 0x8B
    assert report.data[1] == 0x00
    assert report.data[2] == 0x00
    assert report.data[3] == 0x00
    assert report.data[4] == 0x02
    assert report.data[5] == 0x00
    assert report.data[6] == 50

def test_ga2_lcd_fan_speed_out_of_range(mockGA2LCD):
    mockGA2LCD.set_fixed_speed(channel='fan', duty=150)
    report = mockGA2LCD.device.sent[0]
    assert report[0] == 0x01  # report ID
    assert report.data[0] == 0x8B
    assert report.data[1] == 0x00
    assert report.data[2] == 0x00
    assert report.data[3] == 0x00
    assert report.data[4] == 0x02
    assert report.data[5] == 0x00
    assert report.data[6] == 100

def test_ga2_lcd_fan_speed_negative(mockGA2LCD):
    mockGA2LCD.set_fixed_speed(channel='fan', duty=-5)
    report = mockGA2LCD.device.sent[0]
    assert report[0] == 0x01  # report ID
    assert report.data[0] == 0x8B
    assert report.data[1] == 0x00
    assert report.data[2] == 0x00
    assert report.data[3] == 0x00
    assert report.data[4] == 0x02
    assert report.data[5] == 0x00
    assert report.data[6] == 0

def test_ga2_lcd_pump_speed(mockGA2LCD):
    mockGA2LCD.set_fixed_speed(channel='pump', duty=75)
    report = mockGA2LCD.device.sent[0]
    assert report[0] == 0x01  # report ID
    assert report.data[0] == 0x8A
    assert report.data[1] == 0x00
    assert report.data[2] == 0x00
    assert report.data[3] == 0x00
    assert report.data[4] == 0x02
    assert report.data[5] == 0x00
    assert report.data[6] == 75

def test_ga2_lcd_pump_speed_out_of_range(mockGA2LCD):
    mockGA2LCD.set_fixed_speed(channel='pump', duty=150)
    report = mockGA2LCD.device.sent[0]
    assert report[0] == 0x01  # report ID
    assert report.data[0] == 0x8A
    assert report.data[1] == 0x00
    assert report.data[2] == 0x00
    assert report.data[3] == 0x00
    assert report.data[4] == 0x02
    assert report.data[5] == 0x00
    assert report.data[6] == 100

def test_ga2_lcd_pump_speed_negative(mockGA2LCD):
    mockGA2LCD.set_fixed_speed(channel='pump', duty=-10)
    report = mockGA2LCD.device.sent[0]
    assert report[0] == 0x01  # report ID
    assert report.data[0] == 0x8A
    assert report.data[1] == 0x00
    assert report.data[2] == 0x00
    assert report.data[3] == 0x00
    assert report.data[4] == 0x02
    assert report.data[5] == 0x00
    assert report.data[6] == 0

def test_ga2_lcd_set_pump_lighting_mode(mockGA2LCD):
    mockGA2LCD.set_color(channel='pump', mode='static', colors=[(0xFF, 0x00, 0x00), (0x00, 0xFF, 0x00), (0x00, 0x00, 0xFF), (0xFF, 0x00, 0xFF)], speed='faster', direction='up')
    report = mockGA2LCD.device.sent[0]
    assert report[0] == 0x01  # report ID
    assert report.data[0] == 0x83
    assert report.data[1] == 0x00
    assert report.data[2] == 0x00
    assert report.data[3] == 0x00
    assert report.data[4] == 19
    assert report.data[5] == 0x00

    assert report.data[6] == 0x03 # static mode
    assert report.data[7] == 0x04 # brightness max
    assert report.data[8] == 0x03 # faster speed
    assert report.data[9] == 0xFF # red
    assert report.data[10] == 0x00
    assert report.data[11] == 0x00
    assert report.data[12] == 0x00 # green
    assert report.data[13] == 0xFF
    assert report.data[14] == 0x00
    assert report.data[15] == 0x00 # blue
    assert report.data[16] == 0x00
    assert report.data[17] == 0xFF
    assert report.data[18] == 0xFF # purple
    assert report.data[19] == 0x00
    assert report.data[20] == 0xFF

    assert report.data[21] == 0x03 # up
    assert report.data[22] == 0x00
    assert report.data[23] == 0x00
    assert report.data[24] == 0x00

def test_ga2_lcd_set_fan_lighting_mode(mockGA2LCD):
    mockGA2LCD.set_color(channel='fan', mode='rainbow', colors=[(0x00, 0x00, 0xFF), (0xFF, 0x00, 0xFF), (0xFF, 0x00, 0x00), (0x00, 0xFF, 0x00)], speed='slower', direction='down')
    report = mockGA2LCD.device.sent[0]
    assert report[0] == 0x01  # report ID
    assert report.data[0] == 0x85
    assert report.data[1] == 0x00
    assert report.data[2] == 0x00
    assert report.data[3] == 0x00
    assert report.data[4] == 20

    assert report.data[5] == 0x05 # static mode
    assert report.data[6] == 0x04 # brightness max
    assert report.data[7] == 0x01 # slower speed
    assert report.data[8] == 0x00 # blue
    assert report.data[9] == 0x00
    assert report.data[10] == 0xFF
    assert report.data[11] == 0xFF # purple
    assert report.data[12] == 0x00
    assert report.data[13] == 0xFF
    assert report.data[14] == 0xFF # red
    assert report.data[15] == 0x00
    assert report.data[16] == 0x00
    assert report.data[17] == 0x00 # green
    assert report.data[18] == 0xFF
    assert report.data[19] == 0x00

    assert report.data[20] == 0x02 # down
    assert report.data[21] == 0x00
    assert report.data[22] == 0x00
    assert report.data[23] == 0x00
    assert report.data[24] == 24
