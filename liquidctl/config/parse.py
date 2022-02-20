
import logging
import os
import sys
from tomlkit import parse

_LOGGER = logging.getLogger(__name__)

def load_config_file(file):

    with open(file, 'r') as f:
        read_data = f.read()
    try:
        data = parse(read_data)
    except Exception as e:
        _LOGGER.error('failed to parse the toml file, got error: %s', e)

    return data
