from liquidctl.driver.nvidia import *
from liquidctl.error import *
import pytest

from _testutils import VirtualSmbus


# ASUS Turing


def create_strix_2080ti_oc_bus(controller_address=None):
    smbus = VirtualSmbus(
            description='NVIDIA i2c adapter 1 at 1c:00.0',
            parent_vendor=NVIDIA,
            parent_device=RTX_2080_TI_REV_A,
            parent_subsystem_vendor=ASUS,
            parent_subsystem_device=ASUS_STRIX_RTX_2080_TI_OC,
            parent_driver='nvidia',
    )

    if controller_address == None:
        return smbus

    try:
        smbus.open()
        smbus.write_byte_data(controller_address, 0x20, 0x15)
        smbus.write_byte_data(controller_address, 0x21, 0x89)
        smbus.close()
    except:
        pass

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
    assert list(map(type, RogTuring.probe(smbus, unsafe='smbus,rog_turing'))) == []


def test_rog_turing_assumes_device_if_unsafe_bus_unavailable(monkeypatch):
    smbus = create_strix_2080ti_oc_bus()  # no addresses enabled

    # assume a device if the bus cannot be read due to missing unsafe features
    assert list(map(type, RogTuring.probe(smbus))) == [RogTuring]


def test_rog_turing_finds_devices_on_any_addresses(monkeypatch):
    addresses = [0x29, 0x2a, 0x60]
    for addr in addresses:
        smbus = create_strix_2080ti_oc_bus(controller_address=addr)
        cards = list(RogTuring.probe(smbus, unsafe='smbus,rog_turing'))
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

    cards = list(RogTuring.probe(smbus, unsafe='smbus,rog_turing'))
    assert list(map(type, cards)) == [RogTuring]
    assert cards[0].address == hex(addresses[0])


def test_unsafely_probed_does_use_placehold_address(strix_2080ti_oc_bus):
    card = next(RogTuring.probe(strix_2080ti_oc_bus))
    too_late = 'smbus,rog_turing'

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
    assert card.get_status(verbose=True) == []
    assert card.get_status(verbose=True, unsafe='rog_turing') == []
    assert card.get_status(verbose=True, unsafe='smbus') == []


def test_rog_turing_gets_verbose_status(strix_2080ti_oc_bus):
    enable = 'smbus,rog_turing'
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    try:
        card.connect(unsafe=enable)

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
    finally:
        card.disconnect()


def test_rog_turing_set_color_is_unsafe(strix_2080ti_oc_bus):
    card = next(RogTuring.probe(strix_2080ti_oc_bus))

    with pytest.raises(UnsafeFeaturesNotEnabled):
        assert card.set_color('led', 'off', [])

    with pytest.raises(UnsafeFeaturesNotEnabled):
        assert card.set_color('led', 'off', [], unsafe='rog_turing')

    with pytest.raises(UnsafeFeaturesNotEnabled):
        assert card.set_color('led', 'off', [], unsafe='smbus')


def test_rog_turing_sets_color_to_off(strix_2080ti_oc_bus):
    enable = 'smbus,rog_turing'
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    try:
        card.connect(unsafe=enable)

        # change colors to something other than 0
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x04, 0xaa)
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x05, 0xbb)
        strix_2080ti_oc_bus.write_byte_data(0x2a, 0x06, 0xcc)

        card.set_color('led', 'off', [], unsafe=enable)

        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x01
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x04) == 0x00
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x05) == 0x00
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x06) == 0x00
    finally:
        card.disconnect()


def test_rog_turing_sets_color_to_fixed(strix_2080ti_oc_bus):
    enable = 'smbus,rog_turing'
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    try:
        card.connect(unsafe=enable)

        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'fixed', [radical_red], unsafe=enable)

        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x01
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x04) == 0xff
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x05) == 0x35
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x06) == 0x5e
    finally:
        card.disconnect()


def test_rog_turing_sets_color_to_rainbow(strix_2080ti_oc_bus):
    enable = 'smbus,rog_turing'
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    try:
        card.connect(unsafe=enable)

        card.set_color('led', 'rainbow', [], unsafe=enable)
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x04
    finally:
        card.disconnect()


def test_rog_turing_sets_color_to_breathing(strix_2080ti_oc_bus):
    enable = 'smbus,rog_turing'
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    try:
        card.connect(unsafe=enable)

        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'breathing', [radical_red], unsafe=enable)

        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x02
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x04) == 0xff
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x05) == 0x35
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x06) == 0x5e
    finally:
        card.disconnect()


def test_rog_turing_sets_non_volatile_color(strix_2080ti_oc_bus):
    enable = 'smbus,rog_turing'
    card = next(RogTuring.probe(strix_2080ti_oc_bus, unsafe=enable))

    try:
        card.connect(unsafe=enable)

        card.set_color('led', 'off', [], non_volatile=True, unsafe=enable)
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x07) == 0x01
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x04) == 0x00
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x05) == 0x00
        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x06) == 0x00

        assert strix_2080ti_oc_bus.read_byte_data(0x2a, 0x0e) == 0x01  # persistent
    finally:
        card.disconnect()
