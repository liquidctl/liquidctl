"""Test backward compatibility with liquidctl 1.8.x."""

# uses the psf/black style

import pytest


def test_version_version_dunder_still_imports(caplog):
    from liquidctl.version import __version__

    assert type(__version__) is str


def test_pre19_driver_names_still_import():
    from liquidctl.driver.asetek_pro import CorsairAsetekProDriver
