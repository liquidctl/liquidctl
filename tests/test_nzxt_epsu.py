import pytest
from liquidctl.driver.nzxt_epsu import NzxtEPsu
from _testutils import MockHidapiDevice, Report


class _MockPsuDevice(MockHidapiDevice):
    def write(self, data):
        super().write(data)
        data = data[1:]  # skip unused report ID
        reply = bytearray(64)
        reply[0:2] = (0xaa, data[2])
        if data[5] == 0x06:
            reply[2] = data[2] - 2
        elif data[5] == 0xfc:
            reply[2:4] = (0x11, 0x41)
        self.preload_read(Report(0, reply[0:]))


@pytest.fixture
def mockPsuDevice():
    device = _MockPsuDevice()
    return NzxtEPsu(device, 'mock NZXT E500 PSU')


def test_psu_device_initialize(mockPsuDevice):
    mockPsuDevice.initialize()

    assert len(mockPsuDevice.device.sent) == 0


def test_psu_device_status(mockPsuDevice):

    mockPsuDevice.connect()
    status = mockPsuDevice.get_status()

    fw = next(filter(lambda x: x[0] == 'Firmware version', status))
    assert fw == ('Firmware version', 'A017/40983', '')

    sent = mockPsuDevice.device.sent
    assert sent[0] == Report(0, [0xad, 0, 3, 1, 0x60, 0xfc] + 58*[0])
