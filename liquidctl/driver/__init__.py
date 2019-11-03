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

---

Initialization of the drivers and buses package.
Copyright (C) 2018–2019  Jonas Malaco
Copyright (C) 2018–2019  each contribution's author

This file is part of liquidctl.

liquidctl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

liquidctl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import liquidctl.driver.asetek
import liquidctl.driver.corsair_hid_psu
import liquidctl.driver.kraken_two
import liquidctl.driver.nzxt_smart_device
import liquidctl.driver.seasonic

from liquidctl.driver.base import BaseBus, find_all_subclasses


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
    buses = sorted(find_all_subclasses(BaseBus), key=lambda x: x.__name__)
    num = 0
    for bus_cls in buses:
        for dev in  bus_cls().find_devices(**kwargs):
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
