import pytest

from _testutils import MockHidapiDevice
from liquidctl.driver.asus_ryujin import AsusRyujin


@pytest.fixture
def mockRyujin():
    return AsusRyujin(_MockRyujinDevice(), "Mock ASUS Ryujin II")


class _MockRyujinDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0x0B05, product_id=0x1988)
        self.requests = []
        self.response = None

    def write(self, data):
        super().write(data)
        self.requests.append(data)

        assert data[0] == 0xEC
        header = data[1]

        # Sampled responses without trailing zeros
        if header == 0x82:  # Get firmware info
            self.response = "ec02004155524a312d533735302d30313034"
        elif header == 0x99:  # Get cooler status (temperature, pump speed, embedded fan speed)
            self.response = "ec19001b056405100e"
        elif header == 0x9A:  # Get pump and embedded fan duty
            self.response = "ec1a0000223c"
        elif header == 0xA0:  # Get AIO fan controller fan speeds
            self.response = "ec200000000c03ee02"
        elif header == 0xA1:  # Get AIO fan controller duty
            self.response = "ec2100005b"
        elif header == 0x1A:  # Set pump and embedded fan duty
            self.response = "ec1a"
        elif header == 0x21:  # Set AIO fan controller duty
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


def test_initialize(mockRyujin):
    with mockRyujin.connect():
        (firmware_status,) = mockRyujin.initialize()

        assert firmware_status[1] == "AURJ1-S750-0104"


def test_status(mockRyujin):
    with mockRyujin.connect():
        actual = mockRyujin.get_status()

        expected = [
            ("Liquid temperature", pytest.approx(27.5), "°C"),
            ("Pump speed", 1380, "rpm"),
            ("Pump fan speed", 3600, "rpm"),
            ("Pump duty", 34, "%"),
            ("Pump fan duty", 60, "%"),
            ("External fan duty", 36, "%"),
            ("External fan 1 speed", 780, "rpm"),
            ("External fan 2 speed", 750, "rpm"),
            ("External fan 3 speed", 0, "rpm"),
            ("External fan 4 speed", 0, "rpm"),
        ]

    assert sorted(actual) == sorted(expected)


def test_set_fixed_speeds(mockRyujin):
    with mockRyujin.connect():
        mockRyujin.set_fixed_speed(channel="pump", duty=10)
        assert mockRyujin.device.requests[-1][3] == 0x0A

        mockRyujin.set_fixed_speed(channel="pump-fan", duty=20)
        assert mockRyujin.device.requests[-1][4] == 0x14

        mockRyujin.set_fixed_speed(channel="external-fans", duty=30)
        assert mockRyujin.device.requests[-1][4] == 0x4C

        mockRyujin.set_fixed_speed(channel="fans", duty=40)
        assert mockRyujin.device.requests[-2][4] == 0x28
        assert mockRyujin.device.requests[-1][4] == 0x66
