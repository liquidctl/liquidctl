from struct import pack

import pytest
from _testutils import MockHidapiDevice

from liquidctl.driver.msi import MpgCooler


@pytest.fixture
def mpgCoreLiquidK360Device():
    description = 'Mock MPG CoreLiquid K360'
    device = _MockCoreLiquidK360Device(0xffff, 0xb130)
    dev = MpgCooler(device, description)
    return dev


@pytest.fixture
def mpgCoreLiquidK360DeviceInvalid():
    description = 'Mock MPG CoreLiquid K360'
    device = _MockCoreLiquidK360DeviceInvalid(0xffff, 0xb130)
    dev = MpgCooler(device, description)
    return dev


class _MockCoreLiquidK360Device(MockHidapiDevice):
    def read(self, length):
        buf = bytearray([0xd0, 0x31])
        buf += pack('<h', 496)
        buf += pack('<h', 517)
        buf += pack('<h', 509)
        buf += pack('<h', 1045)
        buf += pack('<h', 1754)
        buf += bytearray([0, 0, 0, 0, 0x7d, 0, 0x7d, 0, 0, 0])
        buf += pack('<h', 20)
        buf += pack('<h', 20)
        buf += pack('<h', 20)
        buf += pack('<h', 20)
        buf += pack('<h', 50)
        buf += bytearray([0] * 32)
        return buf[:length]


class _MockCoreLiquidK360DeviceInvalid(MockHidapiDevice):
    def read(self, length):
        buf = bytearray([0xd0, 0x32] + (62 * [0]))
        return buf[:length]


def test_mpg_core_liquid_k360_get_status(mpgCoreLiquidK360Device):
    dev = mpgCoreLiquidK360Device
    (fan1, fan1d, fan2, fan2d, fan3, fan3d, wbfan, wbfand, pump, pumpd,
     temp_in, temp_out, temp1, temp2) = dev.get_status()
    assert fan1[1] == 496
    assert fan1d[1] == 20
    assert fan2[1] == 517
    assert fan2d[1] == 20
    assert fan3[1] == 509
    assert fan3d[1] == 20
    assert wbfan[1] == 1045
    assert wbfand[1] == 20
    assert pump[1] == 1754
    assert pumpd[1] == 50
    assert dev.device.sent[0].number == 0xd0
    assert dev.device.sent[0].data[0] == 0x31


def test_mpg_core_liquid_k360_get_status_invalid_read(
        mpgCoreLiquidK360DeviceInvalid):
    dev = mpgCoreLiquidK360DeviceInvalid
    with pytest.raises(AssertionError):
        dev.get_status()
