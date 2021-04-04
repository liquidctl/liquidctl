import pytest
import os
from liquidctl.config.parse import _validate_leds

from tomlkit import parse

def load_config(name):
    dir = os.path.dirname(os.path.realpath(__file__))
    file = os.path.join(dir, 'config_files', name)

    with open(file, 'r') as f:
        read_data = f.read()
    return parse(read_data)

@pytest.fixture(scope="function")
def config(request):
    return load_config(request.param)

@pytest.fixture
def parse_test_file():
    return load_config


def test_led_block_required_fields(parse_test_file):
    ledBlock = parse_test_file('led_required_fields.toml')

    valid = _validate_leds(ledBlock)
    assert valid

def test_led_block_missing_colors_fields(parse_test_file):
    ledBlock = parse_test_file('led_missing_colors_fields.toml')

    valid = _validate_leds(ledBlock)
    assert valid

@pytest.mark.parametrize("config", [
    'led_colors_hex_list.toml',
    'led_colors_invalid_hex.toml',
    'led_colors_empty.toml',
    'led_colors_string.toml'
], indirect=['config'])
def test_led_block_invalid_colors(config):

    valid = _validate_leds(config)
    assert not valid

@pytest.mark.parametrize("config", [
    'led_colors_0x_hex_str.toml',
    'led_colors_hex_str.toml',
    'led_colors_hls_str.toml',
    'led_colors_hsv_str.toml',
    'led_colors_num_hex_str.toml',
    'led_colors_rgb_str.toml'
], indirect=['config'])
def test_led_block_valid_colors(config):

    valid = _validate_leds(config)
    assert valid






#def test_led_block_missing_mode_fields():
#    assert False
#
#def test_led_block_extra_fields():
#    assert False
