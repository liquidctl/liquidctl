# uses the psf/black style

import pytest

from liquidctl.driver.hwmon import HwmonDevice


@pytest.fixture
def mock_hwmon(tmp_path):
    hwmon = tmp_path / "hwmon7"
    hwmon.mkdir()

    (hwmon / "fan1_input").write_text("1499\n")

    return HwmonDevice("mock_module", hwmon)


def test_has_module(mock_hwmon):
    assert mock_hwmon.module == "mock_module"


def test_has_path(mock_hwmon):
    assert mock_hwmon.path.is_dir()


def test_has_name(mock_hwmon):
    assert mock_hwmon.name == "hwmon7"
