"""liquidctl drivers for NVIDIA graphics cards.

Copyright (C) 2020–2022  Jonas Malaco, Marshall Asch and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
from enum import unique

from liquidctl.driver.smbus import SmbusDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import RelaxedNamesEnum, check_unsafe

_LOGGER = logging.getLogger(__name__)

# sources for pci device and subsystem device ids:
# - https://www.nv-drivers.eu/nvidia-all-devices.html
# - https://pci-ids.ucw.cz/pci.ids
# - https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/pci_ids/pci_ids.h

# vendor, devices
# FWUPD_GUID = [vendor]:[device] - use hwinfo to inspect
NVIDIA = 0x10de
NVIDIA_GTX_1050 = 0x1c81
NVIDIA_GTX_1050_TI = 0x1c82
NVIDIA_GTX_1060 = 0x1c03
NVIDIA_GTX_1070 = 0x1b81
NVIDIA_GTX_1070_TI = 0x1b82
NVIDIA_GTX_1080 = 0x1b80
NVIDIA_GTX_1080_TI = 0x1b06
NVIDIA_GTX_1650 = 0x1f82
NVIDIA_GTX_1650S = 0x2187
NVIDIA_GTX_1660 = 0x2184
NVIDIA_GTX_1660S = 0x21c4
NVIDIA_GTX_1660_TI = 0x2182
NVIDIA_RTX_2060S = 0x1f47
NVIDIA_RTX_2060S_OC = 0x1f06
NVIDIA_RTX_2060_TU104 = 0x1e89
NVIDIA_RTX_2060_TU106 = 0x1f08
NVIDIA_RTX_2070 = 0x1f02
NVIDIA_RTX_2070S = 0x1ec7
NVIDIA_RTX_2070S_OC = 0x1e84
NVIDIA_RTX_2070_OC = 0x1f07
NVIDIA_RTX_2080 = 0x1e82
NVIDIA_RTX_2080S = 0x1e81
NVIDIA_RTX_2080_REV_A = 0x1e87
NVIDIA_RTX_2080_TI = 0x1e04
NVIDIA_RTX_2080_TI_REV_A = 0x1e07
NVIDIA_RTX_3050 = 0x2507
NVIDIA_RTX_3060 = 0x2503
NVIDIA_RTX_3060_GA104 = 0x2487
NVIDIA_RTX_3060_LHR = 0x2504
NVIDIA_RTX_3060_TI = 0x2486
NVIDIA_RTX_3060_TI_LHR = 0x2489
NVIDIA_RTX_3070 = 0x2484
NVIDIA_RTX_3070_LHR = 0x2488
NVIDIA_RTX_3070_TI = 0x2482
NVIDIA_RTX_3080 = 0x2206
NVIDIA_RTX_3080_12G_LHR = 0x220a
NVIDIA_RTX_3080_LHR = 0x2216
NVIDIA_RTX_3080_TI = 0x2208
NVIDIA_RTX_3090 = 0x2204

# subsystem vendor ASUS, subsystem devices
# PCI_SUBSYS_ID = [subsystem vendor]:[subsystem device] - use hwinfo to inspect
ASUS = 0x1043
ASUS_STRIX_GTX_1050_O2G = 0x85d8
ASUS_STRIX_GTX_1050_TI_O4G = 0x85cd
ASUS_STRIX_GTX_1050_TI_O4G_2 = 0x85d1
ASUS_STRIX_GTX_1060_6G = 0x85a4
ASUS_STRIX_GTX_1060_O6G = 0x85ac
ASUS_STRIX_GTX_1070 = 0x8598
ASUS_STRIX_GTX_1070_OC = 0x8599
ASUS_STRIX_GTX_1070_TI_8G = 0x861d
ASUS_STRIX_GTX_1070_TI_A8G = 0x861e
ASUS_STRIX_GTX_1080 = 0x8592
ASUS_STRIX_GTX_1080_A8G = 0x85aa
ASUS_STRIX_GTX_1080_O8G = 0x85f9
ASUS_STRIX_GTX_1080_TI = 0x85eb
ASUS_STRIX_GTX_1080_TI_11G = 0x85f1
ASUS_STRIX_GTX_1080_TI_O11G = 0x85ea
ASUS_STRIX_GTX_1080_TI_O11G_A02 = 0x85e4
ASUS_STRIX_GTX_1650S_OC = 0x874f
ASUS_STRIX_GTX_1660S_O6G = 0x8752
ASUS_STRIX_GTX_1660_TI_OC = 0x86a5
ASUS_STRIX_RTX_2060S_8G = 0x8730
ASUS_STRIX_RTX_2060S_A8G = 0x86fc
ASUS_STRIX_RTX_2060S_A8G_EVO = 0x8703
ASUS_STRIX_RTX_2060S_O8G = 0x86fb
ASUS_STRIX_RTX_2060_EVO = 0x86d3
ASUS_STRIX_RTX_2060_O6G = 0x868e
ASUS_STRIX_RTX_2060_O6G_EVO = 0x8775
ASUS_STRIX_RTX_2070S_8G_8707 = 0x8707
ASUS_STRIX_RTX_2070S_A8G = 0x8728
ASUS_STRIX_RTX_2070S_A8G_86FF = 0x86ff
ASUS_STRIX_RTX_2070S_A8G_8706 = 0x8706
ASUS_STRIX_RTX_2070S_O8G = 0x8727
ASUS_STRIX_RTX_2070S_O8G_8729 = 0x8729
ASUS_STRIX_RTX_2070_A8G = 0x8671
ASUS_STRIX_RTX_2070_O8G = 0x8670
ASUS_STRIX_RTX_2080S_A8G = 0x8712
ASUS_STRIX_RTX_2080S_O8G = 0x8711
ASUS_STRIX_RTX_2080_O8G = 0x865f
ASUS_STRIX_RTX_2080_TI_11G = 0x8687
ASUS_STRIX_RTX_2080_TI_OC = 0x866a
ASUS_TUF_RTX_3060_TI_O8G_OC = 0x87c6

# subsystem vendor EVGA, subsystem devices
# PCI_SUBSYS_ID = [subsystem vendor]:[subsystem device] - use hwinfo to inspect
EVGA = 0x3842
EVGA_GTX_1070_FTW = 0x6276
EVGA_GTX_1070_FTW_DT_GAMING = 0x6274
EVGA_GTX_1070_FTW_HYBRID = 0x6278
EVGA_GTX_1070_TI_FTW2 = 0x6775
EVGA_GTX_1080_FTW = 0x6286


@unique
class _ModeEnum(bytes, RelaxedNamesEnum):
    def __new__(cls, value, required_colors):
        obj = bytes.__new__(cls, [value])
        obj._value_ = value
        obj.required_colors = required_colors
        return obj

    def __str__(self):
        return self.name.capitalize()


class _NvidiaI2CDriver():
    """Generic NVIDIA I²C driver."""

    _VENDOR = None
    _ADDRESSES = []
    _MATCHES = []

    @classmethod
    def pre_probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):

        if (vendor and vendor != cls._VENDOR) \
                or (address and int(address, base=16) not in cls._ADDRESSES) \
                or release or serial:  # filters can never match, always None
            return

        if smbus.parent_subsystem_vendor != cls._VENDOR \
                or smbus.parent_vendor != NVIDIA \
                or smbus.parent_driver != 'nvidia':
            return

        for dev_id, sub_dev_id, desc in cls._MATCHES:
            if (product and product != sub_dev_id) \
                    or (match and match.lower() not in desc.lower()):
                continue

            if smbus.parent_subsystem_device != sub_dev_id \
                    or smbus.parent_device != dev_id \
                    or not smbus.description.startswith('NVIDIA i2c adapter 1 '):
                continue

            yield (dev_id, sub_dev_id, desc)


class EvgaPascal(SmbusDriver, _NvidiaI2CDriver):
    """NVIDIA series 10 (Pascal) graphics card from EVGA."""

    _REG_MODE = 0x0c
    _REG_RED = 0x09
    _REG_GREEN = 0x0a
    _REG_BLUE = 0x0b
    _REG_PERSIST = 0x23
    _PERSIST = 0xe5

    _VENDOR = EVGA
    _ADDRESSES = [0x49]
    _MATCHES = [
        (NVIDIA_GTX_1070, EVGA_GTX_1070_FTW, 'EVGA GTX 1070 FTW (experimental)'),
        (NVIDIA_GTX_1070, EVGA_GTX_1070_FTW_DT_GAMING, 'EVGA GTX 1070 FTW DT Gaming (experimental)'),
        (NVIDIA_GTX_1070, EVGA_GTX_1070_FTW_HYBRID, 'EVGA GTX 1070 FTW Hybrid (experimental)'),
        (NVIDIA_GTX_1070_TI, EVGA_GTX_1070_TI_FTW2, 'EVGA GTX 1070 Ti FTW2 (experimental)'),
        (NVIDIA_GTX_1080, EVGA_GTX_1080_FTW, 'EVGA GTX 1080 FTW'),
    ]

    @unique
    class Mode(_ModeEnum):
        OFF = (0x00, 0)
        FIXED = (0x01, 1)
        RAINBOW = (0x02, 0)
        BREATHING = (0x05, 1)

    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):

        assert len(cls._ADDRESSES) == 1, 'unexpected extra address candidates'

        pre_probed = super().pre_probe(smbus, vendor, product, address, match,
                                        release, serial, **kwargs)


        for dev_id, sub_dev_id, desc in pre_probed:
            dev = cls(smbus, desc, vendor_id=EVGA, product_id=EVGA_GTX_1080_FTW,
                      address=cls._ADDRESSES[0])
            _LOGGER.debug('found %s: %s', cls.__name__, desc)
            yield dev

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'experimental' in self.description:
            self._UNSAFE = ['smbus', 'experimental_evga_gpu']
        else:
            self._UNSAFE = ['smbus']

    def get_status(self, verbose=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        # only RGB lighting information can be fetched for now; as that isn't
        # super interesting, only enable it in verbose mode

        if not verbose:
            return []

        if not check_unsafe(*self._UNSAFE, **kwargs):
            _LOGGER.warning("%s: disabled, requires unsafe features '%s'",
                            self.description, ','.join(self._UNSAFE))
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

        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        colors = list(colors)

        try:
            mode = self.Mode[mode]
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


class RogTuring(SmbusDriver, _NvidiaI2CDriver):
    """NVIDIA series 10 (Pascal) or 20 (Turing) graphics card from ASUS."""

    _REG_RED = 0x04
    _REG_GREEN = 0x05
    _REG_BLUE = 0x06
    _REG_MODE = 0x07
    _REG_APPLY = 0x0e
    _SYNC_REG = 0x0c  # unused

    _VENDOR = ASUS
    _ADDRESSES = [0x29, 0x2a, 0x60]
    _MATCHES = [
        # description normalization rules:
        # - remove redundant ROG and meaningless GAMING;
        # - remove redundancies within a particular GPU core;
        # - keep OC when appropriate;
        # - uppercase ASUS and TUF, titlecase Evo, Ti and Stix;
        # - enforce ASUS Strix|TUF GTX|RTX <number> [Super] [Ti] [Evo] [OC] [...] order;
        # - use consistent memory sizes: 2GB, 4GB, 6GB, 8GB (but omit when redundant).

        # stable
        (NVIDIA_GTX_1070, ASUS_STRIX_GTX_1070_OC, 'ASUS Strix GTX 1070 OC'),
        (NVIDIA_RTX_2080_TI_REV_A, ASUS_STRIX_RTX_2080_TI_OC, 'ASUS Strix RTX 2080 Ti OC'),

        # experimental
        (NVIDIA_GTX_1050, ASUS_STRIX_GTX_1050_O2G, 'ASUS Strix GTX 1050 OC (experimental)'),
        (NVIDIA_GTX_1050_TI, ASUS_STRIX_GTX_1050_TI_O4G, 'ASUS Strix GTX 1050 Ti OC (experimental)'),
        (NVIDIA_GTX_1050_TI, ASUS_STRIX_GTX_1050_TI_O4G_2, 'ASUS Strix GTX 1050 Ti OC (experimental)'),
        (NVIDIA_GTX_1060, ASUS_STRIX_GTX_1060_6G, 'ASUS Strix GTX 1060 6GB (experimental)'),
        (NVIDIA_GTX_1060, ASUS_STRIX_GTX_1060_O6G, 'ASUS Strix GTX 1060 OC 6GB (experimental)'),
        (NVIDIA_GTX_1070, ASUS_STRIX_GTX_1070, 'ASUS Strix GTX 1070 (experimental)'),
        (NVIDIA_GTX_1070_TI, ASUS_STRIX_GTX_1070_TI_8G, 'ASUS Strix GTX 1070 Ti (experimental)'),
        (NVIDIA_GTX_1070_TI, ASUS_STRIX_GTX_1070_TI_A8G, 'ASUS Strix GTX 1070 Ti Advanced (experimental)'),
        (NVIDIA_GTX_1080, ASUS_STRIX_GTX_1080, 'ASUS Strix GTX 1080 (experimental)'),
        (NVIDIA_GTX_1080, ASUS_STRIX_GTX_1080_A8G, 'ASUS Strix GTX 1080 Advanced (experimental)'),
        (NVIDIA_GTX_1080, ASUS_STRIX_GTX_1080_O8G, 'ASUS Strix GTX 1080 OC (experimental)'),
        (NVIDIA_GTX_1080_TI, ASUS_STRIX_GTX_1080_TI, 'ASUS Strix GTX 1080 Ti (experimental)'),
        (NVIDIA_GTX_1080_TI, ASUS_STRIX_GTX_1080_TI_11G, 'ASUS Strix GTX 1080 Ti (experimental)'),
        (NVIDIA_GTX_1080_TI, ASUS_STRIX_GTX_1080_TI_O11G, 'ASUS Strix GTX 1080 Ti OC (experimental)'),
        (NVIDIA_GTX_1080_TI, ASUS_STRIX_GTX_1080_TI_O11G_A02, 'ASUS Strix GTX 1080 Ti OC (experimental)'),
        (NVIDIA_GTX_1650S, ASUS_STRIX_GTX_1650S_OC, 'ASUS Strix GTX 1650 Super OC (experimental)'),
        (NVIDIA_GTX_1660S, ASUS_STRIX_GTX_1660S_O6G, 'ASUS Strix GTX 1660 Super OC (experimental)'),
        (NVIDIA_GTX_1660_TI, ASUS_STRIX_GTX_1660_TI_OC, 'ASUS Strix GTX 1660 Ti OC (experimental)'),
        (NVIDIA_RTX_2060S, ASUS_STRIX_RTX_2060S_A8G_EVO, 'ASUS Strix RTX 2060 Super Evo Advanced (experimental)'),
        (NVIDIA_RTX_2060S_OC, ASUS_STRIX_RTX_2060S_8G, 'ASUS Strix RTX 2060 Super (experimental)'),
        (NVIDIA_RTX_2060S_OC, ASUS_STRIX_RTX_2060S_A8G, 'ASUS Strix RTX 2060 Super Advanced (experimental)'),
        (NVIDIA_RTX_2060S_OC, ASUS_STRIX_RTX_2060S_O8G, 'ASUS Strix RTX 2060 Super OC (experimental)'),
        (NVIDIA_RTX_2060_TU104, ASUS_STRIX_RTX_2060_O6G_EVO, 'ASUS Strix RTX 2060 Evo OC (experimental)'),
        (NVIDIA_RTX_2060_TU106, ASUS_STRIX_RTX_2060_EVO, 'ASUS Strix RTX 2060 Evo (experimental)'),
        (NVIDIA_RTX_2060_TU106, ASUS_STRIX_RTX_2060_O6G, 'ASUS Strix RTX 2060 OC (experimental)'),
        (NVIDIA_RTX_2070S, ASUS_STRIX_RTX_2070S_A8G_86FF, 'ASUS Strix RTX 2070 Super Advanced (experimental)'),
        (NVIDIA_RTX_2070S_OC, ASUS_STRIX_RTX_2070S_8G_8707, 'ASUS Strix RTX 2070 (experimental)'),
        (NVIDIA_RTX_2070S_OC, ASUS_STRIX_RTX_2070S_A8G, 'ASUS Strix RTX 2070 Super Advanced (experimental)'),
        (NVIDIA_RTX_2070S_OC, ASUS_STRIX_RTX_2070S_A8G_8706, 'ASUS Strix RTX 2070 Super Advanced (experimental)'),
        (NVIDIA_RTX_2070S_OC, ASUS_STRIX_RTX_2070S_O8G, 'ASUS Strix RTX 2070 Super OC (experimental)'),
        (NVIDIA_RTX_2070S_OC, ASUS_STRIX_RTX_2070S_O8G_8729, 'ASUS Strix RTX 2070 Super OC (experimental)'),
        (NVIDIA_RTX_2070_OC, ASUS_STRIX_RTX_2070_A8G, 'ASUS Strix RTX 2070 Advanced (experimental)'),
        (NVIDIA_RTX_2070_OC, ASUS_STRIX_RTX_2070_O8G, 'ASUS Strix RTX 2070 OC (experimental)'),
        (NVIDIA_RTX_2080S, ASUS_STRIX_RTX_2080S_A8G, 'ASUS Strix RTX 2080 Super Advanced (experimental)'),
        (NVIDIA_RTX_2080S, ASUS_STRIX_RTX_2080S_O8G, 'ASUS Strix RTX 2080 Super OC (experimental)'),
        (NVIDIA_RTX_2080_REV_A, ASUS_STRIX_RTX_2080_O8G, 'ASUS Strix RTX 2080 OC (experimental)'),
        (NVIDIA_RTX_2080_TI, ASUS_STRIX_RTX_2080_TI_11G, 'ASUS Strix RTX 2080 Ti (experimental)'),
        (NVIDIA_RTX_3060_TI_LHR, ASUS_TUF_RTX_3060_TI_O8G_OC, 'ASUS TUF RTX 3060 Ti OC (experimental)'),
    ]

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

        ASUS_GPU_MAGIC_VALUE = 0x1589

        pre_probed = super().pre_probe(smbus, vendor, product, address, match,
                                        release, serial, **kwargs)

        for dev_id, sub_dev_id, desc in pre_probed:
            selected_address = None

            if check_unsafe('smbus', **kwargs):
                for address in cls._ADDRESSES:
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
                _LOGGER.debug('instantiated driver %s for %s at address %02x',
                              cls.__name__, desc, selected_address)
                yield dev

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'experimental' in self.description:
            self._UNSAFE = ['smbus', 'experimental_asus_gpu']
        else:
            self._UNSAFE = ['smbus']

    def get_status(self, verbose=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        # only RGB lighting information can be fetched for now; as that isn't
        # super interesting, only enable it in verbose mode

        if not verbose:
            return []

        if not check_unsafe(*self._UNSAFE, **kwargs):
            _LOGGER.warning("%s: disabled, requires unsafe features '%s'",
                            self.description, ','.join(self._UNSAFE))
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

        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        assert self._address != self._SENTINEL_ADDRESS, \
               'invalid address (probing may not have had access to SMbus)'

        colors = list(colors)

        try:
            mode = self.Mode[mode]
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
