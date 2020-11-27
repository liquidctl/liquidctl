"""liquidctl drivers for NVIDIA graphics cards.
liquidctl drivers for ASUS Strix RTX 2080 Ti OC graphics card.

Copyright (C) 2020–2020  Jonas Malacoi, Marshall Asch and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from enum import Enum, unique
import logging

from liquidctl.driver.smbus import SmbusDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import check_unsafe

_LOGGER = logging.getLogger(__name__)

NVIDIA = 0x10de                 # vendor ID


# Device id
NVIDIA_GTX_1080 = 0x1b80
RTX_2080_TI_REV_A = 0x1e07     # device id NOTE: 0x1E04 is also a possible value see
                                # https://www.nv-drivers.eu/nvidia-all-devices.html
#  sub system vendors
EVGA = 0x3842
ASUS = 0x1043


# Subsystem devices
EVGA_GTX_1080_FTW = 0x6286
STRIX_RTX_2080_TI_OC = 0x866a

class EvgaPascal(SmbusDriver):
    """NVIDIA series 10 (Pascal) graphics card from EVGA."""

    _REG_MODE = 0x0c
    _REG_RED = 0x09
    _REG_GREEN = 0x0a
    _REG_BLUE = 0x0b
    _REG_PERSIST = 0x23
    _PERSIST = 0xe5

    @unique
    class Mode(bytes, Enum):
        def __new__(cls, value, required_colors):
            obj = bytes.__new__(cls, [value])
            obj._value_ = value
            obj.required_colors = required_colors
            return obj

        OFF = (0x00, 0)
        FIXED = (0x01, 1)
        RAINBOW = (0x02, 0)
        BREATHING = (0x05, 1)

        def __str__(self):
            return self.name.capitalize()

    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):
        ADDRESS = 0x49

        if (vendor and vendor != EVGA) \
                or (address and int(address, base=16) != ADDRESS) \
                or smbus.parent_subsystem_vendor != EVGA \
                or smbus.parent_vendor != NVIDIA \
                or smbus.parent_driver != 'nvidia' \
                or release or serial:  # will never match: always None
            return

        supported = [
            (NVIDIA_GTX_1080, EVGA_GTX_1080_FTW, "EVGA GTX 1080 FTW (experimental)"),
        ]

        for (dev_id, sub_dev_id, desc) in supported:
            if (product and product != sub_dev_id) \
                    or (match and match.lower() not in desc.lower()) \
                    or smbus.parent_subsystem_device != sub_dev_id \
                    or smbus.parent_device != dev_id \
                    or not smbus.description.startswith('NVIDIA i2c adapter 1 '):
                continue

            dev = cls(smbus, desc, vendor_id=EVGA, product_id=EVGA_GTX_1080_FTW,
                      address=ADDRESS)
            _LOGGER.debug('instanced driver for %s', desc)
            yield dev

    def get_status(self, verbose=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        # only RGB lighting information can be fetched for now; as that isn't
        # super interesting, only enable it in verbose mode

        if not verbose:
            return []

        if not check_unsafe('smbus', 'evga_pascal', **kwargs):
            _LOGGER.warning("%s: nothing to return, requires unsafe features "
                            "'smbus,evga_pascal'",  self.description)
            return []

        mode = self.Mode(self._smbus.read_byte_data(self._address, self._REG_MODE))
        status = [('Mode', mode, '')]

        if mode.required_colors > 0:
            r = self._smbus.read_byte_data(self._address, self._REG_RED)
            g = self._smbus.read_byte_data(self._address, self._REG_GREEN)
            b = self._smbus.read_byte_data(self._address, self._REG_BLUE)
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

        check_unsafe('smbus', 'evga_pascal', error=True, **kwargs)

        channel = 'led'
        colors = list(colors)

        try:
            mode = self.Mode[mode.upper()]
        except KeyError:
            raise ValueError(f'Invalid mode: {mode!r}') from None

        if len(colors) < mode.required_colors:
            raise ValueError(f'{mode} mode requires {mode.required_colors} colors')

        if len(colors) > mode.required_colors:
            _LOGGER.debug('too many colors, dropping to %d', mode.required_colors)
            colors = colors[:mode.required_colors]

        self._smbus.write_byte_data(self._address, self._REG_MODE, mode.value)

        for r, g, b in colors:
            self._smbus.write_byte_data(self._address, self._REG_RED, r)
            self._smbus.write_byte_data(self._address, self._REG_GREEN, g)
            self._smbus.write_byte_data(self._address, self._REG_BLUE, b)

        if non_volatile:
            # the following write always fails, but nonetheless induces persistence
            try:
                self._smbus.write_byte_data(self._address, self._REG_PERSIST, self._PERSIST)
            except OSError as err:
                _LOGGER.debug('expected OSError when writing to _REG_PERSIST: %s', err)

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()



class RogTuring(SmbusDriver):
    """Twenty-series (Turing) NVIDIA graphics card from ASUS ROG."""

    _REG_RED = 0x04
    _REG_GREEN = 0x05
    _REG_BLUE = 0x06
    _REG_MODE = 0x07
    # SYNC_REG = 0x0c     # unused
    _REG_APPLY = 0x0e

    _ASUS_GPU_MAGIC_VALUE = 0x1589
    _ASUS_GPU_APPLY_VAL = 0x01

    @unique
    class Mode(bytes, Enum):
        def __new__(cls, value, required_colors):
            obj = bytes.__new__(cls, [value])
            obj._value_ = value
            obj.required_colors = required_colors
            return obj

        OFF = (0x00, 0)     # This is not a real mode, fixed is sent with RGB = 0
        FIXED = (0x01, 1)
        BREATHING = (0x02, 1)
        FLASH = (0x03, 1)
        RAINBOW = (0x04, 0)

        def __str__(self):
            return self.name.capitalize()

    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):

        ADDRESSES = [0x29, 0x2a, 0x60]


        if (vendor and vendor != ASUS) \
                or (address and int(address, base=16) not in ADDRESSES) \
                or smbus.parent_subsystem_vendor != ASUS \
                or smbus.parent_vendor != NVIDIA \
                or smbus.parent_driver != 'nvidia' \
                or release or serial:  # will never match: always None
            return

        supported = [
            (RTX_2080_TI_REV_A, STRIX_RTX_2080_TI_OC, "ASUS Strix RTX 2080 Ti OC (experimental)"),
        ]

        for (dev_id, sub_dev_id, desc) in supported:
            if (product and product != sub_dev_id) \
                    or (match and match.lower() not in desc.lower()) \
                    or smbus.parent_subsystem_device != sub_dev_id \
                    or smbus.parent_device != dev_id \
                    or not smbus.description.startswith('NVIDIA i2c adapter 1 '):
                continue

            if not check_unsafe('smbus', 'rog_turing', **kwargs):
                _LOGGER.warning("%s: assuming driver found at address %02x "
                            "'smbus,rog_turing'",  desc, 0x2a)

                dev = cls(smbus, desc, vendor_id=ASUS, product_id=dev_id,
                          address=0x2a)   # default picked the address that works for my device
                yield dev
                return

            for address in ADDRESSES:
                val1 = 0
                val2 = 0

                smbus.open()
                try:
                    val1 = smbus.read_byte_data(address, 0x20)
                    val2 = smbus.read_byte_data(address, 0x21)
                except:
                    pass
                smbus.close()

                if val1 << 8 | val2 == cls._ASUS_GPU_MAGIC_VALUE:
                    dev = cls(smbus, desc, vendor_id=ASUS, product_id=dev_id,
                              address=address)
                    _LOGGER.debug(f'instanced driver for {desc} at address {address}')
                    yield dev

    def get_status(self, verbose=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        # only RGB lighting information can be fetched for now; as that isn't
        # super interesting, only enable it in verbose mode

        if not verbose:
            return []

        if not check_unsafe('smbus', 'rog_turing', **kwargs):
            _LOGGER.warning("%s: nothing to return, requires unsafe features "
                            "'smbus,rog_turing'",  self.description)
            return []

        mode = self._smbus.read_byte_data(self._address, self._REG_MODE)
        red = self._smbus.read_byte_data(self._address, self._REG_RED)
        green = self._smbus.read_byte_data(self._address, self._REG_GREEN)
        blue = self._smbus.read_byte_data(self._address, self._REG_BLUE)

        # check if the mode is `OFF`
        if red == green == blue == 0:
            mode = 0

        mode = self.Mode(mode)
        status = [('Mode', str(mode), '')]

        if mode.required_colors > 0:
            status.append(('Color', f'{red:02x}{green:02x}{blue:02x}', ''))

        return status

    def set_color(self, channel, mode, colors, non_volatile=False, **kwargs):
        """Set the lighting mode, when applicable, color.

        The table bellow summarizes the available channels, modes and their
        associated number of required colors.

        | Channel  | Mode      | Required colors |
        | -------- | --------- | --------------- |
        | led      | off       |               0 |
        | led      | fixed     |               1 |
        | led      | flash     |               1 |
        | led      | breathing |               1 |
        | led      | rainbow   |               0 |

        The settings configured on the device are persistent across power off without
        the use of the non_volatile argument.

        It is possible to store them in non-volatile controller memory by
        passing `non_volatile=True`.  But as this memory has some unknown yet
        limited maximum number of write cycles, volatile settings are
        preferable, if the use case allows for them.

        """

        check_unsafe('smbus', 'rog_turing', error=True, **kwargs)

        colors = list(colors)

        try:
            mode = self.Mode[mode.upper()]
        except KeyError:
            raise ValueError(f'Invalid mode: {mode!r}') from None

        if len(colors) < mode.required_colors:
            raise ValueError(f'{mode} mode requires {mode.required_colors} colors')

        if len(colors) > mode.required_colors:
            _LOGGER.debug('too many colors, dropping to %d', mode.required_colors)
            colors = colors[:mode.required_colors]

        if mode == self.Mode.OFF:
            self._smbus.write_byte_data(self._address, self._REG_MODE, self.Mode.FIXED.value)
            self._smbus.write_byte_data(self._address, self._REG_RED, 0x00)
            self._smbus.write_byte_data(self._address, self._REG_GREEN, 0x00)
            self._smbus.write_byte_data(self._address, self._REG_BLUE, 0x00)
        else:
            self._smbus.write_byte_data(self._address, self._REG_MODE, mode.value)
            for r, g, b in colors:
                self._smbus.write_byte_data(self._address, self._REG_RED, r)
                self._smbus.write_byte_data(self._address, self._REG_GREEN, g)
                self._smbus.write_byte_data(self._address, self._REG_BLUE, b)

        if non_volatile:
            self._smbus.write_byte_data(self._address, self._REG_APPLY, self._ASUS_GPU_APPLY_VAL)

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()
