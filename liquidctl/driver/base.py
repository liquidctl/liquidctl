"""Base driver API.

Copyright (C) 2018–2019  Jonas Malaco
Copyright (C) 2018–2019  each contribution's author

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

class BaseDriver:
    """Base driver API.

    All drivers are expected to implement this API for compatibility with the
    liquidctl CLI or other thirdy party tools.

    Example usage:

        for dev in <Driver>.find_supported_devices():
            dev.connect()
            print(dev.get_status())
            if dev.serial_number == '49385027ZP':
                dev.set_fixed_speed("fan3", 42)
            dev.disconnect()

    """

    @classmethod
    def find_supported_devices(cls, **kwargs):
        """Find and bind to compatible devices.

        Returns a list of bound driver instances.
        """
        raise NotImplementedError()

    def connect(self, **kwargs):
        """Connect to the device.

        Procedure before any read or write operation can be performed.
        Typically a handshake between driver and device.
        """
        raise NotImplementedError()

    def initialize(self, **kwargs):
        """Initialize the device.

        Apart from `connect()`, some devices might require a onetime
        intialization procedure after powering on, or to detect hardware
        changes.  This should be called *after* connecting to the device.
        """
        raise NotImplementedError()

    def disconnect(self, **kwargs):
        """Disconnect from the device.

        Procedure before the driver can safely unbind from the device.
        Typically just cleanup.
        """
        raise NotImplementedError()

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        raise NotImplementedError()

    def set_color(self, channel, mode, colors, **kwargs):
        """Set the color mode for a specific channel."""
        raise NotImplementedError()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to follow a speed duty profile."""
        raise NotImplementedError()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        raise NotImplementedError()

    @property
    def description(self):
        """Human readable description of the corresponding device."""
        raise NotImplementedError()

    @property
    def vendor_id(self):
        """Numeric vendor identifier."""
        raise NotImplementedError()

    @property
    def product_id(self):
        """Numeric product identifier."""
        raise NotImplementedError()

    @property
    def release_number(self):
        """Device versioning number, or None if N/A.

        In USB devices this is bcdDevice.
        """
        raise NotImplementedError()

    @property
    def serial_number(self):
        """Serial number reported by the device, or None if N/A."""
        raise NotImplementedError()

    @property
    def bus(self):
        """Bus the device is connected to, or None if N/A."""
        raise NotImplementedError()

    @property
    def address(self):
        """Address of the device on the corresponding bus, or None if N/A.

        This typically depends on the bus enumeration order.
        """
        raise NotImplementedError()

    @property
    def port(self):
        """Physical location of the device, or None if N/A.

        This typically refers to a USB port, which is *not* dependent on bus
        enumeration order.  However, a USB port is hub-specific, and hubs can
        be chained.  Thus, for USB devices, this returns a tuple of port
        numbers, from the root hub to the parent of the connected device.
        """
        raise NotImplementedError()

