from liquidctl.driver.nvidia import *
from liquidctl.error import *
import pytest

from _testutils import VirtualSmbus


# ASUS Strix turing


@pytest.fixture
def asus_strix_2080ti_oc_smbus():
    return VirtualSmbus(
            description='NVIDIA i2c adapter 1 at 1c:00.0',
            parent_vendor=NVIDIA,
            parent_device=RTX_2080_TI_REV_A,
            parent_subsystem_vendor=ASUS,
            parent_subsystem_device=STRIX_RTX_2080_TI_OC,
            parent_driver='nvidia',
    )


def create_asus_strix_2080ti_oc_smbus(controller_address=None):
    smbus = VirtualSmbus(
            description='NVIDIA i2c adapter 1 at 1c:00.0',
            parent_vendor=NVIDIA,
            parent_device=RTX_2080_TI_REV_A,
            parent_subsystem_vendor=ASUS,
            parent_subsystem_device=STRIX_RTX_2080_TI_OC,
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



def test_rog_turing_finds_devices(monkeypatch, asus_strix_2080ti_oc_smbus):
    smbus = asus_strix_2080ti_oc_smbus

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

    # check device with no read write permissions should assume there is a device
    assert list(map(type, RogTuring.probe(smbus))) == [RogTuring]

    # check device with unsafe permissions should not find a device
    assert list(map(type, RogTuring.probe(smbus, unsafe='smbus,rog_turing'))) == []

    # check that each of the 3 register types are detected
    addresses = [0x29, 0x2a, 0x60]
    for addr in addresses:
        smbus = create_asus_strix_2080ti_oc_smbus(controller_address=addr)
        assert list(map(type, RogTuring.probe(smbus, unsafe='smbus,rog_turing'))) == [RogTuring]


    # test multiple controllers on one bus? I suppose that is possible
    try:
        asus_strix_2080ti_oc_smbus.open()
        asus_strix_2080ti_oc_smbus.write_byte_data(0x29, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x29, 0x21, 0x89)
        
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x21, 0x89)
        
        asus_strix_2080ti_oc_smbus.write_byte_data(0x60, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x60, 0x21, 0x89)
        asus_strix_2080ti_oc_smbus.close()
    except:
        pass

    assert list(map(type, RogTuring.probe(asus_strix_2080ti_oc_smbus, unsafe='smbus,rog_turing'))) == [RogTuring, RogTuring, RogTuring]

def test_rog_turing_get_status_is_noop(asus_strix_2080ti_oc_smbus):
    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))
    assert card.get_status() == []


def test_rog_turing_get_verbose_status_is_unsafe(asus_strix_2080ti_oc_smbus):
    
    try:
        asus_strix_2080ti_oc_smbus.open()
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x21, 0x89)
        asus_strix_2080ti_oc_smbus.close()
    except:
        pass

    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))
    assert card.get_status(verbose=True) == []


def test_rog_turing_gets_verbose_status(asus_strix_2080ti_oc_smbus):
    try:
        asus_strix_2080ti_oc_smbus.open()
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x21, 0x89)
        asus_strix_2080ti_oc_smbus.close()
    except:
        pass

    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))
    enable = 'smbus,rog_turing'

    try:
        card.connect(unsafe=enable)

        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x07, 0x01)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x04, 0xaa)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x05, 0xbb)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x06, 0xcc)

        status = card.get_status(verbose=True, unsafe=enable)
        expected = [
            ('Mode', str(RogTuring.Mode.FIXED), ''),
            ('Color', 'aabbcc', ''),
        ]

        assert status == expected
    finally:
        card.disconnect()


def test_rog_turing_set_color_is_unsafe(asus_strix_2080ti_oc_smbus):
    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))

    with pytest.raises(UnsafeFeaturesNotEnabled):
        assert card.set_color('led', 'off', [])

    with pytest.raises(UnsafeFeaturesNotEnabled):
        assert card.set_color('led', 'off', [], unsafe='rog_turing')

    with pytest.raises(UnsafeFeaturesNotEnabled):
        assert card.set_color('led', 'off', [], unsafe='smbus')

def test_rog_turing_sets_color_to_off(asus_strix_2080ti_oc_smbus):
    try:
        asus_strix_2080ti_oc_smbus.open()
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x21, 0x89)
        
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x07, 0x02)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x04, 0xaa)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x05, 0xbb)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x06, 0xcc)
        asus_strix_2080ti_oc_smbus.close()
    except:
        pass

    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))
    enable = 'smbus,rog_turing'

    try:
        card.connect(unsafe=enable)

        card.set_color('led', 'off', [], unsafe=enable)
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x07) == 0x01
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x04) == 0x00
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x05) == 0x00
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x06) == 0x00
    finally:
        card.disconnect()


def test_rog_turing_sets_color_to_fixed(asus_strix_2080ti_oc_smbus):
    try:
        asus_strix_2080ti_oc_smbus.open()
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x21, 0x89)
        
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x07, 0x02)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x04, 0xaa)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x05, 0xbb)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x06, 0xcc)
        asus_strix_2080ti_oc_smbus.close()
    except:
        pass

    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))
    enable = 'smbus,rog_turing'

    try:
        card.connect(unsafe=enable)

        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'fixed', [radical_red], unsafe=enable)

        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x07) == 0x01
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x04) == 0xff
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x05) == 0x35
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x06) == 0x5e
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x0e) == 0x00   # make sure its not persistant
    finally:
        card.disconnect()


def test_rog_turing_sets_color_to_rainbow(asus_strix_2080ti_oc_smbus):
    try:
        asus_strix_2080ti_oc_smbus.open()
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x21, 0x89)
        
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x07, 0x02)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x04, 0xaa)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x05, 0xbb)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x06, 0xcc)
        asus_strix_2080ti_oc_smbus.close()
    except:
        pass

    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))
    enable = 'smbus,rog_turing'

    try:
        card.connect(unsafe=enable)

        card.set_color('led', 'rainbow', [], unsafe=enable)
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x07) == 0x04
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x0e) == 0x00
    finally:
        card.disconnect()


def test_rog_turing_sets_color_to_breathing(asus_strix_2080ti_oc_smbus):
    try:
        asus_strix_2080ti_oc_smbus.open()
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x21, 0x89)
        
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x07, 0x01)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x04, 0xaa)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x05, 0xbb)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x06, 0xcc)
        asus_strix_2080ti_oc_smbus.close()
    except:
        pass

    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))
    enable = 'smbus,rog_turing'

    try:
        card.connect(unsafe=enable)

        radical_red = [0xff, 0x35, 0x5e]
        card.set_color('led', 'breathing', [radical_red], unsafe=enable)
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x07) == 0x02
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x04) == 0xff
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x05) == 0x35
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x06) == 0x5e
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x0e) == 0x00
    finally:
        card.disconnect()


def test_rog_turing_sets_non_volatile_color(asus_strix_2080ti_oc_smbus):
    try:
        asus_strix_2080ti_oc_smbus.open()
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x20, 0x15)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x21, 0x89)
        
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x07, 0x02)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x04, 0xaa)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x05, 0xbb)
        asus_strix_2080ti_oc_smbus.write_byte_data(0x2a, 0x06, 0xcc)
        asus_strix_2080ti_oc_smbus.close()
    except:
        pass

    card = next(RogTuring.probe(asus_strix_2080ti_oc_smbus))
    enable = 'smbus,rog_turing'

    try:
        card.connect(unsafe=enable)

        card.set_color('led', 'off', [], non_volatile=True, unsafe=enable)
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x07) == 0x01
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x04) == 0x00
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x05) == 0x00
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x06) == 0x00
        
        assert asus_strix_2080ti_oc_smbus.read_byte_data(0x2a, 0x0e) == 0x01
    finally:
        card.disconnect()
