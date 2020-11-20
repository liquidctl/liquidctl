"""Base SMBus bus and driver APIs.

Only implemented for Linux.

Copyright (C) 2020–2020  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from pathlib import Path
import logging
import os
import sys

from liquidctl.driver.base import BaseDriver, BaseBus, find_all_subclasses
from liquidctl.util import LazyHexRepr

_LOGGER = logging.getLogger(__name__)

if sys.platform == 'linux':
    import smbus


    class LinuxI2c(BaseBus):
        """The Linux I²C (`/sys/bus/i2c`) bus."""

        def find_devices(self, bus=None, usb_port=None, **kwargs):
            """Find compatible SMBus devices."""

            if usb_port:
                return  # an USB port implies the bus is USB

            drivers = sorted(find_all_subclasses(SmbusDriver),
                             key=lambda x: (x.__module__, x.__name__))

            _LOGGER.debug('searching %s (%s)', self.__class__.__name__,
                          ', '.join(map(lambda x: x.__name__, drivers)))

            for i2c_dev in Path('/sys/bus/i2c/devices').iterdir():
                i2c_bus = LinuxI2cBus(i2c_dev)

                if bus and bus != i2c_bus.name:
                    continue

                _LOGGER.debug('found I²C bus %s', i2c_bus.name)
                yield from i2c_bus.find_devices(drivers, **kwargs)


    class LinuxI2cBus:
        """A Linux I²C device, which is itself an I²C bus.

        Should not be instantiated directly; `LinuxI2c.find_devices` should be
        used instead.

        This type also does *not* extend `BaseBus`, due to how buses are
        automatically discovered by `liquidctl.find_liquidctl_devices`.
        """

        def __init__(self, i2c_dev):
            self._i2c_dev = i2c_dev

        def find_devices(self, drivers, **kwargs):
            """Probe drivers and find compatible devices in this bus."""
            for drv in drivers:
                yield from drv.probe(self, **kwargs)

        @property
        def name(self):
            return self._i2c_dev.name

        @property
        def description(self):
            return self._try_read('name')

        @property
        def vendor(self):
            return self._try_read_hex('device/vendor')

        @property
        def device(self):
            return self._try_read_hex('device/device')

        @property
        def subsystem_vendor(self):
            return self._try_read_hex('device/subsystem_vendor')

        @property
        def subsystem_device(self):
            return self._try_read_hex('device/subsystem_device')

        @property
        def driver(self):
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
                   f'vendor: {hexid(self.vendor)}, device: {hexid(self.device)}, ' \
                   f'subsystem_vendor: {hexid(self.subsystem_vendor)}, ' \
                   f'subsystem_device: {hexid(self.subsystem_device)}, ' \
                   f'driver: {self.driver!r}'

        def _try_read(self, *sub, default=None):
            try:
                return self._i2c_dev.joinpath(*sub).read_text().rstrip()
            except FileNotFoundError:
                return default

        def _try_read_hex(self, *sub, default=None):
            try:
                return int(self._i2c_dev.joinpath(*sub).read_text(), base=16)
            except FileNotFoundError:
                return default


class SmbusDriver(BaseDriver):
    """Base driver class for SMBus devices."""

    @classmethod
    def probe(cls, i2c_bus, **kwargs):
        raise NotImplementedError()

    @classmethod
    def find_supported_devices(cls, **kwargs):
        """Find devices specifically compatible with this driver."""
        if sys.platform != 'linux':
            return []

        devs = filter(lambda x: type(x) == cls, LinuxI2c.find_devices(**kwargs))
        return list(devs)

    def __init__(self, smbus, description, vendor_id=None, product_id=None,
                 address=None, **kwargs):
        assert vendor_id and product_id and address is not None

        self._smbus = smbus
        self._description = description
        self._vendor_id = vendor_id
        self._product_id = product_id
        self._address = address

    def connect(self, **kwargs):
        """Connect to the device."""
        pass

    def disconnect(self, **kwargs):
        """Disconnect from the device."""
        pass

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
