from pathlib import Path

from liquidctl.driver.smbus import LinuxI2c, LinuxI2cBus, SmbusDriver

import pytest


class Canary(SmbusDriver):
    """Canary driver to reveal if SMBus probing is taking place."""

    @classmethod
    def probe(cls, smbus, **kwargs):
        yield Canary(smbus, 'Canary', vendor_id=-1, product_id=-1, address=-1)

    def connect(self, **kwargs):
        # there is no justification for calling connect on this test driver
        raise RuntimeError('forbidden')


def replace_smbus(replacement, monkeypatch):
    import liquidctl.driver.smbus

    # fragile hack: since messing with sys.meta_path (PEP 302) is tricky in a
    # pytest context, get into liquidctl.driver.smbus module and replace the
    # imported SMBus class after the fact
    monkeypatch.setattr(liquidctl.driver.smbus, 'SMBus', replacement)

    return replacement


@pytest.fixture
def emulated_smbus(monkeypatch):
    class SMBus:
        def __init__(self, number):
            pass

    return replace_smbus(SMBus, monkeypatch)


@pytest.fixture
def no_smbus(monkeypatch):
    return replace_smbus(None, monkeypatch)


def test__helper_fixture_replaces_real_smbus_implementation(emulated_smbus, tmpdir):
    i2c_dev = Path(tmpdir.mkdir('i2c-9999'))  # unlikely to be valid
    bus = LinuxI2cBus(i2c_dev=i2c_dev)

    bus.open()

    assert type(bus._smbus) == emulated_smbus


def test_probing_is_aborted_if_smbus_module_is_unavailable(no_smbus):
    discovered = Canary.find_supported_devices()
    assert discovered == []


def test_filter_by_usb_port_yields_no_devices(emulated_smbus):
    discovered = Canary.find_supported_devices(usb_port='usb1')
    assert discovered == []


def test_aborts_if_sysfs_is_missing_devices(emulated_smbus, tmpdir):
    empty = tmpdir.mkdir('sys').mkdir('bus').mkdir('i2c')
    virtual_bus = LinuxI2c(i2c_root=empty)

    discovered = Canary.find_supported_devices(root_bus=virtual_bus)
    assert discovered == []


def test_finds_a_device(emulated_smbus, tmpdir):
    i2c_root = tmpdir.mkdir('sys').mkdir('bus').mkdir('i2c')
    device1 = i2c_root.mkdir('devices').mkdir('i2c-42')

    virtual_bus = LinuxI2c(i2c_root=i2c_root)

    discovered = Canary.find_supported_devices(root_bus=virtual_bus)
    assert len(discovered) == 1
    assert discovered[0]._smbus.name == 'i2c-42'


def test_ignores_non_bus_sysfs_entries(emulated_smbus, tmpdir):
    i2c_root = tmpdir.mkdir('sys').mkdir('bus').mkdir('i2c')
    devices = i2c_root.mkdir('devices')
    device1 = devices.mkdir('i2c-0')
    device2 = devices.mkdir('0-0050')  # SPD info chip on i2c-0
    device3 = devices.mkdir('i2c-DELL0829:00')  # i2c HID chip from Dell laptop

    virtual_bus = LinuxI2c(i2c_root=i2c_root)

    discovered = Canary.find_supported_devices(root_bus=virtual_bus)
    assert len(discovered) == 1
    assert discovered[0]._smbus.name == 'i2c-0'


def test_honors_a_bus_filter(emulated_smbus, tmpdir):
    i2c_root = tmpdir.mkdir('sys').mkdir('bus').mkdir('i2c')
    devices = i2c_root.mkdir('devices')
    device1 = devices.mkdir('i2c-0')
    device1 = devices.mkdir('i2c-1')

    virtual_bus = LinuxI2c(i2c_root=i2c_root)

    discovered = Canary.find_supported_devices(bus='i2c-1',
                                               root_bus=virtual_bus)
    assert len(discovered) == 1
    assert discovered[0]._smbus.name == 'i2c-1'


@pytest.fixture
def emulated_device(tmpdir, emulated_smbus):
    i2c_dev = Path(tmpdir.mkdir('i2c-0'))
    bus = LinuxI2cBus(i2c_dev=i2c_dev)
    dev = SmbusDriver(smbus=bus, description='Test', vendor_id=-1,
                      product_id=-1, address=-1)

    return (bus, dev)


def test_connect_is_unsafe(emulated_device):
    bus, dev = emulated_device

    def mock_open():
        nonlocal opened
        opened = True

    bus.open = mock_open
    opened = False

    dev.connect()
    assert not opened


def test_connects(emulated_device):
    bus, dev = emulated_device

    def mock_open():
        nonlocal opened
        opened = True

    bus.open = mock_open
    opened = False

    with dev.connect(unsafe='smbus') as cm:
        assert cm == dev
        assert opened
