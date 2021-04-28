import pytest

import json
import sys
from datetime import timedelta
from enum import Enum, unique

import liquidctl.cli
from liquidctl.driver.base import *


@unique
class ControlMode(Enum):
    QUIET = 0x0
    BALANCED = 0x1
    EXTREME = 0x2


class Virtual(BaseDriver):
    def __init__(self, **kwargs):
        pass

    def connect(self, **kwargs):
        return self

    def disconnect(self, **kwargs):
        pass

    def initialize(self, **kwargs):
        return self.get_status(**kwargs)

    def get_status(self, **kwargs):
        return [
            ('Temperature', 30.4, '°C'),
            ('Fan control mode', ControlMode.QUIET, ''),
            ('Animation', None, ''),
            ('Uptime', timedelta(hours=18, minutes=23, seconds=12), ''),
            ('Hardware mode', True, ''),
        ]

    @property
    def description(self):
        return 'Virtual device (experimental)'

    @property
    def vendor_id(self):
        return 0x1234

    @property
    def product_id(self):
        return 0xabcd

    @property
    def release_number(self):
        None

    @property
    def serial_number(self):
        raise OSError()

    @property
    def bus(self):
        return 'virtual'

    @property
    def address(self):
        return 'virtual_address'

    @property
    def port(self):
        return None


class VirtualBus(BaseBus):
    def find_devices(self, **kwargs):
        yield from [Virtual()]


@pytest.fixture
def main(monkeypatch, capsys):
    """Return a function f(*args) to run main with `args` as `sys.argv`."""
    def call_with_args(*args):
        monkeypatch.setattr(sys, 'argv', args)
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
            'description': 'Virtual device',
            'vendor_id': 0x1234,
            'product_id': 0xabcd,
            'release_number': None,
            'serial_number': None,
            'bus': 'virtual',
            'address': 'virtual_address',
            'port': None,
            'driver': 'Virtual',
            'experimental': True,
        }
    ]
    assert got == exp


def assert_json_status_like(out):
    got = json.loads(out)
    exp = [
        {
            'bus': 'virtual',
            'address': 'virtual_address',
            'description': 'Virtual device',
            'status': [
                { 'key': 'Temperature', 'value': 30.4, 'unit': '°C' },
                { 'key': 'Fan control mode', 'value': 'ControlMode.QUIET', 'unit': '' },
                { 'key': 'Animation', 'value': None, 'unit': '' },
                { 'key': 'Uptime', 'value': 66192.0, 'unit': 's' },
                { 'key': 'Hardware mode', 'value': True, 'unit': '' },
            ]
        }
    ]
    assert got == exp


def test_json_initialize(main):
    code, out, _ = main('test', '--bus', 'virtual', 'initialize', '--json')
    assert code == 0
    assert_json_status_like(out)


def test_json_status(main):
    code, out, _ = main('test', '--bus', 'virtual', 'status', '--json')
    assert code == 0
    assert_json_status_like(out)
