import pytest
from _testutils import MockHidapiDevice, Report
from pytest import approx

from datetime import timedelta

from liquidctl.driver.corsair_hid_psu import CorsairHidPsu, OCPMode, FanControlMode
from liquidctl.driver.hwmon import HwmonDevice


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


class MockPsu(MockHidapiDevice):
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
def mock_psu():
    pid, vid, _, desc, kwargs = CorsairHidPsu.SUPPORTED_DEVICES[0]
    device = MockPsu(vendor_id=vid, product_id=pid, address='addr')
    return CorsairHidPsu(device, f'Mock {desc}', **kwargs)


def test_not_totally_broken(mock_psu):

    mock_psu.set_fixed_speed(channel='fan', duty=50)
    report_id, report_data = mock_psu.device.sent[0]
    assert report_id == 0
    assert len(report_data) == 64


def test_dont_inject_report_ids(mock_psu):

    mock_psu.set_fixed_speed(channel='fan', duty=50)
    report_id, report_data = mock_psu.device.sent[0]
    assert report_id == 0
    assert len(report_data) == 64


@pytest.mark.parametrize('has_hwmon,direct_access', [(False, False), (True, True), (True, False)])
def test_initializes(mock_psu, has_hwmon, direct_access, tmp_path):
    if has_hwmon:
        mock_psu._hwmon = HwmonDevice('mock_module', tmp_path)

    # TODO check the result
    _ = mock_psu.initialize(direct_access=direct_access)

    writes = len(mock_psu.device.sent)
    if not has_hwmon or direct_access:
        assert writes > 0
    else:
        assert writes == 0


@pytest.mark.parametrize('has_hwmon,direct_access', [(False, False), (True, True)])
def test_reads_status_directly(mock_psu, has_hwmon, direct_access):
    if has_hwmon:
        mock_psu._hwmon = HwmonDevice(None, None)

    got = mock_psu.get_status(direct_access=direct_access)

    expected = [
        ('Current uptime', timedelta(seconds=5522), ''),
        ('Total uptime', timedelta(days=13, seconds=9122), ''),
        ('Temperature 1', approx(33.5, rel=1e-3), '°C'),
        ('Temperature 2', approx(26.5, rel=1e-3), '°C'),
        ('Fan control mode', FanControlMode.SOFTWARE, ''),
        ('Fan speed', approx(968, rel=1e-3), 'rpm'),
        ('Input voltage', approx(230, rel=1e-3), 'V'),
        ('Total power output', approx(140, rel=1e-3), 'W'),
        ('+12V OCP mode', OCPMode.MULTI_RAIL, ''),
        ('+12V output voltage', approx(11.98, rel=1e-3), 'V'),
        ('+12V output current', approx(10.75, rel=1e-3), 'A'),
        ('+12V output power', approx(124, rel=1e-3), 'W'),
        ('+5V output voltage', approx(5.016, rel=1e-3), 'V'),
        ('+5V output current', approx(1.688, rel=1e-3), 'A'),
        ('+5V output power', approx(8, rel=1e-3), 'W'),
        ('+3.3V output voltage', approx(3.297, rel=1e-3), 'V'),
        ('+3.3V output current', approx(0.562, rel=1e-3), 'A'),
        ('+3.3V output power', approx(1.5, rel=1e-3), 'W'),
        ('Estimated input power', approx(153, abs=1), 'W'),
        ('Estimated efficiency', approx(92, abs=1), '%'),
    ]

    assert sorted(got) == sorted(expected)


def test_reads_status_from_hwmon(mock_psu, tmp_path):
    mock_psu.device.write = None  # make sure we aren't writing to the mock device

    mock_psu._hwmon = HwmonDevice('mock_module', tmp_path)
    (tmp_path / 'temp1_input').write_text('33500\n')
    (tmp_path / 'temp2_input').write_text('26500\n')
    (tmp_path / 'fan1_input').write_text('968\n')
    (tmp_path / 'in0_input').write_text('230000\n')
    (tmp_path / 'power1_input').write_text('140000000\n')
    (tmp_path / 'in1_input').write_text('11980\n')
    (tmp_path / 'curr2_input').write_text('10750\n')
    (tmp_path / 'power2_input').write_text('124000000\n')
    (tmp_path / 'in2_input').write_text('5016\n')
    (tmp_path / 'curr3_input').write_text('1688\n')
    (tmp_path / 'power3_input').write_text('8000000\n')
    (tmp_path / 'in3_input').write_text('3297\n')
    (tmp_path / 'curr4_input').write_text('562\n')
    (tmp_path / 'power4_input').write_text('1500000\n')

    got = mock_psu.get_status()

    expected = [
        ('Temperature 1', approx(33.5, rel=1e-3), '°C'),
        ('Temperature 2', approx(26.5, rel=1e-3), '°C'),
        ('Fan speed', approx(968, rel=1e-3), 'rpm'),
        ('Input voltage', approx(230, rel=1e-3), 'V'),
        ('Total power output', approx(140, rel=1e-3), 'W'),
        ('+12V output voltage', approx(11.98, rel=1e-3), 'V'),
        ('+12V output current', approx(10.75, rel=1e-3), 'A'),
        ('+12V output power', approx(124, rel=1e-3), 'W'),
        ('+5V output voltage', approx(5.016, rel=1e-3), 'V'),
        ('+5V output current', approx(1.688, rel=1e-3), 'A'),
        ('+5V output power', approx(8, rel=1e-3), 'W'),
        ('+3.3V output voltage', approx(3.297, rel=1e-3), 'V'),
        ('+3.3V output current', approx(0.562, rel=1e-3), 'A'),
        ('+3.3V output power', approx(1.5, rel=1e-3), 'W'),
        ('Estimated input power', approx(153, abs=1), 'W'),
        ('Estimated efficiency', approx(92, abs=1), '%'),
    ]

    assert sorted(got) == sorted(expected)
