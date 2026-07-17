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


def test_set_screen_forwards_optional_interval():
    class Device:
        def __init__(self):
            self.calls = []

        def set_screen(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    device = Device()
    liquidctl.cli._device_set_screen(
        device,
        {
            '<channel>': 'lcd',
            '<mode>': 'stats',
            '<value>': 'dashboard.json',
            '<interval>': '5',
        },
    )

    assert device.calls == [
        (('lcd', 'stats', 'dashboard.json'), {'interval': '5'}),
    ]
