from liquidctl.driver.nvidia import *
from liquidctl.error import *
import pytest

from _testutils import VirtualSmbus


# EVGA Pascal


@pytest.fixture
def evga_gtx_1080_ftw_smbus():
    return VirtualSmbus(
            description='NVIDIA i2c adapter 1 at 1:00.0',
            parent_vendor=NVIDIA,
            parent_device=NVIDIA_GTX_1080,
            parent_subsystem_vendor=EVGA,
            parent_subsystem_device=EVGA_GTX_1080_FTW,
            parent_driver='nvidia',
    )


def test_evga_pascal_finds_devices(monkeypatch, evga_gtx_1080_ftw_smbus):
    smbus = evga_gtx_1080_ftw_smbus

    checks = [
        ('parent_subsystem_vendor', 0xffff),
        ('parent_vendor', 0xffff),
        ('parent_driver', 'other'),
        ('parent_subsystem_device', 0xffff),
        ('parent_device', 0xffff),
        ('description', 'NVIDIA i2c adapter 2 at 1:00.0'),
    ]

    for attr, val in checks:
        with monkeypatch.context() as m:
            m.setattr(smbus, attr, val)
            assert list(EvgaPascal.probe(smbus)) == [], \
                    f'changing {attr} did not cause a mismatch'

    assert list(map(type, EvgaPascal.probe(smbus))) == [EvgaPascal]


def test_evga_pascal_get_status_is_noop(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))
    assert card.get_status() == []


def test_evga_pascal_get_verbose_status_is_unsafe(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))
    assert card.get_status(verbose=True) == []


def test_evga_pascal_gets_verbose_status(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))
    enable = 'smbus,evga_pascal'

    try:
        card.connect(unsafe=enable)

        evga_gtx_1080_ftw_smbus.write_byte_data(0x49, 0x09, 0xaa)
        evga_gtx_1080_ftw_smbus.write_byte_data(0x49, 0x0a, 0xbb)
        evga_gtx_1080_ftw_smbus.write_byte_data(0x49, 0x0b, 0xcc)
        evga_gtx_1080_ftw_smbus.write_byte_data(0x49, 0x0c, 0x01)

        status = card.get_status(verbose=True, unsafe=enable)
        expected = [
            ('Mode', EvgaPascal.Mode.FIXED, ''),
            ('Color', 'aabbcc', ''),
        ]

        assert status == expected
    finally:
        card.disconnect()


def test_evga_pascal_set_color_is_unsafe(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))

    with pytest.raises(UnsafeFeaturesNotEnabled):
        assert card.set_color('led', 'off', [])


def test_evga_pascal_sets_color_to_off(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))
    enable = 'smbus,evga_pascal'

    try:
        card.connect(unsafe=enable)

        # change mode register to something other than 0 (=off)
        evga_gtx_1080_ftw_smbus.write_byte_data(0x49, 0x0c, 0x01)

        card.set_color('led', 'off', [], unsafe=enable)
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x0c) == 0x00
    finally:
        card.disconnect()


def test_evga_pascal_sets_color_to_fixed(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))
    enable = 'smbus,evga_pascal'

    try:
        card.connect(unsafe=enable)

        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'fixed', [radical_red], unsafe=enable)

        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x0c) == 0x01
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x09) == 0xff
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x0a) == 0x35
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x0b) == 0x5e
    finally:
        card.disconnect()


def test_evga_pascal_sets_color_to_rainbow(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))
    enable = 'smbus,evga_pascal'

    try:
        card.connect(unsafe=enable)

        card.set_color('led', 'rainbow', [], unsafe=enable)
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x0c) == 0x02
    finally:
        card.disconnect()


def test_evga_pascal_sets_color_to_breathing(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))
    enable = 'smbus,evga_pascal'

    try:
        card.connect(unsafe=enable)

        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'breathing', [radical_red], unsafe=enable)

        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x0c) == 0x05
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x09) == 0xff
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x0a) == 0x35
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x0b) == 0x5e
    finally:
        card.disconnect()


def test_evga_pascal_sets_non_volatile_color(evga_gtx_1080_ftw_smbus):
    card = next(EvgaPascal.probe(evga_gtx_1080_ftw_smbus))
    enable = 'smbus,evga_pascal'

    orig = evga_gtx_1080_ftw_smbus.write_byte_data

    def raise_if_23h(address, register, value):
        orig(address, register, value)
        if register == 0x23:
            raise OSError()  # mimic smbus.SMBus on actual hardware

    evga_gtx_1080_ftw_smbus.write_byte_data = raise_if_23h

    try:
        card.connect(unsafe=enable)

        card.set_color('led', 'off', [], non_volatile=True, unsafe=enable)
        assert evga_gtx_1080_ftw_smbus.read_byte_data(0x49, 0x23) == 0xe5
    finally:
        card.disconnect()
