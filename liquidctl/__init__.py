"""liquidctl – monitor and control liquid coolers and other devices.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

from liquidctl.driver import find_liquidctl_devices
from liquidctl.error import *
from liquidctl.version import __version__
