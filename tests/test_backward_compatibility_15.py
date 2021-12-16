"""Test backward compatibility with liquidctl 1.5.x."""

import pytest

from liquidctl.driver.hydro_platinum import HydroPlatinum
from liquidctl.driver.usb import hid


def test_matches_platinum_and_pro_xt_coolers_regardless_of_hydro(monkeypatch):
    mock_match = [
        {'vendor_id': 0x1b1c, 'product_id': 0x0c18},  # H100i Platinum
        {'vendor_id': 0x1b1c, 'product_id': 0x0c19},  # H100i Platinum SE
        {'vendor_id': 0x1b1c, 'product_id': 0x0c17},  # H115i Platinum
        {'vendor_id': 0x1b1c, 'product_id': 0x0c29},  # H60i Pro XT
        {'vendor_id': 0x1b1c, 'product_id': 0x0c20},  # H100i Pro XT
        {'vendor_id': 0x1b1c, 'product_id': 0x0c21},  # H115i Pro XT
        {'vendor_id': 0x1b1c, 'product_id': 0x0c22},  # H150i Pro XT
    ]

    mock_skip = [
        {'vendor_id': 0x1b1c, 'product_id': 0xffff},  # nothing
        {'vendor_id': 0xffff, 'product_id': 0x0c22},  # nothing
    ]

    mock_hids = mock_match + mock_skip

    for info in mock_hids:
        info.setdefault('path', b'')
        info.setdefault('path', b'')
        info.setdefault('serial_number', '')
        info.setdefault('release_number', 0)
        info.setdefault('manufacturer_string', '')
        info.setdefault('product_string', '')
        info.setdefault('usage_page', 0)
        info.setdefault('usage', 0)
        info.setdefault('interface_number', 0)

    def mock_enumerate(vid=0, pid=0):
        return mock_hids

    monkeypatch.setattr(hid, 'enumerate', mock_enumerate)

    def find(match):
        return HydroPlatinum.find_supported_devices(match=match)

    assert len(find('corsair hydro')) == 7
    assert len(find('hydro')) == 7
    assert len(find('corsair')) == 7

    assert len(find('corsair hydro h100i')) == 3
    assert len(find('hydro h100i')) == 3
    assert len(find('corsair h100i')) == 3
