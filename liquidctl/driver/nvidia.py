"""liquidctl drivers for NVIDIA graphics cards.

Copyright (C) 2020–2020  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from enum import Enum, unique
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

    ADDRESS = 0x49
    REG_MODE = 0xc
    REG_RED = 0x9
    REG_GREEN = 0xa
    REG_BLUE = 0xb
    REG_PERSIST = 0x23
    PERSIST = 0xe5

    @unique
    class Mode(bytes, Enum):
        def __new__(cls, value, required_colors):
            obj = bytes.__new__(cls, [value])
            obj._value_ = value
            obj.required_colors = required_colors
            return obj

        OFF = (0b000, 0)
        FIXED = (0b001, 1)
        RAINBOW = (0b010, 0)
        BREATHING = (0b101, 1)

        def __str__(self):
            return self.name.capitalize()

    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):
        GTX_1080_FTW = 0x6286

        if (vendor and vendor != _EVGA) \
                or (address and int(address, base=16) != cls.ADDRESS) \
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
                      address=cls.ADDRESS)
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

        if not (unsafe and 'evga_pascal' in unsafe):
            _LOGGER.warning('Device requires `evga_pascal` unsafe flag')
            return []

        mode = self.Mode(self._smbus.read_byte_data(self.ADDRESS, self.REG_MODE))
        status = [('Mode', mode, '')]

        if mode.required_colors > 0:
            r = self._smbus.read_byte_data(self.ADDRESS, self.REG_RED)
            g = self._smbus.read_byte_data(self.ADDRESS, self.REG_GREEN)
            b = self._smbus.read_byte_data(self.ADDRESS, self.REG_BLUE)
            status.append(('Color', f'{r:02x}{g:02x}{b:02x}', ''))

        return status

    def set_color(self, channel, mode, colors, non_volatile=False, **kwargs):
        """Set the RGB lighting mode and, when applicable, color.

        The table bellow summarizes the available channels, modes and their
        associated number of required colors.

        | Channel  | Mode      | Required colors |
        | -------- | --------- | --------------- |
        | led      | off       |               0 |
        | led      | fixed     |               1 |
        | led      | breathing |               1 |
        | led      | rainbow   |               0 |

        The settings configured on the device are normally volatile, and are
        cleared whenever the graphics card is powered down.

        It is possible to store them in non-volatile controller memory by
        passing `non_volatile=True`.  But as this memory has some unknown yet
        limited maximum number of write cycles, volatile settings are
        preferable, if the use case allows for them.
        """

        channel = 'led'
        colors = list(colors)

        try:
            mode = self.Mode[mode.upper()]
        except KeyError:
            raise ValueError(f'Invalid mode: {mode!r}') from None

        if len(colors) < mode.required_colors:
            raise ValueError(f'{mode} mode requires {mode.required_colors} colors')
        elif len(colors) > mode.required_colors:
            _LOGGER.debug('too many colors, dropping to %d', mode.required_colors)
            colors = colors[:mode.required_colors]

        self._smbus.write_byte_data(self.ADDRESS, self.REG_MODE, mode.value)

        for r, g, b in colors:
            self._smbus.write_byte_data(self.ADDRESS, self.REG_RED, r)
            self._smbus.write_byte_data(self.ADDRESS, self.REG_GREEN, g)
            self._smbus.write_byte_data(self.ADDRESS, self.REG_BLUE, b)

        if non_volatile:
            # the following write always fails, but nonetheless induces persistence
            try:
                self._smbus.write_byte_data(self.ADDRESS, self.REG_PERSIST, self.PERSIST)
            except OSError as err:
                _LOGGER.debug('expected OSError when writing to REG_PERSIST: %s', err)
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
