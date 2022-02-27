# uses the psf/black style

import pytest

from liquidctl.driver.hwmon import HwmonDevice


@pytest.fixture
def mock_hwmon(tmp_path):
    hwmon = tmp_path / "hwmon7"
    hwmon.mkdir()

    (hwmon / "fan1_input").write_text("1499\n")
    (hwmon / "fan1_label").write_text("Pump Speed\n")

    return HwmonDevice("mock_module", hwmon)


def test_has_module(mock_hwmon):
    assert mock_hwmon.module == "mock_module"


def test_has_path(mock_hwmon):
    assert mock_hwmon.path.is_dir()


def test_has_name(mock_hwmon):
    assert mock_hwmon.name == "hwmon7"


def test_checks_existing_attribute(mock_hwmon):
    assert mock_hwmon.has_attribute("fan1_input")


def test_checks_non_existing_attribute(mock_hwmon):
    assert not mock_hwmon.has_attribute("bubble1_input")


def test_gets_string(mock_hwmon):
    assert mock_hwmon.get_string("fan1_label") == "Pump Speed"


def test_gets_int(mock_hwmon):
    assert mock_hwmon.get_int("fan1_input") == 1499
