"""liquidctl drivers for DDR4 memory.

Copyright (C) 2020–2020  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from enum import Enum, unique
import logging

from liquidctl.driver.smbus import SmbusDriver
from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver
from liquidctl.util import check_unsafe

_LOGGER = logging.getLogger(__name__)


from collections import namedtuple


class Ddr4Spd:
    """Partial decoding of DDR4 Serial Presence Detect (SPD) information.

    Properties will raise on data they are not yet prepared to handle, but what
    is implemented attempts to comply with JEDEC 21-C Annex L.
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
        2: { 0x98: 'Kingston' },
        3: { 0x9e: 'Corsair' },
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

        assert self.dram_device_type in [self.DramDeviceType.DDR4_SDRAM,
                                         self.DramDeviceType.LPDDR4_SDRAM,
                                         self.DramDeviceType.LPDDR4X_SDRAM]

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
    """DDR4 module with TSE2004av-compatible SPD EEPROM and temperature sensor."""

    _REG_CAPABILITIES = 0x00
    _REG_TEMPERATURE = 0x05

    _UNSAFE = ['smbus', 'ddr4_temperature']

    @classmethod
    def probe(cls, smbus, vendor=None, product=None, address=None, match=None,
              release=None, serial=None, **kwargs):

        # FIXME support mainstream AMD chipsets on Linux; note that unlike
        # i801_smbus, piix4_smbus does not enumerate and register the available
        # SPD EEPROMs with i2c_register_spd

        _DIMM_MASK = 0b111
        _SPD_DTIC = 0x50
        _TS_DTIC = 0x18
        _SMBUS_DRIVERS = ['i801_smbus']

        if smbus.parent_driver not in _SMBUS_DRIVERS \
                or any([vendor, product, release, serial]):  # wont match, always None
            return

        for dimm in range(_DIMM_MASK + 1):
            spd_addr = _SPD_DTIC | dimm
            spd = smbus.load_spd_eeprom(spd_addr)

            if not spd:
                continue

            try:
                spd = Ddr4Spd(spd)

                if spd.dram_device_type != Ddr4Spd.DramDeviceType.DDR4_SDRAM:
                    continue

                desc = cls._match(spd)
            except:
                continue

            if not desc:
                continue

            ts_addr = _TS_DTIC | dimm
            desc += f' DIMM{dimm + 1} (experimental)'

            if (address and int(address, base=16) != ts_addr) \
                    or (match and match.lower() not in desc.lower()):
                continue

            dev = cls(smbus, desc, address=ts_addr)
            _LOGGER.debug('instanced driver for %s', desc)
            yield dev

    @classmethod
    def _match(cls, spd):
        if not spd.module_thermal_sensor:
            return None

        try:
            manufacturer = spd.module_manufacturer
        except:
            return f'DDR4'

        if spd.module_part_number:
            return f'{manufacturer} {spd.module_part_number}'
        else:
            return f'{manufacturer}'

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        if not check_unsafe(*self._UNSAFE, **kwargs):
            _LOGGER.warning("%s: nothing to return, requires unsafe features "
                            "'%s'",  self.description, ','.join(self._UNSAFE))
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
        return self._smbus.read_block_data(self._address, self._REG_TEMPERATURE)

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

    _UNSAFE = ['smbus', 'vengeance_rgb']

    @classmethod
    def _match(cls, spd):
        if spd.module_type != (Ddr4Spd.BaseModuleType.UDIMM, None) \
                or spd.module_manufacturer != 'Corsair' \
                or not spd.module_part_number.startswith('CMR'):
            return None

        return 'Corsair Vengeance RGB'

    def _read_temperature_register(self):
        # instead of using block reads, Vengeance RGB temperature sensor
        # devices must be read in words
        treg = self._smbus.read_word_data(self._address, self._REG_TEMPERATURE)

        # swap LSB and MSB; read_word_data reads in little endianess, but the
        # temperature sensor registers should be read in big endianess
        treg = ((treg & 0xff) << 8) | (treg >> 8)

        return treg
