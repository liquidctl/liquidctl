import pytest
from liquidctl.driver.kraken2 import Kraken2
from _testutils import MockHidapiDevice
from liquidctl.error import NotSupportedByDevice


@pytest.fixture
def mockKrakenXDevice():
    device = _MockKrakenDevice(fw_version=(6, 0, 2))
    dev = Kraken2(device, 'Mock X62', device_type=Kraken2.DEVICE_KRAKENX)

    dev.connect()
    return dev


@pytest.fixture
def mockOldKrakenXDevice():
    device = _MockKrakenDevice(fw_version=(2, 5, 8))
    dev = Kraken2(device, 'Mock X62', device_type=Kraken2.DEVICE_KRAKENX)

    dev.connect()
    return dev


@pytest.fixture
def mockKrakenMDevice():
    device = _MockKrakenDevice(fw_version=(6, 0, 2))
    dev = Kraken2(device, 'Mock M22', device_type=Kraken2.DEVICE_KRAKENM)

    dev.connect()
    return dev


class _MockKrakenDevice(MockHidapiDevice):
    def __init__(self, fw_version):
        super().__init__(vendor_id=0xffff, product_id=0x1e71)
        self.fw_version = fw_version
        self.temperature = 30.9
        self.fan_speed = 1499
        self.pump_speed = 2702

    def read(self, length):
        pre = super().read(length)
        if pre:
            return pre
        buf = bytearray(64)
        buf[1:3] = divmod(int(self.temperature * 10), 10)
        buf[3:5] = self.fan_speed.to_bytes(length=2, byteorder='big')
        buf[5:7] = self.pump_speed.to_bytes(length=2, byteorder='big')
        major, minor, patch = self.fw_version
        buf[0xb] = major
        buf[0xc:0xe] = minor.to_bytes(length=2, byteorder='big')
        buf[0xe] = patch
        return buf[:length]


def test_kraken_connect(mockKrakenXDevice):
    def mock_open():
        nonlocal opened
        opened = True

    mockKrakenXDevice.device.open = mock_open
    opened = False

    with mockKrakenXDevice.connect() as cm:
        assert cm == mockKrakenXDevice
        assert opened


def test_kraken_get_status(mockKrakenXDevice):
    fan, fw_ver, temp, pump = sorted(mockKrakenXDevice.get_status())

    assert fw_ver[1] == '6.0.2'
    assert temp[1] == pytest.approx(mockKrakenXDevice.device.temperature)
    assert fan[1] == mockKrakenXDevice.device.fan_speed
    assert pump[1] == mockKrakenXDevice.device.pump_speed


def test_kraken_not_totally_broken(mockKrakenXDevice):
    """Reasonable example calls to untested APIs do not raise exceptions."""
    dev = mockKrakenXDevice

    dev.initialize()
    dev.set_color(channel='ring', mode='loading', colors=iter([[90, 80, 0]]),
                  speed='slowest')
    dev.set_speed_profile(channel='fan',
                          profile=iter([(20, 20), (30, 40), (40, 100)]))
    dev.set_fixed_speed(channel='pump', duty=50)
    dev.set_instantaneous_speed(channel='pump', duty=50)


def test_kraken_set_fixed_speeds(mockOldKrakenXDevice):
    mockOldKrakenXDevice.set_fixed_speed(channel='fan', duty=42)
    mockOldKrakenXDevice.set_fixed_speed(channel='pump', duty=84)

    fan_report, pump_report = mockOldKrakenXDevice.device.sent

    assert fan_report.number == 2
    assert fan_report.data[0:4] == [0x4d, 0, 0, 42]
    assert pump_report.number == 2
    assert pump_report.data[0:4] == [0x4d, 0x40, 0, 84]


def test_kraken_speed_profiles_not_supported(mockOldKrakenXDevice):

    with pytest.raises(NotSupportedByDevice):
        mockOldKrakenXDevice.set_speed_profile('fan', [(20, 42)])

    with pytest.raises(NotSupportedByDevice):
        mockOldKrakenXDevice.set_speed_profile('pump', [(20, 84)])


def test_krakenM_get_status(mockKrakenMDevice):
    (fw_ver,) = mockKrakenMDevice.get_status()
    assert fw_ver[1] == '6.0.2'


def test_krakenM_speed_control_not_supported(mockKrakenMDevice):
    with pytest.raises(NotSupportedByDevice):
        mockKrakenMDevice.set_fixed_speed('fan', 42)

    with pytest.raises(NotSupportedByDevice):
        mockKrakenMDevice.set_fixed_speed('pump', 84)

    with pytest.raises(NotSupportedByDevice):
        mockKrakenMDevice.set_speed_profile('fan', [(20, 42)])

    with pytest.raises(NotSupportedByDevice):
        mockKrakenMDevice.set_speed_profile('pump', [(20, 84)])


def test_krakenM_not_totally_broken(mockKrakenMDevice):
    """Reasonable example calls to untested APIs do not raise exceptions."""
    dev = mockKrakenMDevice
    dev.initialize()
    dev.set_color(channel='ring', mode='loading', colors=iter([[90, 80, 0]]),
                  speed='slowest')
