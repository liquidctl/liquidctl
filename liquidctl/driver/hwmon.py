# uses the psf/black style

import logging
import sys
from pathlib import Path

_LOGGER = logging.getLogger(__name__)
_IS_LINUX = sys.platform == "linux"


class HwmonDevice:
    """Unstable API."""

    __slots__ = [
        "module",
        "path",
    ]

    def __init__(self, module, path):
        self.module = module
        self.path = path

    @property
    def name(self):
        return self.path.name

    @classmethod
    def from_hidraw(cls, path):
        """Find the `HwmonDevice` for `path`."""

        if not _IS_LINUX:
            return None

        if not path.startswith(b"/dev/hidraw"):
            _LOGGER.debug("cannot search hwmon device for %s: unsupported path", path)
            return None

        path = path.decode()
        name = path[5:]
        class_path = Path("/sys/class/hidraw", name)

        sys_device = class_path / "device"
        hwmon_devices = (sys_device / "hwmon").iterdir()

        hwmon_path = next(hwmon_devices)

        if next(hwmon_devices, None) is not None:
            _LOGGER.debug("cannot pick hwmon device for %s: more than one alternative", path)
            return None

        module = (sys_device / "driver" / "module").readlink().name

        return HwmonDevice(module, hwmon_path)
