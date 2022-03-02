import pytest
from _testutils import VirtualSmbus

from liquidctl.driver.nvidia import *
from liquidctl.error import *


# EVGA Pascal


@pytest.fixture
def evga_1080_ftw_bus():
    return VirtualSmbus(
            description='NVIDIA i2c adapter 1 at 1:00.0',
            parent_vendor=NVIDIA,
            parent_device=NVIDIA_GTX_1080,
            parent_subsystem_vendor=EVGA,
            parent_subsystem_device=EVGA_GTX_1080_FTW,
            parent_driver='nvidia',
    )


def test_evga_pascal_finds_devices(evga_1080_ftw_bus, monkeypatch):
    smbus = evga_1080_ftw_bus

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


def test_evga_pascal_get_status_is_noop(evga_1080_ftw_bus):
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))
    assert card.get_status() == []


def test_evga_pascal_get_verbose_status_is_unsafe(evga_1080_ftw_bus):
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))
    assert card.get_status(verbose=True) == []
    assert card.get_status(verbose=True, unsafe='other') == []


def test_evga_pascal_gets_verbose_status(evga_1080_ftw_bus):
    enable = ['smbus']
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))

    with card.connect(unsafe=enable):
        evga_1080_ftw_bus.write_byte_data(0x49, 0x09, 0xaa)
        evga_1080_ftw_bus.write_byte_data(0x49, 0x0a, 0xbb)
        evga_1080_ftw_bus.write_byte_data(0x49, 0x0b, 0xcc)
        evga_1080_ftw_bus.write_byte_data(0x49, 0x0c, 0x01)

        status = card.get_status(verbose=True, unsafe=enable)
        expected = [
            ('Mode', EvgaPascal.Mode.FIXED, ''),
            ('Color', 'aabbcc', ''),
        ]

        assert status == expected


def test_evga_pascal_set_color_is_unsafe(evga_1080_ftw_bus):
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))

    with pytest.raises(UnsafeFeaturesNotEnabled):
        card.set_color('led', 'off', [])

    with pytest.raises(UnsafeFeaturesNotEnabled):
        card.set_color('led', 'off', [], unsafe='other')


def test_evga_pascal_sets_color_to_off(evga_1080_ftw_bus):
    enable = ['smbus']
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))

    with card.connect(unsafe=enable):
        # change mode register to something other than 0 (=off)
        evga_1080_ftw_bus.write_byte_data(0x49, 0x0c, 0x01)

        card.set_color('led', 'off', [], unsafe=enable)
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x0c) == 0x00

        # persistence not enabled
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x23) == 0x00


def test_evga_pascal_sets_color_to_fixed(evga_1080_ftw_bus):
    enable = ['smbus']
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))

    with card.connect(unsafe=enable):
        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'fixed', [radical_red], unsafe=enable)

        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x0c) == 0x01
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x09) == 0xff
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x0a) == 0x35
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x0b) == 0x5e

        # persistence not enabled
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x23) == 0x00


def test_evga_pascal_sets_color_to_rainbow(evga_1080_ftw_bus):
    enable = ['smbus']
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))

    with card.connect(unsafe=enable):
        card.set_color('led', 'rainbow', [], unsafe=enable)
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x0c) == 0x02

        # persistence not enabled
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x23) == 0x00


def test_evga_pascal_sets_color_to_breathing(evga_1080_ftw_bus):
    enable = ['smbus']
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))

    with card.connect(unsafe=enable):
        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'breathing', [radical_red], unsafe=enable)

        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x0c) == 0x05
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x09) == 0xff
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x0a) == 0x35
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x0b) == 0x5e

        # persistence not enabled
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x23) == 0x00


def test_evga_pascal_sets_non_volatile_color(evga_1080_ftw_bus):
    enable = ['smbus']
    card = next(EvgaPascal.probe(evga_1080_ftw_bus))

    orig = evga_1080_ftw_bus.write_byte_data

    def raise_if_23h(address, register, value):
        orig(address, register, value)
        if register == 0x23:
            raise OSError()  # mimic smbus.SMBus on actual hardware

    evga_1080_ftw_bus.write_byte_data = raise_if_23h

    with card.connect(unsafe=enable):
        card.set_color('led', 'off', [], non_volatile=True, unsafe=enable)
        assert evga_1080_ftw_bus.read_byte_data(0x49, 0x23) == 0xe5


def test_evga_pascal_experimental_devices_are_unsafe():
    for dev_id, sub_dev_id, desc in EvgaPascal._MATCHES:
        if 'experimental' not in desc:
            continue

        vbus = VirtualSmbus(
                description='NVIDIA i2c adapter 1 at 1:00.0',
                parent_vendor=NVIDIA,
                parent_device=dev_id,
                parent_subsystem_vendor=EVGA,
                parent_subsystem_device=sub_dev_id,
                parent_driver='nvidia',
        )

        card = next(EvgaPascal.probe(vbus))

        insufficient = ['smbus']

        # can connect but not read status or set color without specific
        # experimental feature
        with card.connect(unsafe=insufficient):
            assert card.get_status(verbose=True, unsafe=insufficient) == []

            with pytest.raises(UnsafeFeaturesNotEnabled):
                card.set_color('led', 'off', [], unsafe=insufficient)


# ASUS Turing


def create_strix_2080ti_oc_bus(controller_address=None):
    smbus = VirtualSmbus(
            description='NVIDIA i2c adapter 1 at 1c:00.0',
            parent_vendor=NVIDIA,
            parent_device=NVIDIA_RTX_2080_TI_REV_A,
            parent_subsystem_vendor=ASUS,
            parent_subsystem_device=ASUS_STRIX_RTX_2080_TI_OC,
            parent_driver='nvidia',
    )

    if controller_address is None:
        return smbus

    smbus.open()
    try:
        smbus.write_byte_data(controller_address, 0x20, 0x15)
        smbus.write_byte_data(controller_address, 0x21, 0x89)
    except:
        pass
    smbus.close()

    return smbus


@pytest.fixture
def strix_2080ti_oc_bus():
    address = 0x2a  # not the first candidate
    return create_strix_2080ti_oc_bus(address)


def test_rog_turing_does_not_find_devices(monkeypatch):
    smbus = create_strix_2080ti_oc_bus()  # no addresses enabled

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
            assert list(RogTuring.probe(smbus)) == [], \
                f'changing {attr} did not cause a mismatch'

    # with unsafe features addresses can be checked and none match
    assert list(map(type, RogTuring.probe(smbus, unsafe='smbus'))) == []


def test_rog_turing_assumes_device_if_unsafe_bus_unavailable(monkeypatch):
    smbus = create_strix_2080ti_oc_bus()  # no addresses enabled

    # assume a device if the bus cannot be read due to missing unsafe features
    assert list(map(type, RogTuring.probe(smbus))) == [RogTuring]


def test_rog_turing_finds_devices_on_any_addresses(monkeypatch):
    addresses = [0x29, 0x2a, 0x60]
    for addr in addresses:
        smbus = create_strix_2080ti_oc_bus(controller_address=addr)
        cards = list(RogTuring.probe(smbus, unsafe='smbus'))
        assert list(map(type, cards)) == [RogTuring]
        assert cards[0].address == hex(addr)


def test_rog_turing_only_use_one_address(monkeypatch):
    smbus = create_strix_2080ti_oc_bus()  # no addresses enabled
    addresses = [0x29, 0x2a, 0x60]

    smbus.open()
    for addr in addresses:
        smbus.write_byte_data(addr, 0x20, 0x15)
        smbus.write_byte_data(addr, 0x21, 0x89)
    smbus.close()

    cards = list(RogTuring.probe(smbus, unsafe='smbus'))
    assert list(map(type, cards)) == [RogTuring]
    assert cards[0].address == hex(addresses[0])


def test_rog_turing_unsafely_probed_is_not_usable(strix_2080ti_oc_bus):
    card = next(RogTuring.probe(strix_2080ti_oc_bus))
    too_late = 'smbus'

    with pytest.raises(AssertionError):
        card.get_status(verbose=True, unsafe=too_late)

    with pytest.raises(AssertionError):
        card.set_color('led', 'off', [], unsafe=too_late)


def test_rog_turing_get_status_is_noop(strix_2080ti_oc_bus):
    card = next(RogTuring.probe(strix_2080ti_oc_bus))
    assert card.get_status() == []


def test_rog_turing_get_verbose_status_is_unsafe(strix_2080ti_oc_bus):
    card = next(RogTuring.probe(strix_2080ti_oc_bus))
    assert card.get_status(verbose=True) == []


def test_rog_turing_gets_verbose_status(strix_2080ti_oc_bus):
    enable = ['smbus']
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    with card.connect(unsafe=enable):
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x07, 0x01)
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x04, 0xaa)
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x05, 0xbb)
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x06, 0xcc)

        status = card.get_status(verbose=True, unsafe=enable)
        expected = [
            ('Mode', RogTuring.Mode.FIXED, ''),
            ('Color', 'aabbcc', ''),
        ]

        assert status == expected


def test_rog_turing_set_color_is_unsafe(strix_2080ti_oc_bus):
    card = next(RogTuring.probe(strix_2080ti_oc_bus))

    with pytest.raises(UnsafeFeaturesNotEnabled):
        assert card.set_color('led', 'off', [])


def test_rog_turing_sets_color_to_off(strix_2080ti_oc_bus):
    enable = ['smbus']
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    with card.connect(unsafe=enable):
        # change colors to something other than 0
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x04, 0xaa)
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x05, 0xbb)
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x06, 0xcc)

        card.set_color('led', 'off', [], unsafe=enable)

        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x01
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x04) == 0x00
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x05) == 0x00
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x06) == 0x00

        # persistence not enabled
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x0e) == 0x00


def test_rog_turing_sets_color_to_fixed(strix_2080ti_oc_bus):
    enable = ['smbus']
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    with card.connect(unsafe=enable):
        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'fixed', [radical_red], unsafe=enable)

        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x01
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x04) == 0xff
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x05) == 0x35
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x06) == 0x5e

        # persistence not enabled
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x0e) == 0x00


def test_rog_turing_sets_color_to_rainbow(strix_2080ti_oc_bus):
    enable = ['smbus']
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    with card.connect(unsafe=enable):
        card.set_color('led', 'rainbow', [], unsafe=enable)
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x04

        # persistence not enabled
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x0e) == 0x00


def test_rog_turing_sets_color_to_breathing(strix_2080ti_oc_bus):
    enable = ['smbus']
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    with card.connect(unsafe=enable):
        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'breathing', [radical_red], unsafe=enable)

        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x02
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x04) == 0xff
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x05) == 0x35
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x06) == 0x5e

        # persistence not enabled
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x0e) == 0x00


def test_rog_turing_sets_non_volatile_color(strix_2080ti_oc_bus):
    enable = ['smbus']
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    with card.connect(unsafe=enable):
        card.set_color('led', 'off', [], non_volatile=True, unsafe=enable)
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x0e) == 0x01


def test_rog_turing_experimental_devices_are_unsafe():
    for dev_id, sub_dev_id, desc in RogTuring._MATCHES:
        if 'experimental' not in desc:
            continue

        vbus = VirtualSmbus(
                description='NVIDIA i2c adapter 1 at 1:00.0',
                parent_vendor=NVIDIA,
                parent_device=dev_id,
                parent_subsystem_vendor=ASUS,
                parent_subsystem_device=sub_dev_id,
                parent_driver='nvidia',
        )

        card = next(RogTuring.probe(vbus))

        enable = ['smbus', 'experimental_asus_gpu']
        insufficient = ['smbus']

        # not usable if connected without specific experimental feature
        with card.connect(unsafe=insufficient):
            with pytest.raises(AssertionError):
                card.get_status(verbose=True, unsafe=enable)

            with pytest.raises(AssertionError):
                card.set_color('led', 'off', [], unsafe=enable)

        # once connected, still cannot read status or set color without
        # specific experimental feature
        with card.connect(unsafe=enable):
            assert card.get_status(verbose=True, unsafe=insufficient) == []

            with pytest.raises(UnsafeFeaturesNotEnabled):
                card.set_color('led', 'off', [], unsafe=insufficient)
