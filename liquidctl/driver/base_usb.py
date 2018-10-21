"""Base driver for USB devices.

Copyright (C) 2018  Jonas Malaco
Copyright (C) 2018  each contribution's author

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys
import logging

import usb.core
import usb.util


LOGGER = logging.getLogger(__name__)


class BaseUsbDriver(object):
    """Base driver class for USB devices.

    Each driver should provide its own list of SUPPORTED_DEVICES, as well as
    implementations for all methods applicable to the devices is supports.

    SUPPORTED_DEVICES should consist of a list of tuples (vendor id, product
    id, device release range, description, kwargs).
    """

    SUPPORTED_DEVICES = []

    def __init__(self, device, description):
        """Instantiate a driver with a device handle."""
        self.device = device
        self.description = description
        self.dry_run = False
        self._should_reattach_kernel_driver = False

    @classmethod
    def find_supported_devices(cls):
        """Find compatible devices and return corresponding driver instances.

        Returns a list of driver class instances.
        """
        drivers = []
        for vid, pid, ver, description, kwargs in cls.SUPPORTED_DEVICES:
            usbdevs = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
            for dev in usbdevs:
                if ver and (dev.bcdDevice < ver[0] or dev.bcdDevice > ver[1]):
                    continue
                drivers.append(cls(dev, description, **kwargs))
        return drivers

    def connect(self):
        """Connect to the device.

        Replace the kernel driver (Linux only) and set the device configuration
        to the first available one, if none has been set.
        """
        if sys.platform.startswith('linux') and self.device.is_kernel_driver_active(0):
            LOGGER.debug('detaching currently active kernel driver')
            self.device.detach_kernel_driver(0)
            self._should_reattach_kernel_driver = True
        cfg = self.device.get_active_configuration()
        if cfg is None:
            LOGGER.debug('setting the (first) configuration')
            self.device.set_configuration()

    def disconnect(self):
        """Disconnect from the device.

        Clean up and (Linux only) reattach the kernel driver.
        """
        usb.util.dispose_resources(self.device)
        if self._should_reattach_kernel_driver:
            LOGGER.debug('reattaching previously active kernel driver')
            self.device.attach_kernel_driver(0)

    def initialize(self):
        """Initialize the device.

        Apart from the connection handshake, some devices might support or
        require a intialization procedure.  In particular, this might be
        required after hardware changes or resuming from Mechanical Off.

        On devices that do not require manual initialization, this call will
        simply translate to a NOOP.
        """
        pass

    def get_status(self):
        """Get a status report.

        Returns a list of (key, value, unit) tuples.
        """
        raise NotImplementedError()
        return []

    def set_color(self, channel, mode, colors, speed):
        """Set the color mode for a specific channel."""
        raise NotImplementedError()

    def set_speed_profile(self, channel, profile):
        """Set channel to use a speed profile."""
        raise NotImplementedError()

    def set_fixed_speed(self, channel, speed):
        """Set channel to a fixed speed."""
        raise NotImplementedError()

