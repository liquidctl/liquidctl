"""liquidctl drivers for DDR4 memory.

Copyright (C) 2020–2022  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging
from collections import namedtuple
from enum import Enum, unique

from liquidctl.driver.smbus import SmbusDriver
from liquidctl.error import ExpectationNotMet, NotSupportedByDevice, NotSupportedByDriver
from liquidctl.util import RelaxedNamesEnum, check_unsafe, clamp

_LOGGER = logging.getLogger(__name__)


class Ddr4Spd:
    """Partial decoding of DDR4 Serial Presence Detect (SPD) information.

    Properties will raise on data they are not yet prepared to handle, but what
    is implemented attempts to comply with JEDEC 21-C 4.1.2 Annex L.
    """

    class DramDeviceType(Enum):
        """DRAM device type (not exhaustive)."""
        DDR4_SDRAM = 0x0c
        LPDDR4_SDRAM = 0x10
        LPDDR4X_SDRAM = 0x11

        def __str__(self):
            return self.name.replace('_', ' ')

    class BaseModuleType(Enum):
        """Base module type (not exhaustive)."""

        RDIMM = 0b0001
        UDIMM = 0b0010
        SO_DIMM = 0b0011
        LRDIMM = 0x0100

        def __str__(self):
            return self.name.replace('_', ' ')

    # Standard Manufacturer's Identification Code from JEDEC JEP106;
    # (not exhaustive) maps banks and IDs to names: _JEP106[<bank>][id]
    _JEP106 = {
        1: {
            0x2c: 'Micron',
            0xad: 'SK Hynix',
            0xce: 'Samsung',
        },
        2: {0x98: 'Kingston'},
        3: {0x9e: 'Corsair'},
        5: {
            0xcd: 'G.SKILL',
            0xef: 'Team Group',
        },
        6: {
            0x02: 'Patriot',
            0x9b: 'Crucial',
        },
    }

    def __init__(self, eeprom):
        self._eeprom = eeprom

        if self.dram_device_type not in [self.DramDeviceType.DDR4_SDRAM,
                                         self.DramDeviceType.LPDDR4_SDRAM,
                                         self.DramDeviceType.LPDDR4X_SDRAM]:
            raise ValueError('not a DDR4 SPD EEPROM')

    @property
    def spd_bytes_used(self):
        nibble = self._eeprom[0x00] & 0x0f
        assert nibble <= 0b0100, 'reserved'
        return nibble * 128

    @property
    def spd_bytes_total(self):
        nibble = (self._eeprom[0x00] >> 4) & 0b111
        assert nibble <= 0b010, 'reserved'
        return nibble * 256

    @property
    def spd_revision(self):
        enc_level = self._eeprom[0x01] >> 4
        add_level = self._eeprom[0x01] & 0x0f
        return (enc_level, add_level)

    @property
    def dram_device_type(self):
        return self.DramDeviceType(self._eeprom[0x02])

    @property
    def module_type(self):
        base = self._eeprom[0x03] & 0x0f
        hybrid = self._eeprom[0x03] >> 4
        assert not hybrid
        return (self.BaseModuleType(base), None)

    @property
    def module_thermal_sensor(self):
        present = self._eeprom[0x0e] >> 7
        return bool(present)

    @property
    def module_manufacturer(self):
        bank = 1 + self._eeprom[0x140] & 0x7f
        mid = self._eeprom[0x141]
        return self._JEP106[bank][mid]

    @property
    def module_part_number(self):
        return self._eeprom[0x149:0x15d].decode(encoding='ascii').rstrip()

    @property
    def dram_manufacturer(self):
        bank = 1 + self._eeprom[0x15e] & 0x7f
        mid = self._eeprom[0x15f]
        return self._JEP106[bank][mid]


class Ddr4Temperature(SmbusDriver):
    """DDR4 module with TSE2004-compatible SPD EEPROM and temperature sensor."""

    _SPD_DTIC = 0x50
    _TS_DTIC = 0x18
    _SA_MASK = 0b111
    _REG_CAPABILITIES = 0x00
    _REG_TEMPERATURE = 0x05

    _UNSAFE = ['smbus', 'ddr4_temperature']

    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):

        # FIXME support mainstream AMD chipsets on Linux; note that unlike
        # i801_smbus, piix4_smbus does not enumerate and register the available
        # SPD EEPROMs with i2c_register_spd

        _SMBUS_DRIVERS = ['i801_smbus']

        if smbus.parent_driver not in _SMBUS_DRIVERS \
                or any([vendor, product, release, serial]):  # wont match, always None
            return

        for dimm in range(cls._SA_MASK + 1):
            spd_addr = cls._SPD_DTIC | dimm
            eeprom = smbus.load_eeprom(spd_addr)

            if not eeprom or eeprom.name != 'ee1004':
                continue

            try:
                spd = Ddr4Spd(eeprom.data)

                if spd.dram_device_type != Ddr4Spd.DramDeviceType.DDR4_SDRAM:
                    continue

                desc = cls._match(spd)
            except:
                continue

            if not desc:
                continue

            desc += f' DIMM{dimm + 1}'

            if (address and int(address, base=16) != spd_addr) \
                    or (match and match.lower() not in desc.lower()):
                continue

            # set the default device address to a weird value to prevent
            # accidental attempts of writes to the SPD EEPROM (DDR4 SPD writes
            # are also disabled by default in many motherboards)
            dev = cls(smbus, desc, address=(None, None, spd_addr))
            _LOGGER.debug('found %s: %s', cls.__name__, desc)
            yield dev

    @classmethod
    def _match(cls, spd):
        if not spd.module_thermal_sensor:
            return None

        try:
            manufacturer = spd.module_manufacturer
        except:
            return 'DDR4'

        if spd.module_part_number:
            return f'{manufacturer} {spd.module_part_number}'
        else:
            return manufacturer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ts_address = self._TS_DTIC | (self._address[2] & self._SA_MASK)

    @property
    def address(self):
        return f'{self._address[2]:#04x}'

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        if not check_unsafe(*self._UNSAFE, **kwargs):
            _LOGGER.warning("%s: disabled, requires unsafe features '%s'",
                            self.description, ','.join(self._UNSAFE))
            return []

        treg = self._read_temperature_register()

        # discard flags bits and interpret remaining bits as 2s complement
        treg = treg & 0x1fff
        if treg > 0x0fff:
            treg -= 0x2000

        # should always be supported
        resolution, bits = (.25, 10)

        multiplier = treg >> (12 - bits)

        return [
            ('Temperature', resolution * multiplier, '°C'),
        ]

    def _read_temperature_register(self):
        # in theory we should first write 0x05 to the pointer register, but
        # avoid writing to the device, even if that means occasionally reading
        # garbage; ideally we would check the currently set pointer, but we
        # have not found any way to do that

        # while JEDEC 21-C 4.1.6 uses the term "block read", it has little to
        # do with the SMBus Block Read protocol; instead, it is closer to the
        # SMBus Read Word protocol, except in big endianess
        treg = self._smbus.read_word_data(self._ts_address, self._REG_TEMPERATURE)

        # swap LSB and MSB before returning: read_word_data reads in little
        # endianess, but the register must be read in big endianess
        return ((treg & 0xff) << 8) | (treg >> 8)

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def set_color(self, channel, mode, colors, **kwargs):
        """Not supported by this driver."""
        raise NotSupportedByDriver()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()


class VengeanceRgb(Ddr4Temperature):
    """Corsair Vengeance RGB DDR4 module."""

    _RGB_DTIC = 0x58
    _REG_RGB_TIMING1 = 0xa4
    _REG_RGB_TIMING2 = 0xa5
    _REG_RGB_MODE = 0xa6
    _REG_RGB_COLOR_COUNT = 0xa7
    _REG_RGB_COLOR_START = 0xb0
    _REG_RGB_COLOR_END = 0xc5

    _UNSAFE = ['smbus', 'vengeance_rgb']

    @unique
    class Mode(bytes, RelaxedNamesEnum):
        def __new__(cls, value, min_colors, max_colors):
            obj = bytes.__new__(cls, [value])
            obj._value_ = value
            obj.min_colors = min_colors
            obj.max_colors = max_colors
            return obj

        FIXED = (0x00, 1, 1)
        FADING = (0x01, 2, 7)
        BREATHING = (0x02, 1, 7)

        OFF = (0xf0, 0, 0)  # pseudo mode, equivalent to fixed #000000

        def __str__(self):
            return self.name.lower()

    @unique
    class SpeedTimings(RelaxedNamesEnum):
        SLOWEST = 63
        SLOWER = 48
        NORMAL = 32
        FASTER = 16
        FASTEST = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rgb_address = None

    @classmethod
    def _match(cls, spd):
        if spd.module_type != (Ddr4Spd.BaseModuleType.UDIMM, None) \
                or spd.module_manufacturer != 'Corsair' \
                or not spd.module_part_number.startswith('CMR'):
            return None

        return 'Corsair Vengeance RGB'


    def set_color(self, channel, mode, colors, speed='normal',
                  transition_ticks=None, stable_ticks=None, **kwargs):
        """Set the RGB lighting mode and, when applicable, color.

        The table bellow summarizes the available channels, modes and their
        associated number of required colors.

        | Channel  | Mode      | Colors |
        | -------- | --------- | ------ |
        | led      | off       |      0 |
        | led      | fixed     |      1 |
        | led      | breathing |    1–7 |
        | led      | fading    |    2–7 |

        The speed of the breathing and fading animations can be adjusted with
        `speed`; the allowed values are 'slowest', 'slower', 'normal'
        (default), 'faster' and 'fastest'.

        It is also possible to override the raw timing parameters through
        `transition_ticks` and `stable_ticks`; these should be integer values
        in the range 0–63.
        """

        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        try:
            common = self.SpeedTimings[speed].value
            tp1 = tp2 = common
        except KeyError:
            raise ValueError(f'invalid speed preset: {speed!r}') from None

        if transition_ticks is not None:
            tp1 = clamp(transition_ticks, 0, 63)
        if stable_ticks is not None:
            tp2 = clamp(stable_ticks, 0, 63)

        colors = list(colors)

        try:
            mode = self.Mode[mode]
        except KeyError:
            raise ValueError(f'invalid mode: {mode!r}') from None

        if len(colors) < mode.min_colors:
            raise ValueError(f'{mode} mode requires {mode.min_colors} colors')

        if len(colors) > mode.max_colors:
            _LOGGER.debug('too many colors, dropping to %d', mode.max_colors)
            colors = colors[:mode.max_colors]

        self._compute_rgb_address()

        if mode == self.Mode.OFF:
            mode = self.Mode.FIXED
            colors = [[0x00, 0x00, 0x00]]

        def rgb_write(register, value):
            self._smbus.write_byte_data(self._rgb_address, register, value)

        if mode == self.Mode.FIXED:
            rgb_write(self._REG_RGB_TIMING1, 0x00)
        else:
            rgb_write(self._REG_RGB_TIMING1, tp1)
            rgb_write(self._REG_RGB_TIMING2, tp2)

        color_registers = range(self._REG_RGB_COLOR_START, self._REG_RGB_COLOR_END)
        color_components = itertools.chain(*colors)

        for register, component in zip(color_registers, color_components):
            rgb_write(register, component)

        rgb_write(self._REG_RGB_COLOR_COUNT, len(colors))

        if mode == self.Mode.BREATHING and len(colors) == 1:
            rgb_write(self._REG_RGB_MODE, self.Mode.FIXED.value)
        else:
            rgb_write(self._REG_RGB_MODE, mode.value)

    def _compute_rgb_address(self):
        if self._rgb_address:
            return

        # the dimm's rgb controller is typically at 0x58–0x5f
        candidate = self._RGB_DTIC | (self._address[2] & self._SA_MASK)

        # reading from any register should return 0xba if we have the right device
        if self._smbus.read_byte_data(candidate, self._REG_RGB_MODE) != 0xba:
            raise ExpectationNotMet(f'{self.bus}:{candidate:#04x} is not the RGB controller')

        self._rgb_address = candidate
