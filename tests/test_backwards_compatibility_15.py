"""Test backwards compatibility with liquidctl 1.5.0."""

import pytest

from liquidctl.driver.hydro_platinum import HydroPlatinum
from liquidctl.driver.usb import hid


def test_matches_platinum_and_pro_xt_coolers_regardless_of_hydro(monkeypatch):
    mock_match = [
        {'vendor_id': 0x1b1c, 'product_id': 0x0c18},  # H100i Platinum
        {'vendor_id': 0x1b1c, 'product_id': 0x0c19},  # H100i Platinum SE
        {'vendor_id': 0x1b1c, 'product_id': 0x0c17},  # H115i Platinum
        {'vendor_id': 0x1b1c, 'product_id': 0x0c20},  # H100i Pro XT
        {'vendor_id': 0x1b1c, 'product_id': 0x0c21},  # H115i Pro XT
        {'vendor_id': 0x1b1c, 'product_id': 0x0c22},  # H150i Pro XT
    ]

    mock_skip = [
        {'vendor_id': 0x1b1c, 'product_id': 0xffff},  # nothing
        {'vendor_id': 0xffff, 'product_id': 0x0c22},  # nothing
    ]

    ignored_infos = {
        'path': b'',
        'serial_number': '',
        'release_number': 0,
        'manufacturer_string': '',
        'product_string': '',
        'usage_page': 0,
        'usage': 0,
        'interface_number': 0
    }

    def mock_enumerate(vid=0, pid=0):
        return [infos | ignored_infos for infos in mock_match + mock_skip]

    monkeypatch.setattr(hid, 'enumerate', mock_enumerate)

    def find(match):
        return HydroPlatinum.find_supported_devices(match=match)

    assert len(find('corsair hydro')) == 6
    assert len(find('hydro')) == 6
    assert len(find('corsair')) == 6

    assert len(find('corsair hydro h100i')) == 3
    assert len(find('hydro h100i')) == 3
    assert len(find('corsair h100i')) == 3
