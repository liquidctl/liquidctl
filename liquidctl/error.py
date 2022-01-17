"""Standardized liquidctl errors.

Copyright (C) 2020–2022  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

class ExpectationNotMet(Exception):
    """Unstable."""
    pass


class NotSupportedByDevice(Exception):
    pass


class NotSupportedByDriver(Exception):
    pass


class UnsafeFeaturesNotEnabled(Exception):
    """Unstable."""
    pass
