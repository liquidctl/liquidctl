import pytest
from _testutils import VirtualBusDevice, VirtualControlMode

import json
import sys

import liquidctl.cli


@pytest.fixture
def main(monkeypatch, capsys):
    """Return a function f(*args) to run main with `args` as `sys.argv`."""
    def call_with_args(*args):
        monkeypatch.setattr(sys, 'argv', list(args))
        try:
            liquidctl.cli.main()
        except SystemExit as exit:
            code = exit.code
        else:
            code = 0
        out, err = capsys.readouterr()
        return code, out, err
    return call_with_args


def test_json_list(main):
    code, out, _ = main('test', '--bus', 'virtual', 'list', '--json')
    assert code == 0

    got = json.loads(out)
    exp = [
        {
            'description': 'Virtual Bus Device',
            'vendor_id': 0x1234,
            'product_id': 0xabcd,
            'release_number': None,
            'serial_number': None,
            'bus': 'virtual',
            'address': 'virtual_address',
            'port': None,
            'driver': 'VirtualBusDevice',
            'experimental': False,
        }
    ]
    assert got == exp


def test_json_initialize(main):
    code, out, _ = main('test', '--bus', 'virtual', 'initialize', '--json')
    assert code == 0

    got = json.loads(out)
    exp = [
        {
            'bus': 'virtual',
            'address': 'virtual_address',
            'description': 'Virtual Bus Device',
            'status': [
                { 'key': 'Firmware version', 'value': '3.14.16', 'unit': '' },
            ]
        }
    ]
    assert got == exp


def test_json_status(main):
    code, out, _ = main('test', '--bus', 'virtual', 'status', '--json')
    assert code == 0

    got = json.loads(out)
    exp = [
        {
            'bus': 'virtual',
            'address': 'virtual_address',
            'description': 'Virtual Bus Device',
            'status': [
                { 'key': 'Temperature', 'value': 30.4, 'unit': '°C' },
                { 'key': 'Fan control mode', 'value': 'VirtualControlMode.QUIET', 'unit': '' },
                { 'key': 'Animation', 'value': None, 'unit': '' },
                { 'key': 'Uptime', 'value': 66192.0, 'unit': 's' },
                { 'key': 'Hardware mode', 'value': True, 'unit': '' },
            ]
        }
    ]
    assert got == exp


@pytest.mark.parametrize('options', [{}, {'temperature_sensor': 0}, {'temperature_sensor': 1}])
def test_temperature_sensor_forwarded_to_speed_profile(main, monkeypatch, options):
    device = VirtualBusDevice()
    monkeypatch.setattr(liquidctl.cli, 'find_liquidctl_devices', lambda **kwargs: [device])
    argv = ['liquidctl', 'set', 'fan1', 'speed', '25', '50', '45', '100']
    if options:
        argv += ['--temperature-sensor', str(options['temperature_sensor'])]

    code, _, _ = main(*argv)
    assert code == 0

    args, kwargs = device.call_args['set_speed_profile']
    assert args[0] == 'fan1'
    assert list(args[1]) == [(25, 50), (45, 100)]
    assert {key: value for key, value in kwargs.items() if key == 'temperature_sensor'} == options
