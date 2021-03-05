import pytest
from _testutils import MockHidapiDevice, Report
from pytest import approx

from datetime import timedelta

from liquidctl.driver.corsair_hid_psu import CorsairHidPsu, OCPMode, FanControlMode


# https://github.com/liquidctl/liquidctl/issues/300#issuecomment-788302513
SAMPLE_PAGED_RESPONSES = [
    [
        '038bffd2',
        '038c2bf0',
        '03963e08',
    ],
    [
        '038b41d1',
        '038c1be0',
        '039610f8',
    ],
    [
        '038bd3d0',
        '038c09e0',
        '039603f8',
    ],
]

SAMPLE_RESPONSES = [
    # https://github.com/liquidctl/liquidctl/issues/300#issuecomment-788302513
    '033b1b',
    '034013d1',
    '03441ad2',
    '034680e2',
    '034f46',
    '0388ccf9',
    '038d86f0',
    '038e6af0',
    '0399434f5253414952',
    '039a524d3130303069',
    '03d46d9febfe',
    '03d802',
    '03ee4608',
    'fe03524d3130303069',

    # https://github.com/liquidctl/liquidctl/pull/54#issuecomment-543760522
    '03d29215',
    '03d1224711',

    # artificial
    '0390c803',
    '03f001',
]


class _MockPsuDevice(MockHidapiDevice):
    def __init__(self, *args, **kwargs):
        self._page = 0;
        super().__init__(*args, **kwargs)

    def write(self, data):
        super().write(data)
        data = data[1:]  # skip unused report ID

        reply = bytearray(64)

        if data[0] == 2 and data[1] == 0:
            self._page = data[2]
            reply[0:3] = data[0:3]
            self.preload_read(Report(0, reply))
        else:
            cmd = f'{data[1]:02x}'
            samples = [x for x in SAMPLE_PAGED_RESPONSES[self._page] if x[2:4] == cmd]
            if not samples:
                samples = [x for x in SAMPLE_RESPONSES if x[2:4] == cmd]
            if not samples:
                raise KeyError(cmd)
            reply[0:len(data)] = bytes.fromhex(samples[0])
            self.preload_read(Report(0, reply))


@pytest.fixture
def mockPsuDevice():
    pid, vid, _, desc, kwargs = CorsairHidPsu.SUPPORTED_DEVICES[0]
    device = _MockPsuDevice(vendor_id=vid, product_id=pid, address='addr')
    return CorsairHidPsu(device, f'Mock {desc}', **kwargs)


def test_corsair_psu_not_totally_broken(mockPsuDevice):

    mockPsuDevice.set_fixed_speed(channel='fan', duty=50)
    report_id, report_data = mockPsuDevice.device.sent[0]
    assert report_id == 0
    assert len(report_data) == 64


def test_corsair_psu_dont_inject_report_ids(mockPsuDevice):

    mockPsuDevice.set_fixed_speed(channel='fan', duty=50)
    report_id, report_data = mockPsuDevice.device.sent[0]
    assert report_id == 0
    assert len(report_data) == 64


def test_corsair_psu_get_status(mockPsuDevice):

    status = { k: (v, u) for k, v, u in mockPsuDevice.get_status() }

    assert status['Current uptime'] == (timedelta(seconds=5522), '')
    assert status['Total uptime'] == (timedelta(days=13, seconds=9122), '')
    assert status['Temperature 1'] == (approx(33.5, rel=1e-3), '°C')
    assert status['Temperature 2'] == (approx(26.5, rel=1e-3), '°C')
    assert status['Fan control mode'] == (FanControlMode.SOFTWARE, '')
    assert status['Fan speed'] == (approx(968, rel=1e-3), 'rpm')
    assert status['Input voltage'] == (approx(230, rel=1e-3), 'V')
    assert status['Total power output'] == (approx(140, rel=1e-3), 'W')
    assert status['+12V OCP mode'] == (OCPMode.MULTI_RAIL, '')
    assert status['+12V output voltage'] == (approx(11.98, rel=1e-3), 'V')
    assert status['+12V output current'] == (approx(10.75, rel=1e-3), 'A')
    assert status['+12V output power'] == (approx(124, rel=1e-3), 'W')
    assert status['+5V output voltage'] == (approx(5.016, rel=1e-3), 'V')
    assert status['+5V output current'] == (approx(1.688, rel=1e-3), 'A')
    assert status['+5V output power'] == (approx(8, rel=1e-3), 'W')
    assert status['+3.3V output voltage'] == (approx(3.297, rel=1e-3), 'V')
    assert status['+3.3V output current'] == (approx(0.562, rel=1e-3), 'A')
    assert status['+3.3V output power'] == (approx(1.5, rel=1e-3), 'W')

    assert status['Estimated input power'] == (approx(153, abs=1), 'W')
    assert status['Estimated efficiency'] == (approx(92, abs=1), '%')

    assert len(status) == 20
