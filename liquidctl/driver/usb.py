"""Base USB driver and device APIs.

This modules provides abstractions over several platform and implementation
differences.  As such, there is a lot of boilerplate here, but callers should
be able to disregard almost everything and simply work on the UsbDeviceDriver/
UsbHidDriver level.

UsbDeviceDriver
└── device: PyUsbDevice
    └── uses module usb (PyUSB)
        ├── libusb-1.0
        ├── libusb-0.1
        └── OpenUSB

UsbHidDriver
├── extends: UsbDeviceDriver
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
actual device drivers.  The users of those drivers generally do not care about
read, write or other low level operations; thus, these low level operations are
placed in <driver>.device.

However, there still are legitimate reasons as to why someone would want to
directly access the lower layers (device wrapper level, device implementation
level, or lower).  We do not hide or mark those references as private, but good
judgement should be exercised when calling anything within <driver>.device.

Finally, when subclassing any drivers, prefer to instantiate them through
find_supported_devices, rather than directly supplying a compatible device
wrapper.  The subclass constructor can generally be kept anaware of the
implementation details of the device parameter, and find_supported_devices
already accepts keyword arguments and forwards them to the constructor.

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

import usb

from liquidctl.driver.base import BaseDriver

LOGGER = logging.getLogger(__name__)


class UsbDeviceDriver(BaseDriver):
    """Base driver class for generic USB devices.

    Each driver should provide its own list of SUPPORTED_DEVICES, as well as
    implementations for all methods applicable to the devices is supports.

    SUPPORTED_DEVICES should consist of a list of (vendor id, product
    id, None (reserved), description, and extra kwargs) tuples.

    find_supported_devices will pass these extra kwargs, as well as any it
    receives, to the constructor.
    """

    SUPPORTED_DEVICES = []

    @classmethod
    def find_supported_devices(cls, **kwargs):
        """Find and bind to compatible devices."""
        drivers = []
        for vid, pid, _, description, devargs in cls.SUPPORTED_DEVICES:
            consargs = devargs.copy()
            consargs.update(kwargs)
            for dev in PyUsbDevice.enumerate(vid, pid):
                drivers.append(cls(dev, description, **consargs))
        return drivers

    def __init__(self, device, description, **kwargs):
        self.device = device
        self._description = description

    def connect(self, **kwargs):
        """Connect to the device."""
        self.device.open()

    def disconnect(self, **kwargs):
        """Disconnect from the device."""
        self.device.close()

    @property
    def description(self):
        """Human readable description of the corresponding device."""
        return self._description

    @property
    def vendor_id(self):
        """16-bit numeric vendor identifier."""
        return self.device.vendor_id

    @property
    def product_id(self):
        """16-bit umeric product identifier."""
        return self.device.product_id

    @property
    def release_number(self):
        """16-bit BCD device versioning number."""
        return self.device.release_number

    @property
    def serial_number(self):
        """Serial number reported by the device, or None if N/A."""
        return self.device.serial_number

    @property
    def bus(self):
        """Bus the device is connected to, or None if N/A."""
        return self.device.bus

    @property
    def address(self):
        """Address of the device on the corresponding bus, or None if N/A.

        Dependendent on bus enumeration order.
        """
        return self.device.address

    @property
    def port(self):
        """Physical location of the device, or None if N/A.

        Tuple of USB port numbers, from the root hub to this device.  Not
        dependendent on bus enumeration order.
        """
        return self.device.port


class UsbHidDriver(UsbDeviceDriver):
    """Base driver class for USB Human Interface Devices (HIDs)."""
    @classmethod
    def find_supported_devices(cls, hid=None, **kwargs):
        """Find and bind to compatible devices.

        Both hidapi and PyUSB backends are supported.  On Mac the default is
        hidapi; on all other platforms it is PyUSB.

        The choice of API for HID can be overiden with `hid`:

         - `hid='usb'`: use PyUSB (libusb-1.0, libusb-0.1 or OpenUSB)
         - `hid='hid'`: use hidapi (backend depends on hidapi build options)
         - `hid='hidraw'`: specifically try to use hidraw (Linux; depends on
           hidapi build options)
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

        drivers = []
        if wrapper == HidapiDevice:
            api = importlib.import_module(hid)
            for vid, pid, _, description, devargs in cls.SUPPORTED_DEVICES:
                consargs = devargs.copy()
                consargs.update(kwargs)
                for dev in wrapper.enumerate(api, vid, pid):
                    drivers.append(cls(dev, description, **consargs))
        else:
            for vid, pid, _, description, devargs in cls.SUPPORTED_DEVICES:
                consargs = devargs.copy()
                consargs.update(kwargs)
                for dev in PyUsbHid.enumerate(vid, pid):
                    drivers.append(cls(dev, description, **consargs))
        return drivers

    def __init__(self, device, description, **kwargs):
        # compatibility with v1.1.0 drivers (all HIDs): they could be directly
        # instantiated with a usb.core.Device (but don't do it in new code)
        if isinstance(device, usb.core.Device):
            LOGGER.warning('deprecated: delegate to find_supported_devices or use an appropriate wrapper')
            device = PyUsbHid(device)
        super().__init__(device, description, **kwargs)


class PyUsbDevice:
    """"A PyUSB backed device.

    PyUSB will automatically pick the first available backend (at runtime).
    The supported backends are:

     - libusb-1.0
     - libusb-0.1
     - OpenUSB
    """

    _DEFAULT_INTERFACE = 0  # FIXME not necessarily the desired interface

    def __init__(self, usbdev):
        self.api = usb
        self.usbdev = usbdev
        self._attached = False

    def open(self):
        """Connect to the device.

        Replace the kernel driver (Linux only) and set the device configuration
        to the first available one, if none has been set.
        """
        if (sys.platform.startswith('linux') and
                self.usbdev.is_kernel_driver_active(self._DEFAULT_INTERFACE)):
            LOGGER.debug('replacing stock kernel driver with libusb')
            self.usbdev.detach_kernel_driver(self._DEFAULT_INTERFACE)
            self._attached = True
        try:
            cfg = self.usbdev.get_active_configuration()
        except usb.core.USBError:
            LOGGER.debug('setting the (first) configuration')
            self.usbdev.set_configuration()
            # FIXME device is not ready yet

    def claim(self):
        """Explicitly claim the device from other programs."""
        LOGGER.debug('explicitly claim interface')
        usb.util.claim_interface(self.usbdev, self._DEFAULT_INTERFACE)

    def release(self):
        """Release the device to other programs."""
        LOGGER.debug('ensure interface is released')
        usb.util.release_interface(self.usbdev, self._DEFAULT_INTERFACE)

    def close(self):
        """Disconnect from the device.

        Clean up and (Linux only) reattach the kernel driver.
        """
        self.release()
        if self._attached:
            LOGGER.debug('restoring stock kernel driver')
            self.usbdev.attach_kernel_driver(self._DEFAULT_INTERFACE)

    def read(self, endpoint, length, timeout=None):
        """Read from endpoint."""
        return self.usbdev.read(endpoint, length, timeout=timeout)

    def write(self, endpoint, data, timeout=None):
        """Write to endpoint."""
        return self.usbdev.write(endpoint, data, timeout=timeout)

    def ctrl_transfer(self, bmRequestType, bRequest, wValue=0, wIndex=0,
                      data_or_wLength = None, timeout = None):
        return self.usbdev.ctrl_transfer(bmRequestType, bRequest,
                                         wValue=wValue, wIndex=wIndex,
                                         data_or_wLength=data_or_wLength,
                                         timeout=timeout)

    @classmethod
    def enumerate(cls, vid, pid):
        for handle in usb.core.find(idVendor=vid, idProduct=pid, find_all=True):
            yield cls(handle)

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
    def serial_number(self):
        return self.usbdev.serial_number

    @property
    def bus(self):
        return 'usb{}'.format(self.usbdev.bus)  # follow Linux model

    @property
    def address(self):
        return self.usbdev.address

    @property
    def port(self):
        return self.usbdev.port_numbers


class PyUsbHid(PyUsbDevice):
    """A PyUSB backed HID device.

    The signatures of read() and write() are changed from PyUsbDevice, and no
    longer accept target (in/out) endpoints, which are automatically inferred.

    This change (while unorthodox) unifies the behavior of read() and write()
    between PyUsbHid and HidapiDevice.
    """
    def __init__(self, usbdev):
        super().__init__(usbdev)
        self.hidin = 0x81
        self.hidout = 0x1  # FIXME apart from NZXT HIDs, usually ctrl (0x0)

    def read(self, length):
        """Read raw report from HID."""
        return self.usbdev.read(self.hidin, length, timeout=0)

    def write(self, data):
        """Write raw report to HID."""
        return self.usbdev.write(self.hidout, data, timeout=0)


class HidapiDevice:
    """A hidapi backed device.

    Depending on the platform, the selected `hidapi` and how it was built, this
    might use any of the following backends:

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
        """Connect to the device."""
        self.hiddev.open_path(self.hidinfo['path'])

    def claim(self):
        """NOOP."""
        pass

    def release(self):
        """NOOP."""
        pass

    def close(self):
        """NOOP."""
        pass

    def read(self, length):
        """Read raw report from HID."""
        return self.hiddev.read(length)

    def write(self, data):
        """Write raw report to HID."""
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
    def serial_number(self):
        return self.hidinfo['serial_number']

    @property
    def bus(self):
        return 'hid'  # follow Linux model

    @property
    def address(self):
        return None

    @property
    def port(self):
        return None

