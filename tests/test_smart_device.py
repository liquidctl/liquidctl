import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.smart_device import SmartDevice

SAMPLE_RESPONSES = [
    '043e00056e00000b5b000301000007200002001e00',
    '04400005b500000b5b000201000007020002001e00',
    '044000053800000b5b000201000007120102001e00',
]


@pytest.fixture
def mockSmartDevice():
    device = MockHidapiDevice(vendor_id=0x1e71, product_id=0x1714, address='addr')
    return SmartDevice(device, 'mock NZXT Smart Device V1', speed_channel_count=3, color_channel_count=1)


# class methods
def test_smart_device_constructor(mockSmartDevice):

    assert mockSmartDevice._speed_channels == {
            'fan1': (0, 0, 100),
            'fan2': (1, 0, 100),
            'fan3': (2, 0, 100),
        }

    assert mockSmartDevice._color_channels == {'led': (0), }


def test_smart_device_not_totally_broken(mockSmartDevice):
    dev = mockSmartDevice

    for i in range(4):
        dev.device.preload_read(Report(0, bytes(63)))

    dev.initialize()
    dev.get_status()

    dev.set_color(channel='led', mode='breathing', colors=iter([[142, 24, 68]]),
                  speed='fastest')

    dev.set_fixed_speed(channel='fan3', duty=50)


@pytest.mark.parametrize('has_hwmon,direct_access', [(False, False), (True, True), (True, False)])
def test_smart_device_initializes(mockSmartDevice, has_hwmon, direct_access, tmp_path):
    dev = mockSmartDevice
    if has_hwmon:
        dev._hwmon = HwmonDevice('mock_module', tmp_path)

    for _, capdata in enumerate(SAMPLE_RESPONSES):
        capdata = bytes.fromhex(capdata)
        dev.device.preload_read(Report(capdata[0], capdata[1:]))

    expected = [
        ('Firmware version', '1.0.7', ''),
        ('LED accessories', 2, ''),
        ('LED accessory type', 'HUE+ Strip', ''),
        ('LED count (total)', 20, ''),
    ]

    got = dev.initialize(direct_access=direct_access)

    assert expected == got

    writes = len(dev.device.sent)
    if not has_hwmon or direct_access:
        assert writes == 2
    else:
        assert writes == 0


@pytest.mark.parametrize('has_hwmon,direct_access', [(False, False), (True, True)])
def test_smart_device_reads_status_directly(mockSmartDevice, has_hwmon, direct_access):
    dev = mockSmartDevice
    if has_hwmon:
        dev._hwmon = HwmonDevice(None, None)

    for _, capdata in enumerate(SAMPLE_RESPONSES):
        capdata = bytes.fromhex(capdata)
        dev.device.preload_read(Report(capdata[0], capdata[1:]))

    # skip initialize for now, we're not emulating the behavior precisely
    # enough to require it here

    expected = [
        ('Fan 1 speed', 1461, 'rpm'),
        ('Fan 1 voltage', 11.91, 'V'),
        ('Fan 1 current', 0.02, 'A'),
        ('Fan 1 control mode', 'PWM', ''),
        ('Fan 2 speed', 1336, 'rpm'),
        ('Fan 2 voltage', 11.91, 'V'),
        ('Fan 2 current', 0.02, 'A'),
        ('Fan 2 control mode', 'PWM', ''),
        ('Fan 3 speed', 1390, 'rpm'),
        ('Fan 3 voltage', 11.91, 'V'),
        ('Fan 3 current', 0.03, 'A'),
        ('Fan 3 control mode', None, ''),
        ('Noise level', 63, 'dB')
    ]

    got = dev.get_status(direct_access=direct_access)

    assert expected == got


def test_smart_device_reads_status_from_hwmon(mockSmartDevice, tmp_path):
    dev = mockSmartDevice

    dev._hwmon = HwmonDevice('mock_module', tmp_path)
    (tmp_path / 'fan1_input').write_text('1461\n')
    (tmp_path / 'in0_input').write_text('11910\n')
    (tmp_path / 'curr1_input').write_text('20\n')
    (tmp_path / 'pwm1_mode').write_text('1\n')
    (tmp_path / 'fan2_input').write_text('1336\n')
    (tmp_path / 'in1_input').write_text('11910\n')
    (tmp_path / 'curr2_input').write_text('20\n')
    (tmp_path / 'pwm2_mode').write_text('0\n')
    (tmp_path / 'fan3_input').write_text('1390\n')
    (tmp_path / 'in2_input').write_text('11910\n')
    (tmp_path / 'curr3_input').write_text('30\n')
    (tmp_path / 'pwm3_mode').write_text('1\n')

    # skip initialize for now, we're not emulating the behavior precisely
    # enough to require it here

    expected = [
        ('Fan 1 speed', 1461, 'rpm'),
        ('Fan 1 voltage', 11.91, 'V'),
        ('Fan 1 current', 0.02, 'A'),
        ('Fan 1 control mode', 'PWM', ''),
        ('Fan 2 speed', 1336, 'rpm'),
        ('Fan 2 voltage', 11.91, 'V'),
        ('Fan 2 current', 0.02, 'A'),
        ('Fan 2 control mode', 'DC', ''),
        ('Fan 3 speed', 1390, 'rpm'),
        ('Fan 3 voltage', 11.91, 'V'),
        ('Fan 3 current', 0.03, 'A'),
        ('Fan 3 control mode', 'PWM', ''),
    ]

    got = dev.get_status()

    assert expected == got
