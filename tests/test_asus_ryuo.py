import pytest

from _testutils import MockHidapiDevice 
from liquidctl.driver.asus_ryuo import AsusRyuo

@pytest.fixture
def mockRyuo():
    device = AsusRyuo(_MockRyuoDevice(), "Mock Asus Ryuo I")
    device.connect()
    return device 

class _MockRyuoDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0x0B05, product_id=0x1887)
        self.requests = []
        self.response = None

    def write(self, data):
        super().write(data)
        self.requests.append(data)

        assert data[0] == 0xEC
        header = data[1]
        if header == 0x82:
            self.response = "ec024155524f302d533435322d30323035"
        else:
            self.response = None

    def read(self, length, **kwargs):
        pre = super().read(length, **kwargs)
        if pre:
            return pre

        buf = bytearray(65)
        buf[0] = 0xEC

        if self.response:
            response = bytes.fromhex(self.response)
            buf[: len(response)] = response

        return buf[:length]

def test_initialize(mockRyuo):
    (firmware_status,) = mockRyuo.initialize()

    assert firmware_status[1] == "AURO0-S452-0205"

@pytest.mark.skip(reason="TODO: implement expected status values")
def test_status(mockRyuo):
    actual = mockRyuo.get_status()

    expected = [
   ]

    assert sorted(actual) == sorted(expected)

def test_set_fixed_speeds(mockRyuo):
    mockRyuo.set_fixed_speed(channel="fans", duty=40)
    assert mockRyuo.device.requests[-1][2] == 0x28
