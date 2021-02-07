"""Base SMBus bus and driver APIs.

For now, these are unstable APIs, and only Linux is supported.

Copyright (C) 2020–2021  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections import namedtuple
from pathlib import Path
import logging
import os
import sys

from liquidctl.driver.base import BaseDriver, BaseBus, find_all_subclasses
from liquidctl.util import check_unsafe, LazyHexRepr

_LOGGER = logging.getLogger(__name__)


if sys.platform == 'linux':

    # WARNING: the tests rely on being able to override which SMBus
    # implementation is used here; this is done through the SMBus attribute
    # created below, do not move/replace/change it, nor access it during module
    # initialization
    from smbus import SMBus

    LinuxEeprom = namedtuple('LinuxEeprom', 'name data')

    class LinuxI2c(BaseBus):
        """The Linux I²C (`/sys/bus/i2c`) bus."""

        def __init__(self, i2c_root='/sys/bus/i2c'):
            self._i2c_root = Path(i2c_root)

        def find_devices(self, bus=None, usb_port=None, **kwargs):
            """Find compatible SMBus devices."""

            if usb_port:
                # a usb_port filter implies an USB bus
                return

            devices = self._i2c_root.joinpath('devices')
            if not devices.exists():
                _LOGGER.debug('skipping %s, %s not available',
                              self.__class__.__name__, devices)
                return

            drivers = sorted(find_all_subclasses(SmbusDriver),
                             key=lambda x: (x.__module__, x.__name__))

            _LOGGER.debug('searching %s (%s)', self.__class__.__name__,
                          ', '.join(map(lambda x: x.__name__, drivers)))

            for i2c_dev in devices.iterdir():
                try:
                    i2c_bus = LinuxI2cBus(i2c_dev)
                except ValueError as err:
                    _LOGGER.debug('ignoring %s, %s', i2c_dev.name, err)
                    continue

                if bus and bus != i2c_bus.name:
                    continue

                _LOGGER.debug('found I²C bus %s', i2c_bus.name)
                yield from i2c_bus.find_devices(drivers, **kwargs)

    class LinuxI2cBus:
        """A Linux I²C device, which is itself an I²C bus.

        Should not be instantiated directly; use `LinuxI2c.find_devices`
        instead.

        This type mimics the `smbus.SMBus` read/write/close APIs.  However,
        `open` does not take any parameters, and not all APIs are available.
        """

        # note: this is not a liquidctl BaseBus, as that would cause
        # find_liquidctl_devices to try to directly instantiate it

        def __init__(self, i2c_dev):
            self._i2c_dev = i2c_dev
            self._smbus = None

            try:
                assert i2c_dev.name.startswith('i2c-')
                self._number = int(i2c_dev.name[4:])
            except:
                raise ValueError('cannot infer bus number')

        def find_devices(self, drivers, **kwargs):
            """Probe drivers and find compatible devices in this bus."""
            for drv in drivers:
                yield from drv.probe(self, **kwargs)

        def open(self):
            """Open the I²C bus."""
            if not self._smbus:
                try:
                    self._smbus = SMBus(self._number)
                except FileNotFoundError:
                    if Path('/sys/class/i2c-dev').exists():
                        raise
                    raise OSError('kernel module i2c-dev not loaded') from None

        def read_byte(self, address):
            """Read a single byte from a device."""
            value = self._smbus.read_byte(address)
            _LOGGER.debug('read byte @ 0x%02x:0x%02x', address, value)
            return value

        def read_byte_data(self, address, register):
            """Read a single byte from a designated register."""
            value = self._smbus.read_byte_data(address, register)
            _LOGGER.debug('read byte data @ 0x%02x:0x%02x 0x%02x',
                          address, register, value)
            return value

        def read_word_data(self, address, register):
            """Read a single 2-byte word from a given register."""
            value = self._smbus.read_word_data(address, register)
            _LOGGER.debug('read word data @ 0x%02x:0x%02x 0x%02x',
                          address, register, value)
            return value

        def read_block_data(self, address, register):
            """Read a block of up to  32 bytes from a given register."""
            data = self._smbus.read_block_data(address, register)
            _LOGGER.debug('read block data @ 0x%02x:0x%02x: %r',
                          address, register, LazyHexRepr(data))
            return data

        def write_byte(self, address, value):
            """Write a single byte to a device."""
            _LOGGER.debug('writing byte @ 0x%02x: 0x%02x', address, value)
            return self._smbus.write_byte(address, value)

        def write_byte_data(self, address, register, value):
            """Write a single byte to a designated register."""
            _LOGGER.debug('writing byte data @ 0x%02x:0x%02x 0x%02x',
                          address, register, value)
            return self._smbus.write_byte_data(address, register, value)

        def write_word_data(self, address, register, value):
            """Write a single 2-byte word to a designated register."""
            _LOGGER.debug('writing word data @ 0x%02x:0x%02x 0x%02x',
                          address, register, value)
            return self._smbus.write_word_data(address, register, value)

        def write_block_data(self, address, register, data):
            """Write a block of byte data to a given register."""
            _LOGGER.debug('writing block data @ 0x%02x:0x%02x %r',
                          address, register, LazyHexRepr(data))
            return self._smbus.write_block_data(address, register, data)

        def close(self):
            """Close the I²C connection."""
            if self._smbus:
                self._smbus.close()
                self._smbus = None

        def load_eeprom(self, address):
            """Return EEPROM name and data in `address`, or None if N/A."""

            # uses kernel facilities to avoid directly reading from the EEPROM
            # or managing its pages, also avoiding the need for unsafe=smbus

            dev = f'{self._number}-{address:04x}'
            try:
                name = self._i2c_dev.joinpath(dev, 'name').read_text().strip()
                eeprom = self._i2c_dev.joinpath(dev, 'eeprom').read_bytes()
                return LinuxEeprom(name, eeprom)
            except Exception:
                return None

        @property
        def name(self):
            return self._i2c_dev.name

        @property
        def description(self):
            return self._try_sysfs_read('name')

        @property
        def parent_vendor(self):
            return self._try_sysfs_read_hex('device/vendor')

        @property
        def parent_device(self):
            return self._try_sysfs_read_hex('device/device')

        @property
        def parent_subsystem_vendor(self):
            return self._try_sysfs_read_hex('device/subsystem_vendor')

        @property
        def parent_subsystem_device(self):
            return self._try_sysfs_read_hex('device/subsystem_device')

        @property
        def parent_driver(self):
            try:
                return Path(os.readlink(self._i2c_dev.joinpath('device/driver'))).name
            except FileNotFoundError:
                return None

        def __str__(self):
            if self.description:
                return f'{self.name}: {self.description}'
            return self.name

        def __repr__(self):
            def hexid(maybe):
                if maybe is not None:
                    return f'{maybe:#06x}'
                return 'None'

            return f'{self.__class__.__name__}: name: {self.name!r}, description:' \
                   f' {self.description!r}, parent_vendor: {hexid(self.parent_vendor)},' \
                   f' parent_device: {hexid(self.parent_device)}, parent_subsystem_vendor:' \
                   f' {hexid(self.parent_subsystem_vendor)},' \
                   f' parent_subsystem_device: {hexid(self.parent_subsystem_device)},' \
                   f' parent_driver: {self.parent_driver!r}'

        def _try_sysfs_read(self, *sub, default=None):
            try:
                return self._i2c_dev.joinpath(*sub).read_text().rstrip()
            except FileNotFoundError:
                return default

        def _try_sysfs_read_hex(self, *sub, default=None):
            try:
                return int(self._i2c_dev.joinpath(*sub).read_text(), base=16)
            except FileNotFoundError:
                return default


class SmbusDriver(BaseDriver):
    """Base driver class for SMBus devices."""

    @classmethod
    def probe(cls, smbus, **kwargs):
        raise NotImplementedError()

    @classmethod
    def find_supported_devices(cls, root_bus=None, **kwargs):
        """Find devices specifically compatible with this driver."""
        if sys.platform != 'linux':
            return []

        if not root_bus:
            root_bus = LinuxI2c()

        devs = filter(lambda x: isinstance(x, cls),
                      root_bus.find_devices(**kwargs))
        return list(devs)

    def __init__(self, smbus, description, vendor_id=None, product_id=None,
                 address=None, **kwargs):
        # note: vendor_id and product_id are liquidctl properties intended to
        # allow the user to differentiate and ultimately filter devices; in the
        # context of SMBus, drivers may choose to use the parent's PCI
        # **subsystem** vendor/device IDs for this task, as those are more
        # specific and closer to the product the user purchased than the less
        # specific PCI vendor/device IDs.

        assert address is not None

        self._smbus = smbus
        self._description = description
        self._vendor_id = vendor_id
        self._product_id = product_id
        self._address = address

    def connect(self, **kwargs):
        """Connect to the device."""
        if check_unsafe('smbus', **kwargs):
            self._smbus.open()
        else:
            # do not raise: some driver APIs may not access the bus after all,
            # and allowing the device to pseudo-connect is convenient given the
            # current API structure; APIs that do access the bus should check
            # for the 'smbus' feature themselves and, if necessary, raise
            # UnsafeFeaturesNotEnabled(*requirements)
            # (see also: check_unsafe(..., error=True))
            _LOGGER.debug("SMBus is disabled, missing unsafe feature 'smbus'")
        return self

    def disconnect(self, **kwargs):
        """Disconnect from the device."""
        self._smbus.close()

    @property
    def description(self):
        """Human readable description of the corresponding device."""
        return self._description

    @property
    def vendor_id(self):
        """Numeric vendor identifier, or None if N/A."""
        return self._vendor_id

    @property
    def product_id(self):
        """Numeric product identifier, or None if N/A."""
        return self._product_id

    @property
    def release_number(self):
        """Device versioning number, or None if N/A.

        In USB devices this is bcdDevice.
        """
        return None

    @property
    def serial_number(self):
        """Serial number reported by the device, or None if N/A."""
        return None

    @property
    def bus(self):
        """Bus the device is connected to, or None if N/A."""
        return self._smbus.name

    @property
    def address(self):
        """Address of the device on the corresponding bus, or None if N/A."""
        return f'{self._address:#04x}'

    @property
    def port(self):
        """Physical location of the device, or None if N/A."""
        return None
