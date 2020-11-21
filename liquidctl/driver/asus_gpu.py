"""liquidctl drivers for ASUS ROG NVIDIA graphics cards.

Copyright (C) 2020–2020  Marshall Asch and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import re

from liquidctl.driver.smbus import SmbusDriver
from liquidctl.error import NotSupportedByDevice

_LOGGER = logging.getLogger(__name__)

_NVIDIA = 0x10de                # vendor
_ASUS = 0x1043                  # subsystem vendor

_ROG_RTX_2080_TI = 0x1e07       # device id
_RTX_2080_TI_FTW = 0x866a       # subsystem device



class RogTuring(SmbusDriver):
    """Twenty-series (Turing) NVIDIA graphics card from ASUS ROG."""

    ADDRESSES = [0x29, 0x2a, 0x60]
    RED_REG = 0x04
    BLUE_REG = 0x05
    GREEN_REG = 0x06
    MODE_REG = 0x07
    SYNC_REG = 0x0c     # unused
    APPLY_REG = 0x0e

    _ASUS_GPU_MAGIC_VALUE = 0x1589

    MODE_FIXED = 0x01
    MODE_BREATHING = 0x02
    MODE_FLASH = 0x03
    MODE_RAINBOW = 0x04


    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):

        if (vendor and vendor != _NVIDIA) \
                or (address and int(address, base=16) not in cls.ADDRESSES) \
                or smbus.subsystem_vendor != _ASUS \
                or smbus.vendor != _NVIDIA \
                or smbus.driver != 'nvidia' \
                or release or serial:  # will never match: always None
            return

        supported = [
            (_ROG_RTX_2080_TI, _RTX_2080_TI_FTW, "ASUS ROG RTX 2080ti (experimental)"),
        ]

        for (dev_id, sub_dev_id, desc) in supported:
            if (product and product != sub_dev_id) \
                    or (match and match.lower() not in desc.lower()) \
                    or smbus.subsystem_device != sub_dev_id \
                    or smbus.device != dev_id \
                    or not smbus.description.startswith('NVIDIA i2c adapter 1 '):
                continue

            for address in cls.ADDRESSES:
                val1=0
                val2=0
                try:
                    smbus.open()
                    val1 = smbus.read_byte_data(address, 0x20)
                    val2 = smbus.read_byte_data(address, 0x21)
                    smbus.close()
                except:
                    _LOGGER.debug(f'Device not found at {address}')

                if val1 << 8 | val2 == cls._ASUS_GPU_MAGIC_VALUE:
                    dev = cls(smbus, desc, vendor_id=_ASUS, product_id=_RTX_2080_TI_FTW,
                        address=address)
                    _LOGGER.debug('instanced driver for %s', desc)
                    yield dev

    def get_status(self, verbose=False, unsafe=None, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        # only RGB lighting information can be fetched for now; as that isn't
        # super interesting, only enable it in verbose mode

        if not verbose:
            return []

        if not (unsafe and 'rog_strix' in unsafe):
            _LOGGER.warning('Device requires `rog_strix` unsafe flag')
            return []

        self._smbus.open()
        mode =  self._smbus.read_byte_data(self._address, self.MODE_REG)
        red = self._smbus.read_byte_data(self._address, self.RED_REG)
        blue = self._smbus.read_byte_data(self._address, self.BLUE_REG)
        green = self._smbus.read_byte_data(self._address, self.GREEN_REG)
        self._smbus.close()

        return [
            ('Mode', mode, ''),
            ('Color', f'#{red:02x}{blue:02x}{green:02x}', ''),
        ]

    def set_color(self, channel, mode, colors, save=False, **kwargs):
        """Set the lighting mode, when applicable, color.

        TODO more details.
        """

        pass

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()
