"""liquidctl drivers for NVIDIA graphics cards.

Copyright (C) 2020–2020  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import re

from liquidctl.driver.smbus import SmbusDriver
from liquidctl.error import NotSupportedByDevice

_LOGGER = logging.getLogger(__name__)

_NVIDIA = 0x10de
_EVGA = 0x3842

_NVIDIA_GTX_1080 = 0x1b80


class EvgaPascal(SmbusDriver):
    """Tenth-series (Pascal) NVIDIA graphics card from EVGA."""

    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):
        GTX_1080_FTW = 0x6286
        ADDRESS = 0x49

        if (vendor and vendor != _EVGA) \
                or (address and int(address, base=16) != ADDRESS) \
                or smbus.subsystem_vendor != _EVGA \
                or smbus.vendor != _NVIDIA \
                or smbus.driver != 'nvidia' \
                or release or serial:  # will never match: always None
            return

        supported = [
            (_NVIDIA_GTX_1080, GTX_1080_FTW, "EVGA GTX 1080 FTW (experimental)"),
        ]

        for (dev_id, sub_dev_id, desc) in supported:
            if (product and product != sub_dev_id) \
                    or (match and match.lower() not in desc.lower()) \
                    or smbus.subsystem_device != sub_dev_id \
                    or smbus.device != dev_id \
                    or not smbus.description.startswith('NVIDIA i2c adapter 1 '):
                continue

            dev = cls(smbus, desc, vendor_id=_EVGA, product_id=GTX_1080_FTW,
                      address=ADDRESS)
            _LOGGER.debug('instanced driver for %s', desc)
            yield dev

    def set_color(self, channel, mode, colors, save=False, **kwargs):
        """Set the lighting mode, when applicable, color.

        TODO more details.
        """

        pass

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        _LOGGER.info(f'Status reports not available from {self.description}')
        return []

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()
