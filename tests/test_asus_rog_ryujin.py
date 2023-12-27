import pytest

from _testutils import MockHidapiDevice
from liquidctl.driver.asus_rog_ryujin import RogRyujin


@pytest.fixture
def mockRyujin():
    return RogRyujin(_MockRyujinDevice(), "Mock ASUS ROG RYUJIN II")


class _MockRyujinDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0x0B05, product_id=0x1988)
        self.response = None

    def write(self, data):
        super().write(data)
        assert data[0] == 0xEC
        header = data[1]

        # Sampled responses without trailing zeros
        if header == 0x82:
            self.response = "ec02004155524a312d533735302d30313034"
        elif header == 0x99:
            self.response = "ec19001b044605"
        elif header == 0x9A:
            self.response = "ec1a000023"
        elif header == 0xA0:
            self.response = "ec200000000c03ee02"
        elif header == 0xA1:
            self.response = "ec2100005b"
        elif header == 0x1A:
            self.response = "ec1a"
        elif header == 0x21:
            self.response = "ec21"
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


def test_basic(mockRyujin):
    with mockRyujin.connect():
        mockRyujin.initialize()
        mockRyujin.get_status()
        mockRyujin.set_fixed_speed(channel="pump", duty=10)
        mockRyujin.set_fixed_speed(channel="fan1", duty=20)
        mockRyujin.set_fixed_speed(channel="fan2", duty=30)
        mockRyujin.set_fixed_speed(channel="fans", duty=40)
