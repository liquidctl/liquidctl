"""Access to Linux HWMON data.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import logging
import sys
from pathlib import Path

_LOGGER = logging.getLogger(__name__)
_IS_LINUX = sys.platform == "linux"


class HwmonDevice:
    """Unstable API."""

    __slots__ = [
        "driver",
        "path",
    ]

    def __init__(self, driver, path):
        self.driver = driver
        self.path = path

    @property
    def name(self):
        return self.path.name

    def has_attribute(self, name):
        return (self.path / name).is_file()

    def get_string(self, name):
        value = (self.path / name).read_text().rstrip()
        _LOGGER.debug("read %s: %s", name, value)
        return value

    def read_int(self, name):
        return int(self.get_string(name))

    def write_int(self, name, value):
        (self.path / name).write_text(str(value))

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
        hwmon_devices = sys_device / "hwmon"

        if not hwmon_devices.exists():
            return None

        hwmon_paths = hwmon_devices.iterdir()
        path = next(hwmon_paths)

        if next(hwmon_paths, None):
            _LOGGER.debug("cannot pick hwmon device for %s: more than one alternative", path)
            return None

        # use resolve() to be compatible with Python < 3.9
        driver = (sys_device / "driver").resolve().name

        return HwmonDevice(driver, path)
