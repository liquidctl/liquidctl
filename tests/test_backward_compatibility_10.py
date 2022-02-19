"""Test API backward compatibility with liquidctl 1.0.x.

While at the time all APIs were undocumented, we choose to support the use
cases from GKraken as that software is a substantial contribution to the
community.
"""

import pytest
from test_kraken2 import mockKrakenXDevice

from liquidctl.version import __version__

SPECTRUM = [
    (235, 77, 40),
    (255, 148, 117),
    (126, 66, 45),
    (165, 87, 0),
    (56, 193, 66),
    (116, 217, 170),
    (166, 158, 255),
    (208, 0, 122)
]


def test_pre11_apis_deprecated_super_mode(mockKrakenXDevice):
    # deprecated in favor of super-fixed, super-breathing and super-wave
    mockKrakenXDevice.set_color('sync', 'super', [(128, 0, 255)] + SPECTRUM, 'normal')
