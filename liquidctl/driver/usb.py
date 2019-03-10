"""Base USB driver and device APIs.

This modules provides abstractions over several platform and implementation
differences.  As such, there is a lot of boilerplate here, but callers should
be able to disregard most differences and simply work on the UsbDeviceDriver/
UsbHidDriver level.

UsbDeviceDriver
└── device: PyUsbDevice
    └── uses module usb (PyUSB)
        ├── libusb-1.0
        ├── libusb-0.1
        └── OpenUSB

UsbHidDriver
├── device: PyUsbHid
│   └── extends PyUsbDevice
│       └── uses module usb (PyUSB)
│           ├── libusb-1.0
│           ├── libusb-0.1
│           └── OpenUSB
└── device: HidapiDevice
    ├── uses module hid (hidapi)
    │   ├── hid.dll (Windows)
    │   ├── hidraw (Linux, depends on hidapi build options)
    │   ├── IOHidManager (MacOS)
    │   └── libusb-1
    └── uses module hidraw (hidapi, depends on build options)
        └── hidraw (Linux)

UsbDeviceDriver and UsbHidDriver are meant to be used as base classes to the
actual device drivers.  The users of those drivers do not care about read,
write or other low level operations; thus, these are placed in <driver>.device.

However, there are legitimate reasons as to why a caller would want to directly
access the lower layers (device wrapper level, device implementation level, or
lower).  We do not hide or mark those references as private, but good judgement
should be exercised when calling anything in <driver>.device.

Copyright (C) 2019  Jonas Malaco
Copyright (C) 2019  each contribution's author

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
            wrapper = PyUsbHid
        elif sys.platform.startswith('darwin'):
            wrapper = HidapiDevice
            hid = 'hid'
        else:
            wrapper = PyUsbHid
            hid = 'usb'
        api = importlib.import_module(hid)
        drivers = []
        for vid, pid, _, description, devargs in cls.SUPPORTED_DEVICES:
            consargs = devargs.copy()
            consargs.update(kwargs)
            for dev in wrapper.enumerate(api, vid, pid):
                drivers.append(cls(dev, description, **consargs))
        return drivers

    def __init__(self, device, description, **kwargs):
        self.device = device
        self._description = description
        driver_name = type(self).__name__
        wrapper_name = type(self.device).__name__
        api_name = self.device.api.__name__

    def connect(self, **kwargs):
        """Connect to the device."""
        self.device.open()

    def disconnect(self, **kwargs):
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
    def release_number(self):
        return self.device.release_number

    @property
    def bus(self):
        return self.device.bus

    @property
    def address(self):
        return self.device.address

    @property
    def port(self):
        return self.device.port

    @property
    def serial_number(self):
        return self.device.serial_number


class PyUsbDevice:
    """"A PyUSB backed device."""

    def __init__(self, api, usbdev):
        self.api = api
        self.usbdev = usbdev
        self._attached = False

    def open(self):
        """Connect to the device.

        Replace the kernel driver (Linux only) and set the device configuration
        to the first available one, if none has been set.
        """
        if sys.platform.startswith('linux') and self.usbdev.is_kernel_driver_active(0):
            LOGGER.debug('replacing stock kernel driver with libusb')
            self.usbdev.detach_kernel_driver(0)
            self._attached = True
        cfg = self.usbdev.get_active_configuration()
        if cfg is None:
            LOGGER.debug('setting the (first) configuration')
            self.usbdev.set_configuration()

    def release(self):
        self.api.util.dispose_resources(self.usbdev)

    def close(self):
        """Disconnect from the device.

        Clean up and (Linux only) reattach the kernel driver.
        """
        self.release()
        if self._attached:
            LOGGER.debug('restoring stock kernel driver')
            self.usbdev.attach_kernel_driver(0)

    def read(self, endpoint, length):
        return self.usbdev.read(endpoint, length)

    def write(self, endpoint, data):
        return self.usbdev.write(endpoint, data)

    @classmethod
    def enumerate(cls, api, vid, pid):
        for handle in api.core.find(idVendor=vid, idProduct=pid, find_all=True):
            yield cls(api, handle)

    @property
    def vendor_id(self):
        return self.usbdev.idVendor

    @property
    def product_id(self):
        return self.usbdev.idProduct

    @property
    def release_number(self):
        return self.usbdev.bcdDevice

    @property
    def bus(self):
        return 'usb{}'.format(self.usbdev.bus)  # follow Linux model

    @property
    def address(self):
        return self.usbdev.address

    @property
    def port(self):
        return self.usbdev.port_numbers

    @property
    def serial_number(self):
        return self.usbdev.serial_number


class PyUsbHid(PyUsbDevice):
    """A PyUSB backed HID device.

    The signatures of read() and write() are changed, and no longer accept
    target (in/out) endpoints, which are automatically inferred.

    This (while unorthodox) unifies the behavior of read() and write() between
    PyUsbHid and HidapiDevice.
    """
    def __init__(self, api, usbdev):
        super().__init__(api, usbdev)
        self.hidin = 0x81
        self.hidout = 0x1  # FIXME apart from NZXT HIDs, usually ctrl (0x0)

    def read(self, length):
        return self.usbdev.read(self.hidin, length)

    def write(self, data):
        return self.usbdev.write(self.hidout, data)


class HidapiDevice:
    """A hidapi backed device.

    Depending on the platform, the selected api and how the package was built,
    this might use any of the following backends:

     - Windows (using hid.dll)
     - Linux/hidraw (using the Kernel's hidraw driver)
     - Linux/libusb (using libusb-1.0)
     - FreeBSD (using libusb-1.0)
     - Mac (using IOHidManager)

    The default hidapi API is the module 'hid'.  On standard Linux builds of the
    hidapi package, this will default to a libusb-1.0 backed implementation; at
    the same time, an alternate 'hidraw' module will also be available in
    normal installations.

    Note: if 'hid' is used with libusb on Linux, it will detach the Kernel
    driver but fail to reattach it later, making hidraw and hwmon unavailable
    on that devcie.  To fix, rebind the device to usbhid with:

        echo '<bus>-<port>:1.0' | _ tee /sys/bus/usb/drivers/usbhid/bind
    """
    def __init__(self, hidapi, hidapi_dev_info):
        self.api = hidapi
        self.hidinfo = hidapi_dev_info
        self.hiddev = self.api.device()

    def open(self):
        self.hiddev.open_path(self.hidinfo['path'])

    def release(self):
        pass

    def close(self):
        pass

    def read(self, length):
        return self.hiddev.read(length)

    def write(self, data):
        return self.hiddev.write(data)

    @classmethod
    def enumerate(cls, api, vid, pid):
        for info in api.enumerate(vid, pid):
            yield cls(api, info)

    @property
    def vendor_id(self):
        return self.hidinfo['vendor_id']

    @property
    def product_id(self):
        return self.hidinfo['product_id']

    @property
    def release_number(self):
        return self.hidinfo['release_number']

    @property
    def bus(self):
        return 'hid'  # follow Linux model

    @property
    def address(self):
        return None

    @property
    def port(self):
        return None

    @property
    def serial_number(self):
        return self.hidinfo['serial_number']

