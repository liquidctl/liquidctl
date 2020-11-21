"""Base SMBus bus and driver APIs.

For now, these are unstable APIs, and only Linux is supported.

Copyright (C) 2020–2020  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from pathlib import Path
import logging
import os
import sys

from liquidctl.driver.base import BaseDriver, BaseBus, find_all_subclasses

_LOGGER = logging.getLogger(__name__)


if sys.platform == 'linux':

    # smbus is an optional dependency
    try:
        from smbus import SMBus
    except ModuleNotFoundError:
        SMBus = None


    class LinuxI2c(BaseBus):
        """The Linux I²C (`/sys/bus/i2c`) bus."""

        def find_devices(self, bus=None, usb_port=None, **kwargs):
            """Find compatible SMBus devices."""

            if usb_port:
                # a usb_port filter implies an USB bus
                return

            if not SMBus:
                _LOGGER.debug('skipping %s, smbus package not available',
                              self.__class__.__name__)
                return

            devices = Path('/sys/bus/i2c/devices')
            if not devices.exists():
                _LOGGER.debug('skipping %s, %s not available',
                              self.__class__.__name__, devices)
                return

            drivers = sorted(find_all_subclasses(SmbusDriver),
                             key=lambda x: (x.__module__, x.__name__))

            _LOGGER.debug('searching %s (%s)', self.__class__.__name__,
                          ', '.join(map(lambda x: x.__name__, drivers)))

            for i2c_dev in devices.iterdir():
                if not i2c_dev.name.startswith('i2c-'):
                    continue  # wont have a matching /dev/i2c-* file

                i2c_bus = LinuxI2cBus(i2c_dev)

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

            assert i2c_dev.name.startswith('i2c-')
            self._number = int(i2c_dev.name[4:])

        def find_devices(self, drivers, **kwargs):
            """Probe drivers and find compatible devices in this bus."""
            for drv in drivers:
                yield from drv.probe(self, **kwargs)

        def open(self):
            """Open the I²C bus."""
            if not self._smbus:
                self._smbus = SMBus(self._number)

        def read_byte(self, address):
            """Read a single byte from a device."""
            value = self._smbus.read_byte(address)
            _LOGGER.debug('read byte @ 0x%02x: 0x%02x', address, value)
            return value

        def read_byte_data(self, address, register):
            """Read a single byte from a designated register."""
            value = self._smbus.read_byte_data(address, register)
            _LOGGER.debug('read byte data @ 0x%02x:0x%02x: 0x%02x', address,
                          register, value)
            return value

        def write_byte(self, address, value):
            """Write a single byte from a device."""
            _LOGGER.debug('writing byte @ 0x%02x: 0x%02x', address, value)
            return self._smbus.write_byte(address, value)

        def write_byte_data(self, address, register, value):
            """Write a single byte from a designated register."""
            _LOGGER.debug('writing byte data @ 0x%02x:0x%02x: 0x%02x', address,
                          register, value)
            return self._smbus.write_byte_data(address, register, value)

        def close(self):
            """Close the I²C connection."""
            if self._smbus:
                self._smbus.close()
                self._smbus = None

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

            return f'{self.__class__.__name__}: name: {self.name!r}, ' \
                   f'description: {self.description!r}, ' \
                   f'parent_vendor: {hexid(self.parent_vendor)}, ' \
                   f'parent_device: {hexid(self.parent_device)}, ' \
                   f'parent_subsystem_vendor: {hexid(self.parent_subsystem_vendor)}, ' \
                   f'parent_subsystem_device: {hexid(self.parent_subsystem_device)}, ' \
                   f'parent_driver: {self.parent_driver!r}'

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
    def find_supported_devices(cls, **kwargs):
        """Find devices specifically compatible with this driver."""
        if sys.platform != 'linux':
            return []

        devs = filter(lambda x: isinstance(x, cls), LinuxI2c.find_devices(**kwargs))
        return list(devs)

    def __init__(self, smbus, description, vendor_id=None, product_id=None,
                 address=None, **kwargs):
        assert vendor_id and product_id and address is not None

        self._smbus = smbus
        self._description = description
        self._vendor_id = vendor_id
        self._product_id = product_id
        self._address = address

    def connect(self, unsafe=None, **kwargs):
        """Connect to the device."""
        if not (unsafe and 'smbus' in unsafe):
            _LOGGER.warning('SMBus support requires the `smbus` unsafe flag')
            return
        self._smbus.open()

    def disconnect(self, **kwargs):
        """Disconnect from the device."""
        self._smbus.close()

    @property
    def description(self):
        """Human readable description of the corresponding device."""
        return self._description

    @property
    def vendor_id(self):
        """Numeric vendor identifier."""
        return self._vendor_id

    @property
    def product_id(self):
        """Numeric product identifier."""
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
