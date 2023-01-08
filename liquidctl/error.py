"""liquidctl errors types.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

from typing import *


class LiquidctlError(Exception):
    """Unspecified liquidctl error.

    Unstable.
    """

    def __str__(self) -> str:
        return "unspecified liquidctl error"


class ExpectationNotMet(LiquidctlError):
    """Unstable."""


class NotSupportedByDevice(LiquidctlError):
    """Operation not supported by the device."""

    def __str__(self) -> str:
        return "operation not supported by the device"


class NotSupportedByDriver(LiquidctlError):
    """Operation not supported by the driver."""

    def __str__(self) -> str:
        return "operation not supported by the driver"


class UnsafeFeaturesNotEnabled(LiquidctlError):
    """Required unsafe features have not been enabled."""

    def __init__(self, missing_features: Iterable[str]) -> None:
        self._missing_features = missing_features

    def __str__(self) -> str:
        features = ",".join(self._missing_features)
        return f"required unsafe features have not been enabled: {features}"


class Timeout(LiquidctlError):
    """Operation timed out.

    Unstable.
    """

    def __str__(self) -> str:
        return "operation timed out"
