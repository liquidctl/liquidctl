"""liquidctl – monitor and control liquid coolers and other devices.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import sys
from liquidctl.cli import main

if __name__ == "__main__":
    sys.exit(main())
