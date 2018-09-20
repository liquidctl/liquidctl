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

import usb.core
import usb.util

import liquidctl.util


class BaseUsbDriver(object):
    """Base driver class for USB devices.

    Each driver should provide its own list of supported_devices, as well as
    implementations for all methods that are supported by the device.

    The list of supported_devices should consist of (vendor id, product id,
    device release range, description, kwargs) tuples; the device release range
    can either be a (lower bound, [inclusive] upper bould) tuple or None.
    """

    supported_devices = []

    def __init__(self, device, description, **kwargs):
        """Instantiate a driver with a device handle.

        Supplied kwargs will be saved as attributes.
        """
        self._should_reattach_kernel_driver = False
        self.device = device
        self.description = description
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def find_supported_devices(cls):
        """Find compatible devices and return corresponding driver instances.

        Returns a list of driver class instances.
        """
        drivers = []
        for vid, pid, ver, description, kwargs in cls.supported_devices:
            usbdevs = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
            for dev in usbdevs:
                if ver and (dev.bcdDevice < ver[0] or dev.bcdDevice > ver[1]):
                    continue
                drivers.append(cls(dev, description, **kwargs))
        return drivers

    def connect(self):
        """Connect to the device."""
        if sys.platform.startswith('linux') and self.device.is_kernel_driver_active(0):
            liquidctl.util.debug('detaching currently active kernel driver')
            self.device.detach_kernel_driver(0)
            self._should_reattach_kernel_driver = True
        self.device.set_configuration()

    def disconnect(self):
        """Disconnect from the device."""
        usb.util.dispose_resources(self.device)
        if self._should_reattach_kernel_driver:
            liquidctl.util.debug('reattaching previously active kernel driver')
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

