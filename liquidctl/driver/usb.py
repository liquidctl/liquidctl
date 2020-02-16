"""Base USB bus, driver and device APIs.

This modules provides abstractions over several platform and implementation
differences.  As such, there is a lot of boilerplate here, but callers should
be able to disregard almost everything and simply work on the UsbDriver/
UsbHidDriver level.

BaseUsbDriver
└── device: PyUsbDevice
    └── uses module usb (PyUSB)
        ├── libusb-1.0
        ├── libusb-0.1
        └── OpenUSB

UsbHidDriver
├── extends: BaseUsbDriver
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

UsbDriver
├── extends: BaseUsbDriver
└── allows to differentiate between UsbHidDriver and (non Hid) UsbDriver

UsbDriver and UsbHidDriver are meant to be used as base classes to the actual
device drivers.  The users of those drivers generally do not care about read,
write or other low level operations; thus, these low level operations are
placed in <driver>.device.

However, there still are legitimate reasons as to why someone would want to
directly access the lower layers (device wrapper level, device implementation
level, or lower).  We do not hide or mark those references as private, but good
judgement should be exercised when calling anything within <driver>.device.

The USB drivers are organized into two buses.  The recommended way to
initialize and bind drivers is through their respective buses, though
<driver>.find_supported_devices can also be useful in certain scenarios.

GenericHidBus
└── drivers: all (recursive) subclasses of UsbHidDriver

PyUsbBus
└── drivers: all (recursive) subclasses of UsbDriver

The subclass constructor can generally be kept unaware of the implementation
details of the device parameter, and find_supported_devices already accepts
keyword arguments and forwards them to the driver constructor.

---

Base USB bus, driver and device APIs.
Copyright (C) 2019–2019  Jonas Malaco
Copyright (C) 2019–2019  each contribution's author

This file is part of liquidctl.

liquidctl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

liquidctl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import sys

import usb
import hid
try:
    import hidraw
except:
    hidraw = hid

from usb.util import ENDPOINT_IN, ENDPOINT_OUT, ENDPOINT_TYPE_INTR, CTRL_TYPE_CLASS, \
                     CTRL_RECIPIENT_INTERFACE

from liquidctl.driver.base import BaseDriver, BaseBus, find_all_subclasses

_CLASS_HID = 3
_ENDPOINT_DIR_MASK = 0x80
_ENDPOINT_TRANSFER_TYPE_MASK = 7
_HID_SET_REPORT = 0x09
_HID_OUTPUT = 2

LOGGER = logging.getLogger(__name__)


class BaseUsbDriver(BaseDriver):
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
    def probe(cls, handle, vendor=None, product=None, release=None,
              serial=None, match=None, **kwargs):
        """Probe `handle` and yield corresponding driver instances."""
        for vid, pid, _, description, devargs in cls.SUPPORTED_DEVICES:
            if (vendor and vendor != vid) or handle.vendor_id != vid:
                continue
            if (product and product != pid) or handle.product_id != pid:
                continue
            if release and handle.release_number != release:
                continue
            if serial and handle.serial_number != serial:
                continue
            if match and match.lower() not in description.lower():
                continue
            consargs = devargs.copy()
            consargs.update(kwargs)
            dev = cls(handle, description, **consargs)
            LOGGER.debug('instanced driver for %s', description)
            yield dev

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


class UsbHidDriver(BaseUsbDriver):
    """Base driver class for USB Human Interface Devices (HIDs)."""

    @classmethod
    def find_supported_devices(cls, hid=None, **kwargs):
        """Find devices specifically compatible with this driver."""
        devs = []
        for vid, pid, _, _, _ in cls.SUPPORTED_DEVICES:
            for dev in GenericHidBus().find_devices(hid=hid, vendor=vid, product=pid, **kwargs):
                if type(dev) == cls:
                    devs.append(dev)
        return devs

    def __init__(self, device, description, **kwargs):
        # compatibility with v1.1.0 drivers (all HIDs): they could be directly
        # instantiated with a usb.core.Device (but don't do it in new code)
        if isinstance(device, usb.core.Device):
            LOGGER.warning('deprecated: delegate to find_supported_devices or use an appropriate wrapper')
            device = PyUsbHid(device)
        self.device = device
        self._description = description


class UsbDriver(BaseUsbDriver):
    """Base driver class for regular USB devices.

    Specifically, regular USB devices are *not* Human Interface Devices (HIDs).
    """

    @classmethod
    def find_supported_devices(cls, hid=None, **kwargs):
        """Find devices specifically compatible with this driver."""
        devs = []
        for vid, pid, _, _, _ in cls.SUPPORTED_DEVICES:
            for dev in PyUsbBus().find_devices(vendor=vid, product=pid, **kwargs):
                if type(dev) == cls:
                    devs.append(dev)
        return devs

    def __init__(self, device, description, **kwargs):
        self.device = device
        self._description = description


class PyUsbDevice:
    """"A PyUSB backed device.

    PyUSB will automatically pick the first available backend (at runtime).
    The supported backends are:

     - libusb-1.0
     - libusb-0.1
     - OpenUSB
    """

    def __init__(self, usbdev, bInterfaceNumber=None):
        self.api = usb
        self.usbdev = usbdev
        self.bInterfaceNumber = bInterfaceNumber
        self._attached = False

    def _select_interface(self, cfg):
        return self.bInterfaceNumber or 0

    def open(self, bInterfaceNumber=0):
        """Connect to the device.

        Ensure the device is configured and replace the kernel kernel on the
        selected interface, if necessary.
        """
        try:
            cfg = self.usbdev.get_active_configuration()
        except usb.core.USBError:
            LOGGER.debug('setting the (first) configuration')
            self.usbdev.set_configuration()  # assume the first configuration
            # FIXME device or handle might not be ready for use after set_configuration()
            cfg = self.usbdev.get_active_configuration()
        self.bInterfaceNumber = self._select_interface(cfg)
        LOGGER.debug('selected interface: %d', self.bInterfaceNumber)
        if (sys.platform.startswith('linux') and
                self.usbdev.is_kernel_driver_active(self.bInterfaceNumber)):
            LOGGER.debug('replacing stock kernel driver with libusb')
            self.usbdev.detach_kernel_driver(self.bInterfaceNumber)
            self._attached = True

    def claim(self):
        """Explicitly claim the device from other programs."""
        LOGGER.debug('explicitly claim interface')
        usb.util.claim_interface(self.usbdev, self.bInterfaceNumber)

    def release(self):
        """Release the device to other programs."""
        LOGGER.debug('ensure interface is released')
        usb.util.release_interface(self.usbdev, self.bInterfaceNumber)

    def close(self):
        """Disconnect from the device.

        Clean up and (Linux only) reattach the kernel driver.
        """
        self.release()
        if self._attached:
            LOGGER.debug('restoring stock kernel driver')
            self.usbdev.attach_kernel_driver(self.bInterfaceNumber)
            self._attached = False

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
    def enumerate(cls, vid=None, pid=None):
        args = {}
        if vid:
            args['idVendor'] = vid
        if pid:
            args['idProduct'] = pid
        for handle in usb.core.find(find_all=True, **args):
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

    def __eq__(self, other):
        return type(self) == type(other) and self.bus == other.bus and self.address == other.address


class PyUsbHid(PyUsbDevice):
    """A PyUSB backed HID device.

    The signatures of read() and write() are changed from PyUsbDevice, and no
    longer accept target (in/out) endpoints, which are automatically inferred.

    This change (while unorthodox) unifies the behavior of read() and write()
    between PyUsbHid and HidapiDevice.
    """
    def __init__(self, usbdev):
        super().__init__(usbdev)
        self.ep_in = None
        self.ep_out = None

    def _select_interface(self, cfg):
        hid_intf = None
        for intf in cfg:
            if intf.bInterfaceClass != _CLASS_HID:
                continue
            hid_intf = intf
            for ep in intf:
                if (ep.bmAttributes & _ENDPOINT_TRANSFER_TYPE_MASK) != ENDPOINT_TYPE_INTR:
                    continue
                if not self.ep_in and (ep.bEndpointAddress & _ENDPOINT_DIR_MASK) == ENDPOINT_IN:
                    self.ep_in = ep.bEndpointAddress
                elif not self.ep_out:
                    self.ep_out = ep.bEndpointAddress
            break
        if not hid_intf:
            raise usb.core.USBError('Missing a HID interface')
        if not self.ep_in:
            raise usb.core.USBError('Missing an interrupt IN endpoint')
        # if ep_out is not available Set_Report will be sent on CTRL OUT (0x00)
        LOGGER.debug('hid endpoints: %#04x (IN), %#04x (OUT)', self.ep_in, self.ep_out or 0)
        return hid_intf.bInterfaceNumber

    def read(self, length):
        """Read raw report from HID."""
        return self.usbdev.read(self.ep_in, length, timeout=0)

    def write(self, data):
        """Write raw report to HID.

        The first byte of the buffer passed to write() should be set to the
        report number.  If the device does not use numbered reports, the first
        byte should be set to 0. The report data itself should begin at the
        second byte.

        The distinction between report number and data is
        important for compatibility with kernel APIs and HidapiDevice.
        """
        # report_id == 0 means it's not used, so it isn't actually sent;
        # mimicking hidapi on libusb, this is transparently handled
        report_id = data[0]
        if not report_id:
            data = data[1:]
        if self.ep_out:
            sent = self.usbdev.write(self.ep_out, data, timeout=0)
        else:
            sent = self.ctrl_transfer(
                    bmRequestType=CTRL_TYPE_CLASS | CTRL_RECIPIENT_INTERFACE | ENDPOINT_OUT,
                    bRequest=_HID_SET_REPORT,
                    wValue=(_HID_OUTPUT << 8) | report_id,
                    wIndex=self.bInterfaceNumber,
                    data_or_wLength=data)
        if not report_id:
            sent += 1
        return sent


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
        """Write raw report to HID.

        The first byte of the buffer passed to write() should be set to the
        report number.  If the device does not use numbered reports, the first
        byte should be set to 0. The report data itself should begin at the
        second byte.
        """
        return self.hiddev.write(data)

    @classmethod
    def enumerate(cls, api, vid=None, pid=None):
        infos = api.enumerate(vid or 0, pid or 0)
        if sys.platform == 'darwin':
            infos = sorted(infos, key=lambda info: info['path'])
        for info in infos:
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
        return self.hidinfo['path'].decode()

    @property
    def port(self):
        return None

    def __eq__(self, other):
        return type(self) == type(other) and self.bus == other.bus and self.address == other.address


class GenericHidBus(BaseBus):

    def find_devices(self, vendor=None, product=None, hid=None, bus=None,
                     address=None, usb_port=None, **kwargs):
        """Find compatible USB HID devices.

        Both hidapi and PyUSB backends are supported.  On Mac and Linux the
        default is to use hidapi; on all other platforms it is PyUSB.

        The choice of API for HID can be overiden with `hid`:

         - `hid='usb'`: use PyUSB (libusb-1.0, libusb-0.1 or OpenUSB)
         - `hid='hid'`: use hidapi (backend depends on hidapi build options)
         - `hid='hidraw'`: specifically try to use hidraw (Linux; depends on
           hidapi build options)
        """

        if not hid:
            if sys.platform.startswith('linux'):
                hid = 'hidraw'
            elif sys.platform == 'darwin':
                hid = 'hid'
            else:
                hid = 'usb'

        api = globals()[hid]
        if hid.startswith('hid'):
            handles = HidapiDevice.enumerate(api, vendor, product)
        else:
            handles = PyUsbHid.enumerate(vendor, product)

        drivers = sorted(find_all_subclasses(UsbHidDriver), key=lambda x: x.__name__)
        LOGGER.debug('searching %s (api=%s, drivers=[%s])', self.__class__.__name__, api.__name__,
                     ', '.join(map(lambda x: x.__name__, drivers)))
        for handle in handles:
            if bus and handle.bus != bus:
                continue
            if address and handle.address != address:
                continue
            if usb_port and handle.port != usb_port:
                continue
            LOGGER.debug('probing drivers for device %04x:%04x', handle.vendor_id,
                         handle.product_id)
            for drv in drivers:
                yield from drv.probe(handle, vendor=vendor, product=product, **kwargs)


class PyUsbBus(BaseBus):
    def find_devices(self, vendor=None, product=None, bus=None, address=None,
                     usb_port=None, **kwargs):
        """ Find compatible regular USB devices."""
        drivers = sorted(find_all_subclasses(UsbDriver), key=lambda x: x.__name__)
        LOGGER.debug('searching %s (drivers=[%s])', self.__class__.__name__,
                     ', '.join(map(lambda x: x.__name__, drivers)))
        for handle in PyUsbDevice.enumerate(vendor, product):
            if bus and handle.bus != bus:
                continue
            if address and handle.address != address:
                continue
            if usb_port and handle.port != usb_port:
                continue
            LOGGER.debug('probing drivers for device %04x:%04x', handle.vendor_id,
                         handle.product_id)
            for drv in drivers:
                yield from drv.probe(handle, vendor=vendor, product=product, **kwargs)
