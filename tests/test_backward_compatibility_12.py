"""Test backward compatibility with liquidctl 1.2.x."""

import pytest


def test_pre13_old_driver_names():
    from liquidctl.driver.nzxt_smart_device import NzxtSmartDeviceDriver
