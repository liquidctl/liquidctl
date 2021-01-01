import pytest
from liquidctl.driver.nzxt_epsu import NzxtEPsu
from _testutils import MockHidapiDevice, Report


@pytest.fixture
def mockPsuDevice():
    device = MockHidapiDevice(vendor_id=0x7793, product_id=0x5911, address='addr')
    return NzxtEPsu(device, 'mock NZXT E500 PSU')


def test_psu_device_initialize(mockPsuDevice):
    mockPsuDevice.initialize()

    assert len(mockPsuDevice.device.sent) == 0


def test_psu_device_status(mockPsuDevice):

    replyFW = bytearray(64)
    replyFW[0:2] = (0xaa, 0x03)
    replyFW[2:4] = (0x11, 0x41)

    replyTemp = bytearray(64)
    replyTemp[0:2] = (0xaa, 0x03)

    replySpeed = replyTemp

    replyVoltA = bytearray(64)
    replyVoltA[0:2] = (0xaa, 0x03)
    replyVoltA[2] = 1

    replyVoltB = bytearray(64)
    replyVoltB[0:2] = (0xaa, 0x04)
    replyVoltB[2] = 2

    replyCurrent = replyVoltB
    replyPower = replyCurrent

    replies = [
        replyFW,
        replyTemp,
        replySpeed,
        replyVoltA,
        replyVoltB,
        replyCurrent,
        replyPower,
        replyVoltA,
        replyVoltB,
        replyCurrent,
        replyPower,
        replyVoltA,
        replyVoltB,
        replyCurrent,
        replyPower,
        replyVoltA,
        replyVoltB,
        replyCurrent,
        replyPower,
        replyVoltA,
        replyVoltB,
        replyCurrent,
        replyPower,
    ]

    for reply in replies:
        mockPsuDevice.device.preload_read(Report(0, reply[0:]))

    mockPsuDevice.connect()
    status = mockPsuDevice.get_status()

    fw = next(filter(lambda x: x[0] == 'Firmware version', status))
    assert fw == ('Firmware version', 'A017/40983', '')

    sent = mockPsuDevice.device.sent
    assert sent[0] == Report(0, [0xad, 0, 3, 1, 0x60, 0xfc] + 58*[0])
