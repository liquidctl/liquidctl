import logging
from liquidctl.util import color_from_str

_LOGGER = logging.getLogger(__name__)

def _validate_leds(block):
    isValid = True

    if not block.get('mode'):
        _LOGGER.warning('led mode is a required field')
        isValid = False

    colors = block.get('colors')
    if colors:
        if not isinstance(colors, list):
            _LOGGER.warning('led colors must be a list of colors')
            isValid = False
        else:
            for c in colors:
                if not isinstance(c, str):
                    _LOGGER.warning('led color must be a list of color strings')
                    isValid = False
                else:
                    try:
                        color_from_str(c)
                    except ValueError:
                        isValid = False

    return isValid
