import pytest
from liquidctl.driver.hydro_platinum import HydroPlatinum
from liquidctl.pmbus import compute_pec
from _testutils import MockHidapiDevice, Report, MockRuntimeStorage

_SAMPLE_PATH = (r'IOService:/AppleACPIPlatformExpert/PCI0@0/AppleACPIPCI/XHC@14/XH'
                r'C@14000000/HS11@14a00000/USB2.0 Hub@14a00000/AppleUSB20InternalH'
                r'ub@14a00000/AppleUSB20HubPort@14a10000/USB2.0 Hub@14a10000/Apple'
                r'USB20Hub@14a10000/AppleUSB20HubPort@14a12000/H100i Platinum@14a1'
                r'2000/IOUSBHostInterface@0/AppleUserUSBHostHIDDevice+Win\\#!&3142')
_WIN_MAX_PATH = 260  # Windows API should be the bottleneck


@pytest.fixture
def h115iPlatinumDevice():
    description = 'Mock H115i Platinum'
    kwargs = {'fan_count': 2, 'fan_leds': 4}
    device = _MockHydroPlatinumDevice()
    dev = HydroPlatinum(device, description, **kwargs)

    runtime_storage = MockRuntimeStorage(key_prefixes='testing')
    runtime_storage.store('leds_enabled', 0)

    dev.connect(runtime_storage=runtime_storage)

    return dev

@pytest.fixture
def h100iPlatinumSeDevice():
    description = 'Mock H100i Platinum SE'
    kwargs = {'fan_count': 2, 'fan_leds': 16}
    device = _MockHydroPlatinumDevice()
    dev = HydroPlatinum(device, description, **kwargs)

    runtime_storage = MockRuntimeStorage(key_prefixes='testing')
    runtime_storage.store('leds_enabled', 0)

    dev.connect(runtime_storage=runtime_storage)

    return dev


class _MockHydroPlatinumDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0xffff, product_id=0x0c17, address=_SAMPLE_PATH)
        self.fw_version = (1, 1, 15)
        self.temperature = 30.9
        self.fan1_speed = 1499
        self.fan2_speed = 1512
        self.pump_speed = 2702

    def read(self, length):
        pre = super().read(length)
        if pre:
            return pre
        buf = bytearray(64)
        buf[2] = self.fw_version[0] << 4 | self.fw_version[1]
        buf[3] = self.fw_version[2]
        buf[7] = int((self.temperature - int(self.temperature)) * 255)
        buf[8] = int(self.temperature)
        buf[15:17] = self.fan1_speed.to_bytes(length=2, byteorder='little')
        buf[22:24] = self.fan2_speed.to_bytes(length=2, byteorder='little')
        buf[29:31] = self.pump_speed.to_bytes(length=2, byteorder='little')
        buf[-1] = compute_pec(buf[1:-1])
        return buf[:length]


def test_h115i_platinum_device_connect(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    dev.disconnect()  # the fixture had by default connected to the device

    def mock_open():
        nonlocal opened
        opened = True
    dev.device.open = mock_open
    opened = False

    with dev.connect() as cm:
        assert cm == dev
        assert opened


def test_h115i_platinum_device_command_format(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    dev.initialize()
    dev.get_status()
    dev.set_fixed_speed(channel='fan', duty=100)
    dev.set_speed_profile(channel='fan', profile=[])
    dev.set_color(channel='led', mode='off', colors=[])

    assert len(dev.device.sent) == 9
    for i, (report, data) in enumerate(dev.device.sent):
        assert report == 0
        assert len(data) == 64
        assert data[0] == 0x3f
        assert data[1] >> 3 == i + 1
        assert data[-1] == compute_pec(data[1:-1])


def test_h115i_platinum_device_command_format_enabled(h115iPlatinumDevice):
    dev = h115iPlatinumDevice

    # test that the led enable messages are not sent if they are sent again
    dev.initialize()
    dev._data.store('leds_enabled', 1)
    dev.get_status()
    dev.set_fixed_speed(channel='fan', duty=100)
    dev.set_speed_profile(channel='fan', profile=[])
    dev.set_color(channel='led', mode='off', colors=[])

    assert len(dev.device.sent) == 6
    for i, (report, data) in enumerate(dev.device.sent):
        assert report == 0
        assert len(data) == 64
        assert data[0] == 0x3f
        assert data[1] >> 3 == i + 1
        assert data[-1] == compute_pec(data[1:-1])


def test_h115i_platinum_device_get_status(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    temp, fan1, fan2, pump = dev.get_status()

    assert temp[1] == pytest.approx(dev.device.temperature, abs=1 / 255)
    assert fan1[1] == dev.device.fan1_speed
    assert fan2[1] == dev.device.fan2_speed
    assert pump[1] == dev.device.pump_speed
    assert dev.device.sent[0].data[1] & 0b111 == 0
    assert dev.device.sent[0].data[2] == 0xff


def test_h115i_platinum_device_handle_real_statuses(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    samples = [
        (
            'ff08110f0001002c1e0000aee803aed10700aee803aece0701aa0000aa9c0900'
            '0000000000000000000000000000000000000000000000000000000000000010'
        ),
        (
            'ff40110f009e14011b0102ffe8037e6a0502ffe8037e6d0501aa0000aa350901'
            '0000000000000000000000000000000000000000000000000000000000000098'
        )
    ]
    for sample in samples:
        dev.device.preload_read(Report(0, bytes.fromhex(sample)))
        status = dev.get_status()
        assert len(status) == 4
        assert status[0][1] != dev.device.temperature


def test_h115i_platinum_device_initialize_status(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    dev._data.store('leds_enabled', 1)
    (fw_version, ) = dev.initialize()

    assert fw_version[1] == '%d.%d.%d' % dev.device.fw_version
    assert dev._data.load('leds_enabled', of_type=int, default=1) == 0


def test_h115i_platinum_device_common_cooling_prefix(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    dev.initialize(pump_mode='extreme')
    dev.set_fixed_speed(channel='fan', duty=42)
    dev.set_speed_profile(channel='fan', profile=[(20, 0), (55, 100)])

    assert len(dev.device.sent) == 3
    for _, data in dev.device.sent:
        assert data[0x1] & 0b111 == 0
        assert data[0x2] == 0x14
        # opaque but apparently important prefix (see @makk50's comments in #82):
        assert data[0x3:0xb] == [0x0, 0xff, 0x5] + 5 * [0xff]


def test_h115i_platinum_device_set_pump_mode(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    dev.initialize(pump_mode='extreme')
    assert dev.device.sent[0].data[0x17] == 0x2

    with pytest.raises(KeyError):
        dev.initialize(pump_mode='invalid')


def test_h115i_platinum_device_fixed_fan_speeds(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    dev.set_fixed_speed(channel='fan', duty=42)
    dev.set_fixed_speed(channel='fan1', duty=84)

    assert dev.device.sent[-1].data[0x0b] == 0x2
    assert dev.device.sent[-1].data[0x10] / 2.55 == pytest.approx(84, abs=1 / 2.55)
    assert dev.device.sent[-1].data[0x11] == 0x2
    assert dev.device.sent[-1].data[0x16] / 2.55 == pytest.approx(42, abs=1 / 2.55)

    with pytest.raises(ValueError):
        dev.set_fixed_speed('invalid', 0)


def test_h115i_platinum_device_custom_fan_profiles(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    dev.set_speed_profile(channel='fan', profile=iter([(20, 0), (55, 100)]))
    dev.set_speed_profile(channel='fan1', profile=iter([(30, 20), (50, 80)]))

    assert dev.device.sent[-1].data[0x0b] == 0x0
    assert dev.device.sent[-1].data[0x1d] == 7
    assert dev.device.sent[-1].data[0x1e:0x2c] == [30, 51, 50, 204] + 5 * [60, 255]
    assert dev.device.sent[-1].data[0x11] == 0x0
    assert dev.device.sent[-1].data[0x2c:0x3a] == [20, 0, 55, 255] + 5 * [60, 255]

    with pytest.raises(ValueError):
        dev.set_speed_profile('invalid', [])

    with pytest.raises(ValueError):
        dev.set_speed_profile('fan', zip(range(10), range(10)))


def test_h115i_platinum_device_address_leds(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    colors = [[i + 3, i + 2, i + 1] for i in range(0, 24 * 3, 3)]
    encoded = list(range(1, 24 * 3 + 1))
    dev.set_color(channel='led', mode='super-fixed', colors=iter(colors))

    assert len(dev.device.sent) == 5  # 3 for enable, 2 for off
    assert dev.device.sent[0].data[1] & 0b111 == 0b001
    assert dev.device.sent[1].data[1] & 0b111 == 0b010
    assert dev.device.sent[2].data[1] & 0b111 == 0b011
    assert dev.device.sent[3].data[1] & 0b111 == 0b100
    assert dev.device.sent[3].data[2:62] == encoded[:60]
    assert dev.device.sent[4].data[1] & 0b111 == 0b101
    assert dev.device.sent[4].data[2:14] == encoded[60:]

def test_h100i_platinum_se_device_address_leds(h100iPlatinumSeDevice):
    dev = h100iPlatinumSeDevice
    colors = [[i + 3, i + 2, i + 1] for i in range(0, 48 * 3, 3)]
    encoded = list(range(1, 48 * 3 + 1))
    dev.set_color(channel='led', mode='super-fixed', colors=iter(colors))

    assert len(dev.device.sent) == 6  # 3 for enable, 3 for the leds
    assert dev.device.sent[0].data[1] & 0b111 == 0b001
    assert dev.device.sent[1].data[1] & 0b111 == 0b010
    assert dev.device.sent[2].data[1] & 0b111 == 0b011
    assert dev.device.sent[3].data[1] & 0b111 == 0b100
    assert dev.device.sent[3].data[2:62] == encoded[:60]
    assert dev.device.sent[4].data[1] & 0b111 == 0b101
    assert dev.device.sent[4].data[2:62] == encoded[60:120]
    assert dev.device.sent[5].data[1] & 0b111 == 0b110
    assert dev.device.sent[5].data[2:26] == encoded[120:]


def test_h115i_platinum_device_synchronize(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    colors = [[3, 2, 1]]
    encoded = [1, 2, 3] * 24

    dev.set_color(channel='led', mode='fixed', colors=iter(colors))

    assert len(dev.device.sent) == 5  # 3 for enable, 2 for off

    assert dev.device.sent[0].data[1] & 0b111 == 0b001
    assert dev.device.sent[1].data[1] & 0b111 == 0b010
    assert dev.device.sent[2].data[1] & 0b111 == 0b011
    assert dev.device.sent[3].data[1] & 0b111 == 0b100

    assert dev.device.sent[3].data[2:62] == encoded[:60]
    assert dev.device.sent[4].data[1] & 0b111 == 0b101
    assert dev.device.sent[4].data[2:14] == encoded[60:]


def test_h115i_platinum_device_leds_off(h115iPlatinumDevice):
    dev = h115iPlatinumDevice
    dev.set_color(channel='led', mode='off', colors=iter([]))
    assert len(dev.device.sent) == 5  # 3 for enable, 2 for off

    for _, data in dev.device.sent[3:5]:
        assert data[2:62] == [0] * 60


def test_h115i_platinum_device_invalid_color_modes(h115iPlatinumDevice):
    dev = h115iPlatinumDevice

    with pytest.raises(ValueError):
        dev.set_color('led', 'invalid', [])

    with pytest.raises(ValueError):
        dev.set_color('invalid', 'off', [])

    assert len(dev.device.sent) == 0


def test_h115i_platinum_device_short_enough_storage_path():
    description = 'Mock H115i Platinum'
    kwargs = {'fan_count': 2, 'fan_leds': 4}
    device = _MockHydroPlatinumDevice()
    dev = HydroPlatinum(device, description, **kwargs)
    dev.connect()

    assert len(dev._data._backend._write_dir) < _WIN_MAX_PATH
    assert dev._data._backend._write_dir.endswith('3142')


def test_h115i_platinum_device_bad_stored_data(h115iPlatinumDevice):
    h115iPlatinumDevice
    # TODO
    pass
