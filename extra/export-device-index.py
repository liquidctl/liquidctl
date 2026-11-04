"""Export driver match rules and README support metadata as JSON (Linux tooling).

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))

    from liquidctl._device_index import (
        nvidia_i2c_device_matches,
        readme_support_metadata,
        usb_device_matches,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, default=root / "README.md")
    args = parser.parse_args()
    result = {
        "schema_version": 1,
        "usb_matches": [asdict(match) for match in usb_device_matches()],
        "nvidia_i2c_matches": [asdict(match) for match in nvidia_i2c_device_matches()],
        "readme": readme_support_metadata(args.readme.read_text(encoding="utf-8")),
    }
    if not sys.stdout.isatty() and sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
