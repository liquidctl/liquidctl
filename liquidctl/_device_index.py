"""Private helpers for generating device metadata without probing hardware.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import re
from copy import deepcopy
from dataclasses import dataclass

from liquidctl.driver.base import find_all_subclasses
from liquidctl.driver.nvidia import NVIDIA, _NvidiaI2CDriver
from liquidctl.driver.usb import BaseUsbDriver


@dataclass(frozen=True)
class UsbDeviceMatch:
    driver: str
    vendor_id: int
    product_id: int
    description: str
    constructor_kwargs: dict


@dataclass(frozen=True)
class NvidiaI2cDeviceMatch:
    driver: str
    vendor_id: int
    device_id: int
    subsystem_vendor_id: int
    subsystem_device_id: int
    i2c_addresses: tuple
    description: str


def usb_device_matches():
    """Yield declared USB match rows, keeping shared IDs and driver parameters.

    These rows are not a replacement for a driver's complete probe logic.
    No bus is instantiated and no devices are enumerated or opened.
    """
    for driver in sorted(find_all_subclasses(BaseUsbDriver), key=_driver_name):
        for vid, pid, description, kwargs in driver._MATCHES:
            yield UsbDeviceMatch(_driver_name(driver), vid, pid, description, deepcopy(kwargs))


def nvidia_i2c_device_matches():
    """Yield NVIDIA I2C matches with PCI subsystem IDs and I2C addresses.

    These drivers additionally require the NVIDIA kernel driver and an adapter
    whose name starts with ``NVIDIA i2c adapter 1 ``.  PCI identity alone does
    not establish that those requirements are satisfied.
    """
    for driver in sorted(find_all_subclasses(_NvidiaI2CDriver), key=_driver_name):
        for device_id, subsystem_device_id, description in driver._MATCHES:
            yield NvidiaI2cDeviceMatch(
                _driver_name(driver),
                NVIDIA,
                device_id,
                driver._VENDOR,
                subsystem_device_id,
                tuple(driver._ADDRESSES),
                description,
            )


def _driver_name(driver):
    return f"{driver.__module__}.{driver.__qualname__}"


def readme_support_metadata(text):
    """Read the supported-family table, its note legend and Markdown references.

    Preserve the maintainer-owned MRLVs and support notes rather than guessing
    a relationship between a family name and an identifier in a match row.
    Fail if the supported-device table changes shape instead of silently
    exporting incomplete metadata.
    """
    section = re.search(r"^## Supported devices\s*$.*?(?=^## |\Z)", text, re.M | re.S)
    if not section:
        raise ValueError("README has no supported devices section")

    rows = [line for line in section[0].splitlines() if line.startswith("|")]
    if len(rows) < 3:
        raise ValueError("README has no supported devices table")
    if [c.strip() for c in rows[0].strip().strip("|").split("|")] != [
        "Type",
        "Device family and specific documentation",
        "Notes",
        "MRLV",
    ]:
        raise ValueError("unrecognized supported devices table columns")
    separator = [c.strip() for c in rows[1].strip().strip("|").split("|")]
    if len(separator) != 4 or not all(re.fullmatch(r":?-+:?", c) for c in separator):
        raise ValueError("unrecognized supported devices table separator")

    families = []
    for row in rows[2:]:
        columns = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(columns) != 4:
            raise ValueError(f"unrecognized supported devices table row: {row}")
        kind, family, notes, mrlv = columns
        link = re.fullmatch(r"\[([^]]+)\]\(([^)]+)\)", family)
        families.append(
            {
                "type": kind,
                "name": link[1] if link else family,
                "documentation": link[2] if link else None,
                "notes_markdown": notes,
                "minimum_recommended_version": mrlv,
            }
        )

    return {
        "families": families,
        "note_legend_markdown": dict(re.findall(r"^_([A-Za-z]): (.*)_<br>$", section[0], re.M)),
        "references": dict(re.findall(r"^\[([^]]+)\]:\s*(\S+)\s*$", text, re.M)),
    }
