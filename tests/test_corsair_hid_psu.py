import pytest
from liquidctl.driver.corsair_hid_psu import CorsairHidPsu
from _testutils import MockHidapiDevice, Report


class _MockPsuDevice(MockHidapiDevice):
    def write(self, data):
        super().write(data)
        data = data[1:]  # skip unused report ID

        reply = bytearray(64)
        if data[1] in [0xd8, 0xf0]:
            reply[2] = 1  # just a valid mode
        self.preload_read(Report(0, reply))


@pytest.fixture
def mockPsuDevice():
    device = _MockPsuDevice(vendor_id=0x1b1c, product_id=0x1c05, address='addr')
    return CorsairHidPsu(device, 'mock Corsair HX750i PSU')


def test_corsair_psu_not_totally_broken(mockPsuDevice):

    mockPsuDevice.set_fixed_speed(channel='fan', duty=50)
    report_id, report_data = mockPsuDevice.device.sent[0]
    assert report_id == 0
    assert len(report_data) == 64


def test_corsair_psu_dont_inject_report_ids(mockPsuDevice):

    mockPsuDevice.set_fixed_speed(channel='fan', duty=50)
    report_id, report_data = mockPsuDevice.device.sent[0]
    assert report_id == 0
    assert len(report_data) == 64
