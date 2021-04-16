import pytest
from _testutils import MockHidapiDevice, Report

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

    for i in range(3):
        dev.device.preload_read(Report(0, bytes(63)))

    dev.initialize()
    dev.get_status()

    dev.set_color(channel='led', mode='breathing', colors=iter([[142, 24, 68]]),
                  speed='fastest')

    dev.set_fixed_speed(channel='fan3', duty=50)


def test_smart_device_reads_status(mockSmartDevice):
    dev = mockSmartDevice

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
        ('Firmware version', '1.0.7', ''),
        ('LED accessories', 2, ''),
        ('LED accessory type', 'HUE+ Strip', ''),
        ('LED count (total)', 20, ''),
        ('Noise level', 63, 'dB')
    ]

    got = dev.get_status()

    assert expected == got
