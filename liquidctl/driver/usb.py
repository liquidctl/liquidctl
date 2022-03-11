"""Base USB bus, driver and device APIs.

This modules provides abstractions over several platform and implementation
differences.  As such, there is a lot of boilerplate here, but callers should
be able to disregard almost everything and simply work on the UsbDriver/
UsbHidDriver level.

BaseUsbDriver
└── device: PyUsbDevice
    ├── uses PyUSB
    └── backed by (in order of priority)
        ├── libusb-1.0
        ├── libusb-0.1
        └── OpenUSB

UsbHidDriver
├── extends: BaseUsbDriver
└── device: HidapiDevice
    ├── uses hidapi
    └── backed by
        ├── hid.dll on Windows
        ├── hidraw on Linux if it was enabled during the build of hidapi
        ├── IOHidManager on MacOS
        └── libusb-1.0 on all other cases

UsbDriver
├── extends: BaseUsbDriver
└── allows to differentiate between UsbHidDriver and (non HID) UsbDriver

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

HidapiBus
└── drivers: all (recursive) subclasses of UsbHidDriver

PyUsbBus
└── drivers: all (recursive) subclasses of UsbDriver

The subclass constructor can generally be kept unaware of the implementation
details of the device parameter, and find_supported_devices already accepts
keyword arguments and forwards them to the driver constructor.

Copyright (C) 2019–2022  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import sys

import usb
try:
    # The hidapi package, depending on how it's compiled, exposes one or two
    # top level modules: hid and, optionally, hidraw.  When both are available,
    # hid will be a libusb-based fallback implementation, and we prefer hidraw.
    import hidraw as hid
except ModuleNotFoundError:
    import hid
try:
    import libusb_package
except ModuleNotFoundError:
    libusb_package = None

from liquidctl.driver.base import BaseDriver, BaseBus, find_all_subclasses
from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.util import LazyHexRepr

_LOGGER = logging.getLogger(__name__)


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
        for vid, pid, _, desc, devargs in cls.SUPPORTED_DEVICES:
            if (vendor and vendor != vid) or handle.vendor_id != vid:
                continue
            if (product and product != pid) or handle.product_id != pid:
                continue
            if release and handle.release_number != release:
                continue
            if serial and handle.serial_number != serial:
                continue
            if match and match.lower() not in desc.lower():
                continue
            consargs = devargs.copy()
            consargs.update(kwargs)
            dev = cls(handle, desc, **consargs)
            _LOGGER.debug('found %s: %s', cls.__name__, desc)
            yield dev

    def __init__(self, device, description, **kwargs):
        self.device = device
        self._description = description

    def connect(self, **kwargs):
        """Connect to the device."""
        self.device.open()
        return self

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
    def find_supported_devices(cls, **kwargs):
        """Find devices specifically compatible with this driver."""
        devs = []
        for vid, pid, _, _, _ in cls.SUPPORTED_DEVICES:
            for dev in HidapiBus().find_devices(vendor=vid, product=pid, **kwargs):
                if type(dev) == cls:
                    devs.append(dev)
        return devs

    def __init__(self, device, description, **kwargs):
        # compatibility with v1.1.0 drivers, which could be directly
        # instantiated with a usb.core.Device
        if isinstance(device, usb.core.Device):
            clname = self.__class__.__name__
            _LOGGER.warning('constructing a %s instance from a usb.core.Device has been deprecated, '
                            'use %s.find_supported_devices() or pass a HidapiDevice handle', clname, clname)
            usbdev = device
            hidinfo = next(info for info in hid.enumerate(usbdev.idVendor, usbdev.idProduct)
                           if info['serial_number'] == usbdev.serial_number)
            assert hidinfo, 'Could not find device in HID bus'
            device = HidapiDevice(hid, hidinfo)
        super().__init__(device, description, **kwargs)
        self._hwmon = HwmonDevice.from_hidraw(device.path)
        if self._hwmon:
            _LOGGER.debug('has kernel driver: %s (%s)', self._hwmon.module, self._hwmon.path)


class UsbDriver(BaseUsbDriver):
    """Base driver class for regular USB devices.

    Specifically, regular USB devices are *not* Human Interface Devices (HIDs).
    """

    @classmethod
    def find_supported_devices(cls, **kwargs):
        """Find devices specifically compatible with this driver."""
        devs = []
        for vid, pid, _, _, _ in cls.SUPPORTED_DEVICES:
            for dev in PyUsbBus().find_devices(vendor=vid, product=pid, **kwargs):
                if type(dev) == cls:
                    devs.append(dev)
        return devs


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

        # we assume the device is already configured, there is only one
        # configuration, or the first one is desired

        try:
            cfg = self.usbdev.get_active_configuration()
        except usb.core.USBError as err:
            if err.args[0] == 'Configuration not set':
                _LOGGER.debug('setting the (first) configuration')
                self.usbdev.set_configuration()
                # FIXME device or handle might not be ready for use yet
                cfg = self.usbdev.get_active_configuration()
            else:
                raise

        self.bInterfaceNumber = self._select_interface(cfg)
        _LOGGER.debug('selected interface: %d', self.bInterfaceNumber)

        if (sys.platform.startswith('linux') and
                self.usbdev.is_kernel_driver_active(self.bInterfaceNumber)):
            _LOGGER.debug('replacing stock kernel driver with libusb')
            self.usbdev.detach_kernel_driver(self.bInterfaceNumber)
            self._attached = True

    def claim(self):
        """Explicitly claim the device from other programs."""
        _LOGGER.debug('explicitly claim interface')
        usb.util.claim_interface(self.usbdev, self.bInterfaceNumber)

    def release(self):
        """Release the device to other programs."""
        if sys.platform == 'win32':
            # on Windows we need to release the entire device for other
            # programs to be able to access it
            _LOGGER.debug('explicitly release device')
            usb.util.dispose_resources(self.usbdev)
        else:
            # on Linux, and possibly on Mac and BSDs, releasing the specific
            # interface is enough
            _LOGGER.debug('explicitly release interface')
            usb.util.release_interface(self.usbdev, self.bInterfaceNumber)

    def close(self):
        """Disconnect from the device.

        Clean up and (Linux only) reattach the kernel driver.
        """
        self.release()
        if self._attached:
            _LOGGER.debug('restoring stock kernel driver')
            self.usbdev.attach_kernel_driver(self.bInterfaceNumber)
            self._attached = False

    def read(self, endpoint, length, timeout=None):
        """Read from endpoint."""
        data = self.usbdev.read(endpoint, length, timeout=timeout)
        _LOGGER.debug('read %d bytes: %r', len(data), LazyHexRepr(data))
        return data

    def write(self, endpoint, data, timeout=None):
        """Write to endpoint."""
        _LOGGER.debug('writting %d bytes: %r', len(data), LazyHexRepr(data))
        return self.usbdev.write(endpoint, data, timeout=timeout)

    def ctrl_transfer(self, *args, **kwargs):
        """Submit a contrl transfer."""
        _LOGGER.debug('sending control transfer with %r, %r', args, kwargs)
        return self.usbdev.ctrl_transfer(*args, **kwargs)

    @classmethod
    def enumerate(cls, vid=None, pid=None):
        args = {}
        if vid:
            args['idVendor'] = vid
        if pid:
            args['idProduct'] = pid
        if libusb_package and (sys.platform == 'win32' or sys.platform == 'cygwin'):
            _LOGGER.debug('using libusb_package.find')
            find = libusb_package.find
        else:
            find = usb.core.find
        for handle in find(find_all=True, **args):
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
        return f'usb{self.usbdev.bus}'  # follow Linux model

    @property
    def address(self):
        return self.usbdev.address

    @property
    def port(self):
        return self.usbdev.port_numbers

    def __eq__(self, other):
        return type(self) == type(other) and self.bus == other.bus and self.address == other.address


class HidapiDevice:
    """A hidapi backed device.

    Depending on the platform, the selected `hidapi` and how it was built, this
    might use any of the following backends:

     - hid.dll on Windows
     - hidraw on Linux, if it was enabled during the build of hidapi
     - IOHidManager on MacOS
     - libusb-1.0 on all other cases

    The default hidapi API is the module 'hid'.  On standard Linux builds of
    the hidapi package, this might default to a libusb-1.0 backed
    implementation; at the same time an alternate 'hidraw' module may also be
    provided.  The latter is prefered, when available.

    Note: if a libusb-backed 'hid' is used on Linux (assuming default build
    options) it will detach the kernel driver, making hidraw and hwmon
    unavailable for that device.  To fix, rebind the device to usbhid with:

        echo '<bus>-<port>:1.0' | sudo tee /sys/bus/usb/drivers/usbhid/bind
    """
    def __init__(self, hidapi, hidapi_dev_info):
        self.api = hidapi
        self.hidinfo = hidapi_dev_info
        self.hiddev = self.api.device()

    def open(self):
        """Connect to the device."""
        self.hiddev.open_path(self.hidinfo['path'])

    def close(self):
        """NOOP."""
        self.hiddev.close()

    def clear_enqueued_reports(self):
        """Clear already enqueued incoming reports.

        The OS generally enqueues incomming reports for open HIDs, and hidapi
        emulates this when running on top of libusb.  On Linux, up to 64
        reports can be enqueued.

        This method quickly reads and discards any already enqueued reports,
        and is useful when later reads are not expected to return stale data.
        """
        if self.hiddev.set_nonblocking(True) == 0:
            timeout_ms = 0  # use hid_read; wont block because call succeeded
        else:
            timeout_ms = 1  # smallest timeout forwarded to hid_read_timeout
        discarded = 0
        while self.hiddev.read(max_length=1, timeout_ms=timeout_ms):
            discarded += 1
        _LOGGER.debug('discarded %d previously enqueued reports', discarded)

    def read(self, length):
        """Read raw report from HID.

        The returned data follows the semantics of the Linux HIDRAW API.

        > On a device which uses numbered reports, the first byte of the
        > returned data will be the report number; the report data follows,
        > beginning in the second byte. For devices which do not use numbered
        > reports, the report data will begin at the first byte.
        """
        self.hiddev.set_nonblocking(False)
        data = self.hiddev.read(length)
        _LOGGER.debug('read %d bytes: %r', len(data), LazyHexRepr(data))
        return data

    def write(self, data):
        """Write raw report to HID.

        The buffer should follow the semantics of the Linux HIDRAW API.

        > The first byte of the buffer passed to write() should be set to the
        > report number.  If the device does not use numbered reports, the
        > first byte should be set to 0. The report data itself should begin
        > at the second byte.
        """
        _LOGGER.debug('writting report 0x%02x with %d bytes: %r', data[0],
                      len(data) - 1, LazyHexRepr(data, start=1))
        res = self.hiddev.write(data)
        if res < 0:
            raise OSError('Could not write to device')
        if res != len(data):
            _LOGGER.debug('wrote %d total bytes, expected %d', res, len(data))
        return res

    def get_feature_report(self, report_id, length):
        """Get feature report that matches `report_id` from HID.

        If the device does not use numbered reports, set `report_id` to 0.

        Unlike `read`, the returned data follows semantics similar to `write`
        and `send_feature_report`: the first byte will always contain the
        report ID (or 0), and the report data itself will being at the second
        byte.
        """
        data = self.hiddev.get_feature_report(report_id, length)
        _LOGGER.debug('got feature report 0x%02x with %d bytes: %r', data[0],
                      len(data) - 1, LazyHexRepr(data, start=1))
        return data

    def send_feature_report(self, data):
        """Send feature report to HID.

        The buffer should follow the semantics of `write`.

        > The first byte of the buffer passed to write() should be set to the
        > report number.  If the device does not use numbered reports, the
        > first byte should be set to 0. The report data itself should begin
        > at the second byte.
        """
        _LOGGER.debug('sending feature report 0x%02x with %d bytes: %r',
                      data[0], len(data) - 1, LazyHexRepr(data, start=1))
        res = self.hiddev.send_feature_report(data)
        if res < 0:
            raise OSError('Could not send feature report to device')
        if res != len(data):
            _LOGGER.debug('sent %d total bytes, expected %d', res, len(data))
        return res

    @classmethod
    def enumerate(cls, api, vid=None, pid=None):
        infos = api.enumerate(vid or 0, pid or 0)
        if sys.platform == 'darwin':
            infos = sorted(infos, key=lambda info: info['path'])
        for info in infos:
            yield cls(api, info)

    @property
    def path(self):
        return self.hidinfo['path']

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
        return self.hidinfo['path'].decode(errors='replace')

    @property
    def port(self):
        return None

    def __eq__(self, other):
        return type(self) == type(other) and self.bus == other.bus and self.address == other.address


class HidapiBus(BaseBus):
    def find_devices(self, vendor=None, product=None, bus=None, address=None,
                     usb_port=None, **kwargs):
        """Find compatible HID devices."""
        handles = HidapiDevice.enumerate(hid, vendor, product)
        drivers = sorted(find_all_subclasses(UsbHidDriver), key=lambda x: x.__name__)
        _LOGGER.debug('searching %s', self.__class__.__name__)
        _LOGGER.debug(
            '%s drivers: %s',
            self.__class__.__name__,
            ', '.join(map(lambda x: x.__name__, drivers))
        )
        for handle in handles:
            if bus and handle.bus != bus:
                continue
            if address and handle.address != address:
                continue
            if usb_port and handle.port != usb_port:
                continue
            # each handle is a HIDAPI hid_device, and that can either mean one
            # entire HID interface, or one interface ⨯ usage page ⨯ usage id
            # product, depending on the platform and backend; but, for brevity,
            # refer them simply as "HID devices"
            if 'usage' in handle.hidinfo and 'usage_page' in handle.hidinfo:
                _LOGGER.debug(
                    'HID device: %04x:%04x (usage_page=%#06x usage=%#06x)',
                    handle.vendor_id,
                    handle.product_id,
                    handle.hidinfo['usage_page'],
                    handle.hidinfo['usage'],
                )
            else:
                _LOGGER.debug(
                    'HID device: %04x:%04x (usage n/a)',
                    handle.vendor_id,
                    handle.product_id,
                )
            for drv in drivers:
                yield from drv.probe(handle, vendor=vendor, product=product, **kwargs)


class PyUsbBus(BaseBus):
    def find_devices(self, vendor=None, product=None, bus=None, address=None,
                     usb_port=None, **kwargs):
        """ Find compatible regular USB devices."""
        drivers = sorted(find_all_subclasses(UsbDriver), key=lambda x: x.__name__)
        _LOGGER.debug('searching %s', self.__class__.__name__)
        _LOGGER.debug(
            '%s drivers: %s',
            self.__class__.__name__,
            ', '.join(map(lambda x: x.__name__, drivers))
        )
        for handle in PyUsbDevice.enumerate(vendor, product):
            if bus and handle.bus != bus:
                continue
            if address and handle.address != address:
                continue
            if usb_port and handle.port != usb_port:
                continue
            _LOGGER.debug('USB device: %04x:%04x', handle.vendor_id, handle.product_id)
            for drv in drivers:
                yield from drv.probe(handle, vendor=vendor, product=product, **kwargs)
