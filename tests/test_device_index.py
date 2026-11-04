"""Device declarations and README metadata retain their separate constraints.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import pytest

import json
import subprocess
import sys
from pathlib import Path

from liquidctl import _device_index as index
from liquidctl.driver import usb


def test_usb_matches_keep_shared_ids_and_do_not_mutate_driver_parameters(monkeypatch):
    class FamilyDriver:
        _MATCHES = [(0x1234, 0x5678, "Cooler A/B", {"channels": [1, 2]})]

    class AlternateDriver:
        _MATCHES = [(0x1234, 0x5678, "Cooler C", {"legacy": True})]

    monkeypatch.setattr(index, "find_all_subclasses", lambda _: {FamilyDriver, AlternateDriver})
    matches = list(index.usb_device_matches())
    assert len(matches) == 2
    assert {m.description for m in matches} == {"Cooler A/B", "Cooler C"}
    assert {(m.vendor_id, m.product_id) for m in matches} == {(0x1234, 0x5678)}
    family = next(m for m in matches if m.description == "Cooler A/B")
    family.constructor_kwargs["channels"].append(3)
    assert FamilyDriver._MATCHES[0][3] == {"channels": [1, 2]}


def test_nvidia_matches_keep_gpu_subsystem_and_i2c_identities_separate(monkeypatch):
    class BoardDriver:
        _VENDOR = 0x3842
        _ADDRESSES = [0x49]
        _MATCHES = [(0x1B81, 0x6276, "Graphics board")]

    monkeypatch.setattr(index, "find_all_subclasses", lambda _: {BoardDriver})
    [match] = index.nvidia_i2c_device_matches()
    assert match.vendor_id == 0x10DE
    assert match.device_id == 0x1B81
    assert match.subsystem_vendor_id == 0x3842
    assert match.subsystem_device_id == 0x6276
    assert match.i2c_addresses == (0x49,)


def test_declaration_readers_do_not_discover_devices(monkeypatch):
    def unexpected_discovery(*args, **kwargs):
        pytest.fail("metadata generation must not discover or probe devices")

    monkeypatch.setattr(usb.PyUsbBus, "find_devices", unexpected_discovery)
    monkeypatch.setattr(usb.HidapiBus, "find_devices", unexpected_discovery)
    monkeypatch.setattr(usb.usb.core, "find", unexpected_discovery)
    monkeypatch.setattr(usb.hid, "enumerate", unexpected_discovery)
    monkeypatch.setattr(index._NvidiaI2CDriver, "pre_probe", unexpected_discovery)
    assert list(index.usb_device_matches())
    assert list(index.nvidia_i2c_device_matches())


def test_readme_metadata_preserves_grouping_support_notes_and_recommended_versions():
    readme = """
## Supported devices

| Type | Device family and specific documentation | Notes | MRLV |
| :-- | :-- | :-- | :-: |
| Cooler | [Coolers A, B](docs/coolers.md) | [B][#123]p | 1.2.3 |
| Controller | New controller | | git |

_B: Broken in at least one significant way._<br>
_p: Only partially supported._<br>

[#123]: https://example.org/issues/123

## Installation

| Do not | include | this | table |
"""
    metadata = index.readme_support_metadata(readme)
    assert metadata["families"] == [
        {
            "type": "Cooler",
            "name": "Coolers A, B",
            "documentation": "docs/coolers.md",
            "notes_markdown": "[B][#123]p",
            "minimum_recommended_version": "1.2.3",
        },
        {
            "type": "Controller",
            "name": "New controller",
            "documentation": None,
            "notes_markdown": "",
            "minimum_recommended_version": "git",
        },
    ]
    assert metadata["note_legend_markdown"] == {
        "B": "Broken in at least one significant way.",
        "p": "Only partially supported.",
    }
    assert metadata["references"]["#123"] == "https://example.org/issues/123"


@pytest.mark.parametrize(
    "text",
    [
        "# No supported-device table",
        "## Supported devices\nNo table here\n",
        "## Supported devices\n| Changed | Columns |\n| -- | -- |\n| A | B |",
        "## Supported devices\n"
        "| Type | Device family and specific documentation | Notes | MRLV |\n"
        "| Cooler | First family | | 1.0 |\n| Cooler | Second family | | 2.0 |",
    ],
)
def test_readme_layout_changes_fail_explicitly(text):
    with pytest.raises(ValueError):
        index.readme_support_metadata(text)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux repository tooling")
def test_exporter_uses_its_own_checkout_and_is_deterministic(tmp_path):
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, str(root / "extra/export-device-index.py")]
    first = subprocess.check_output(command, cwd=tmp_path)
    second = subprocess.check_output(command, cwd=root)
    assert first == second
    exported = json.loads(first)
    assert exported["schema_version"] == 1
    assert exported["usb_matches"]
    assert exported["nvidia_i2c_matches"]
    assert exported["readme"]["families"]
    # A grouped match stays grouped, without inheriting a guessed family's MRLV.
    grouped = [m for m in exported["usb_matches"] if "X53" in m["description"]]
    assert grouped
    assert all("minimum_recommended_version" not in m for m in grouped)
