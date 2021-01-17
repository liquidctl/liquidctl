"""liquidctl drivers for NVIDIA graphics cards.

Copyright (C) 2020–2021  Jonas Malaco, Marshall Asch and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from enum import Enum, unique
import logging

from liquidctl.driver.smbus import SmbusDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import check_unsafe

_LOGGER = logging.getLogger(__name__)

# vendor, devices
NVIDIA = 0x10de
NVIDIA_GTX_1080 = 0x1b80
NVIDIA_RTX_2080_TI_REV_A = 0x1e07
# https://www.nv-drivers.eu/nvidia-all-devices.html
# https://pci-ids.ucw.cz/pci.ids

# subsystem vendor ASUS, subsystem devices
ASUS = 0x1043
ASUS_STRIX_RTX_2080_TI_OC = 0x866a

# subsystem vendor EVGA, subsystem devices
EVGA = 0x3842
EVGA_GTX_1080_FTW = 0x6286


@unique
class _ModeEnum(bytes, Enum):
    def __new__(cls, value, required_colors):
        obj = bytes.__new__(cls, [value])
        obj._value_ = value
        obj.required_colors = required_colors
        return obj

    def __str__(self):
        return self.name.capitalize()


class EvgaPascal(SmbusDriver):
    """NVIDIA series 10 (Pascal) graphics card from EVGA."""

    _REG_MODE = 0x0c
    _REG_RED = 0x09
    _REG_GREEN = 0x0a
    _REG_BLUE = 0x0b
    _REG_PERSIST = 0x23
    _PERSIST = 0xe5

    @unique
    class Mode(_ModeEnum):
        OFF = (0x00, 0)
        FIXED = (0x01, 1)
        RAINBOW = (0x02, 0)
        BREATHING = (0x05, 1)

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
            (NVIDIA_GTX_1080, EVGA_GTX_1080_FTW, 'EVGA GTX 1080 FTW'),
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

        if not check_unsafe('smbus', **kwargs):
            _LOGGER.warning("%s: nothing to return, requires unsafe features 'smbus'",
                            self.description)
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
        cleared whenever the graphics card is powered down (OS and UEFI power
        saving settings can affect when this happens).

        It is possible to store them in non-volatile controller memory by
        passing `non_volatile=True`.  But as this memory has some unknown yet
        limited maximum number of write cycles, volatile settings are
        preferable, if the use case allows for them.
        """

        check_unsafe('smbus', error=True, **kwargs)

        colors = list(colors)

        try:
            mode = self.Mode[mode.upper()]
        except KeyError:
            raise ValueError(f'invalid mode: {mode!r}') from None

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
    """NVIDIA series 20 (Turing) graphics card from ASUS."""

    _REG_RED = 0x04
    _REG_GREEN = 0x05
    _REG_BLUE = 0x06
    _REG_MODE = 0x07
    _REG_APPLY = 0x0e
    _SYNC_REG = 0x0c  # unused

    _SENTINEL_ADDRESS = 0xffff  # intentionally invalid
    _ASUS_GPU_APPLY_VAL = 0x01

    @unique
    class Mode(_ModeEnum):
        OFF = (0x00, 0)  # not a real mode; fixed is sent with RGB = 0
        FIXED = (0x01, 1)
        BREATHING = (0x02, 1)
        FLASH = (0x03, 1)
        RAINBOW = (0x04, 0)

    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):

        ADDRESSES = [0x29, 0x2a, 0x60]
        ASUS_GPU_MAGIC_VALUE = 0x1589

        if (vendor and vendor != ASUS) \
                or (address and int(address, base=16) not in ADDRESSES) \
                or smbus.parent_subsystem_vendor != ASUS \
                or smbus.parent_vendor != NVIDIA \
                or smbus.parent_driver != 'nvidia' \
                or release or serial:  # will never match: always None
            return

        supported = [
            (NVIDIA_RTX_2080_TI_REV_A, ASUS_STRIX_RTX_2080_TI_OC,
                'ASUS Strix RTX 2080 Ti OC'),
        ]

        for (dev_id, sub_dev_id, desc) in supported:
            if (product and product != sub_dev_id) \
                    or (match and match.lower() not in desc.lower()) \
                    or smbus.parent_subsystem_device != sub_dev_id \
                    or smbus.parent_device != dev_id \
                    or not smbus.description.startswith('NVIDIA i2c adapter 1 '):
                continue

            selected_address = None

            if check_unsafe('smbus', **kwargs):
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

                    if val1 << 8 | val2 == ASUS_GPU_MAGIC_VALUE:
                        selected_address = address
                        break
            else:
                selected_address = cls._SENTINEL_ADDRESS
                _LOGGER.debug('unsafe features not enabled, using sentinel address')

            if selected_address is not None:
                dev = cls(smbus, desc, vendor_id=ASUS, product_id=dev_id,
                          address=selected_address)
                _LOGGER.debug('instanced driver for %s at address %02x',
                              desc, selected_address)
                yield dev

    def get_status(self, verbose=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        # only RGB lighting information can be fetched for now; as that isn't
        # super interesting, only enable it in verbose mode

        if not verbose:
            return []

        if not check_unsafe('smbus', **kwargs):
            _LOGGER.warning("%s: nothing to return, requires unsafe features "
                            "'smbus'", self.description)
            return []

        assert self._address != self._SENTINEL_ADDRESS, \
               'invalid address (probing may not have had access to SMbus)'

        mode = self._smbus.read_byte_data(self._address, self._REG_MODE)
        red = self._smbus.read_byte_data(self._address, self._REG_RED)
        green = self._smbus.read_byte_data(self._address, self._REG_GREEN)
        blue = self._smbus.read_byte_data(self._address, self._REG_BLUE)

        # emulate `OFF` both ways
        if red == green == blue == 0:
            mode = 0

        mode = self.Mode(mode)
        status = [('Mode', mode, '')]

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

        The settings configured on the device are normally volatile, and are
        cleared whenever the graphics card is powered down (OS and UEFI power
        saving settings can affect when this happens).

        It is possible to store them in non-volatile controller memory by
        passing `non_volatile=True`.  But as this memory has some unknown yet
        limited maximum number of write cycles, volatile settings are
        preferable, if the use case allows for them.

        """

        check_unsafe('smbus', error=True, **kwargs)

        assert self._address != self._SENTINEL_ADDRESS, \
               'invalid address (probing may not have had access to SMbus)'

        colors = list(colors)

        try:
            mode = self.Mode[mode.upper()]
        except KeyError:
            raise ValueError(f'invalid mode: {mode!r}') from None

        if len(colors) < mode.required_colors:
            raise ValueError(f'{mode} mode requires {mode.required_colors} colors')

        if len(colors) > mode.required_colors:
            _LOGGER.debug('too many colors, dropping to %d', mode.required_colors)
            colors = colors[:mode.required_colors]

        if mode == self.Mode.OFF:
            self._smbus.write_byte_data(self._address, self._REG_MODE,
                                        self.Mode.FIXED.value)
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
            self._smbus.write_byte_data(self._address, self._REG_APPLY,
                                        self._ASUS_GPU_APPLY_VAL)

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()
