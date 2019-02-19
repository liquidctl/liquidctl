"""Base USB driver and device API.

Copyright (C) 2018-2019  Jonas Malaco
Copyright (C) 2018-2019  each contribution's author

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

import importlib
import logging
import sys

from liquidctl.driver.base import BaseDriver

LOGGER = logging.getLogger(__name__)


class UsbHidDriver(BaseDriver):
    """Base driver class for USB Human Interface Devices (HIDs).

    Each driver should provide its own list of SUPPORTED_DEVICES, as well as
    implementations for all methods applicable to the devices is supports.

    SUPPORTED_DEVICES should consist of a list of tuples (vendor id, product
    id, None (reserved), description, and extra kwargs).  The extra keyword
    arguments will be passed to the constructor.
    """

    SUPPORTED_DEVICES = []

    @classmethod
    def find_supported_devices(cls, hid=None, **kwargs):
        """Find and bind to compatible devices.

        Both hidapi and PyUSB backends are supported.  On all platforms except
        MacOS, the default is to use PyUSB.

        This can be overiden with `hid`:

         - `usb`: use default PyUSB backend (depends on available runtime libraries)
         - `hid`: use default hidapi backend (depends on hidapi build options)
         - `hidraw`: use hidraw hidapi backend (Linux; depends on hidapi build options)
        """
        if hid == 'hidraw' or hid == 'hid':
            wrapper = HidapiDevice
        elif hid == 'usb':
            wrapper = PyUsbHidDevice
        elif sys.platform.startswith('darwin'):
            wrapper = HidapiDevice
            hid = 'hid'
        else:
            wrapper = PyUsbHidDevice
            hid = 'usb'
        api = importlib.import_module(hid)
        drivers = []
        for vid, pid, _, description, devargs in cls.SUPPORTED_DEVICES:
            devargs.update(kwargs)
            for dev in wrapper.enumerate(api, vid, pid):
                drivers.append(cls(dev, description, **devargs))
        return drivers

    def __init__(self, device, description, **kwargs):
        self.device = device
        self._description = description
        driver_name = type(self).__name__
        wrapper_name = type(self.device).__name__
        api_name = self.device.api.__name__

    def connect(self):
        """Connect to the device."""
        self.device.open()

    def disconnect(self):
        """Disconnect from the device."""
        self.device.close()

    @property
    def description(self):
        return self._description

    @property
    def vendor_id(self):
        return self.device.vendor_id

    @property
    def product_id(self):
        return self.device.product_id

    @property
    def implementation(self):
        return '{}={}'.format(type(self.device).__name__, self.device.api.__name__)

    @property
    def device_infos(self):
        return self.device.infos


class PyUsbHidDevice:
    """"A PyUSB backed device."""

    def __init__(self, api, device):
        self.api = api
        self._device = device
        self._read_endpoint = 0x81  # FIXME
        self._write_endpoint = 0x1  # FIXME
        self._attached = False
        self._device_infos = None

    def open(self):
        """Connect to the device.

        Replace the kernel driver (Linux only) and set the device configuration
        to the first available one, if none has been set.
        """
        if sys.platform.startswith('linux') and self._device.is_kernel_driver_active(0):
            LOGGER.debug('replacing stock kernel driver with libusb')
            self._device.detach_kernel_driver(0)
            self._attached = True
        cfg = self._device.get_active_configuration()
        if cfg is None:
            LOGGER.debug('setting the (first) configuration')
            self._device.set_configuration()

    def release(self):
        self.api.util.dispose_resources(self._device)

    def close(self):
        """Disconnect from the device.

        Clean up and (Linux only) reattach the kernel driver.
        """
        self.release()
        if self._attached:
            LOGGER.debug('restoring stock kernel driver')
            self._device.attach_kernel_driver(0)

    def read(self, length):
        return self._device.read(self._read_endpoint, length)

    def write(self, data):
        return self._device.write(self._write_endpoint, data)

    @classmethod
    def enumerate(cls, api, vid, pid):
        for handle in api.core.find(idVendor=vid, idProduct=pid, find_all=True):
            yield cls(api, handle)

    @property
    def vendor_id(self):
        return self._device.idVendor

    @property
    def product_id(self):
        return self._device.idProduct

    @property
    def infos(self):
        if not self._device_infos:
            self._device_infos = {
                'vendor_id': self._device.idVendor,
                'product_id': self._device.idProduct,
                'serial_number': self._device.serial_number,
                'release_number': self._device.bcdDevice,
                'manufacturer_string': self._device.manufacturer,
                'product_string': self._device.product,
                'port_number': self._device.port_number,
                'interface_number': 0  # FIXME
            }
        return self._device_infos


class HidapiDevice:
    """A hidapi backed device.

    Depending on the platform, the selected api and how the package was built,
    this might use any of the following backends:

     - Windows (using hid.dll)
     - Linux/hidraw (using the Kernel's hidraw driver)
     - Linux/libusb (using libusb-1.0)
     - FreeBSD (using libusb-1.0)
     - Mac (using IOHidManager)

    The default API is the module 'hid'.  On standard Linux builds of the
    hidapi package, this will default to a libusb-1.0 backed implementation; at
    the same time, an alternate 'hidraw' module will also be available in
    normal installations.
    """
    def __init__(self, api, info):
        self.api = api
        self.device_infos = info
        self._device = self.api.device()

    def open(self):
        self._device.open_path(self.device_infos['path'])

    def release(self):
        pass

    def close(self):
        pass

    def read(self, length):
        return self._device.read(length)

    def write(self, data):
        return self._device.write(data)

    @classmethod
    def enumerate(cls, api, vid, pid):
        for info in api.enumerate(vid, pid):
            yield cls(api, info)

    @property
    def vendor_id(self):
        return self.device_infos['vendor_id']

    @property
    def product_id(self):
        return self.device_infos['product_id']

    @property
    def infos(self):
        return self.device_infos

