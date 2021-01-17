"""Drivers and buses package for liquidctl.

The typical use case of generic scripts and interfaces – including the
liquidctl CLI – is to instantiate drivers for all known devices found on the
system.

    from liquidctl.driver import *
    for dev in find_liquidctl_devices():
        print(dev.description)

Is also possible to find devices compatible with a specific driver.

    from liquidctl.driver.kraken_two import KrakenTwoDriver
    for dev in KrakenTwoDriver.find_supported_devices():
        print(dev.description)

Copyright (C) 2018–2021  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import sys

from liquidctl.driver.base import BaseBus, find_all_subclasses

from liquidctl.driver import asetek
from liquidctl.driver import corsair_hid_psu
from liquidctl.driver import hydro_platinum
from liquidctl.driver import commander_pro
from liquidctl.driver import kraken2
from liquidctl.driver import kraken3
from liquidctl.driver import nzxt_epsu
from liquidctl.driver import rgb_fusion2
from liquidctl.driver import smart_device

if sys.platform == 'linux':
    from liquidctl.driver import ddr4
    from liquidctl.driver import nvidia


def find_liquidctl_devices(pick=None, **kwargs):
    """Find devices and instantiate corresponding liquidctl drivers.

    Probes all buses and drivers that have been loaded at the time of the call
    and yields driver instances.

    Filter conditions can be passed through to the buses and drivers via
    `**kwargs`.  A driver instance will be yielded for each compatible device
    that matches the supplied filter conditions.

    If `pick` is passed, only the driver instance for the `(pick + 1)`-th
    matched device will be yielded.
    """
    buses = sorted(find_all_subclasses(BaseBus),
                   key=lambda x: (x.__module__, x.__name__))
    num = 0
    for bus_cls in buses:
        for dev in bus_cls().find_devices(**kwargs):
            if pick is not None:
                if num == pick:
                    yield dev
                    return
                num += 1
            else:
                yield dev


__all__ = [
    'find_liquidctl_devices',
]

# allow old driver imports to continue to work by manually placing these into
# the module cache, so import liquidctl.driver.foo does not need to
# check the filesystem for foo
sys.modules['liquidctl.driver.kraken_two'] = kraken2
sys.modules['liquidctl.driver.nzxt_smart_device'] = smart_device
sys.modules['liquidctl.driver.seasonic'] = nzxt_epsu
