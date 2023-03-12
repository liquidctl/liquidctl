import logging

from liquidctl.driver.base import BaseBus, BaseDriver
from liquidctl.util import check_unsafe

_LOGGER = logging.getLogger(__name__)

_NUM_DEVICES = 3

_PORTS = [
    None,
    None,  # TODO: non-tuple literal (currently breaks the CLI).
    (3, 2, 1),
]

_ADDRESSES = [
    "0xf0",
    "/dev/hidraw1",
    # Adapted from <https://github.com/liquidctl/liquidctl/issues/219#issuecomment-726982682>:
    "IOService:/AppleACPIPlatformExpert/PCI0@0/AppleACPIPCI/XHC@14/XHC@14000000/HS11@14500000/"
    "USB2.0 Hub@14500000/AppleUSB20Hub@14500000/AppleUSB20HubPort@14540000/"
    "_Virtual test device@14540000/IOUSBHostInterface@0/AppleUserUSBHostHIDDevice",
]


class _Virtual(BaseDriver):
    def __init__(self, number):
        self._description = f"_Virtual test device #{number + 1}"
        self._vid = 0xFFFF
        self._pid = number
        self._release = 0x0100
        self._serial = f"1234567890-abc{number + 1}"
        self._bus = "_virtual"

        self._port = _PORTS[number]
        self._address = _ADDRESSES[number]

        _LOGGER.debug("%s instantiated: %s", self.__class__.__name__, self._description)

    def connect(self, **kwargs):
        return self

    def disconnect(self, **kwargs):
        pass

    def initialize(self, **kwargs):
        return [
            ("Initialized", True, None),
        ]

    def get_status(self, **kwargs):
        return [
            ("Healthy", True, None),
        ]

    @property
    def description(self):
        return self._description

    @property
    def vendor_id(self):
        return self._vid

    @property
    def product_id(self):
        return self._pid

    @property
    def release_number(self):
        return self._release

    @property
    def serial_number(self):
        return self._serial

    @property
    def bus(self):
        return self._bus

    @property
    def address(self):
        return self._address

    @property
    def port(self):
        return self._port


class _VirtualBus(BaseBus):
    def find_devices(self, **kwargs):
        if not check_unsafe("_virtual", error=False, **kwargs):
            return
        _LOGGER.debug("searching %s", self.__class__.__name__)
        yield from (_Virtual(i) for i in range(_NUM_DEVICES))
