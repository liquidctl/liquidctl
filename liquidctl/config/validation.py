import logging
from liquidctl.util import color_from_str

_LOGGER = logging.getLogger(__name__)

def _validate_leds(block):
    """
    This will validate a single led channel block.
    It will print any of the errors at the `warning` level
    It will return True if it is valid and False if there are any issues.
    """
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

def _validate_fans(block):
    pass

def _validate_pump(block):
    pass


_device_validators =  {
    "aio": _validate_aio,
    "ram": _validate_ram,
    "gpu": _validate_gpu,
    "psu": _validate_psu,
    "fan": _validate_fan,
}


def _validate_psu(device):
    """
    This will validate a top level device.
    These blocks should be in the top scope of the config file.

    Each of the device validator functions is responsible for ensuring that everything
    nested under it is also valid.

    Return False if there are any issues with parsing the block, True if it is good.
    """

    isValid = True

    if device.get('pump'):
        _LOGGER.warning('psu device can not have a pump block')
        isValid = False

    if device.get('leds'):
        _LOGGER.warning('psu device can not have a leds block')
        isValid = False

    if device.get('fans'):
        isValid = isValid and _validate_fans(device.get('fans'))

    return isValid


def _validate_gpu(device):
    pass

def _validate_ram(device):

    isValid = True

    if device.get('pump'):
        _LOGGER.warning('ram device can not have a pump block')
        isValid = False

    if device.get('fans'):
        _LOGGER.warning('ram device can not have a fans block')
        isValid = False

    if device.get('leds'):
        isValid = isValid and _validate_leds(device.get('leds'))

    return isValid

def _validate_aio(device):
    pass

def _validate_fan(device):
    pass


def _validate_global(block):
    """
    This function will validate the global block of the configuration file that is not specific to any one particular device.
    Returns False if there are any issues
    """
    pass


def validate(config):
    """
    validate that all of the fields in the config file are correct
    this will also check to make sure that all of the required values are set
    This will print any errors at the warning log level

    will return True if it is valid, False otherwise
    """

    isValid = True
    devices = config.items()

    if len(devices) == 0:
        _LOGGER.warning('configuration file must have at least one element in it')
        isValid=False

    for name, device in devices:

        # special handler for global field
        if name == 'global':
            isValid = isValid and _validate_global(device)
            continue

        if not device.get('type'):
            _LOGGER.warning(f'configuration device must have a type set')
            isValid=False

        if not device.get('type') in _device_validators.keys():
            _LOGGER.warning(f'configuration device must have a type set as {_device_validators.keys()}')
            isValid=False
        else:
            validator = _device_validators.get(device.get('type'))
            isValid = isValid and validator(device)


        if not device.get('vendor'):
            _LOGGER.warning('configuration device must have a vendor set')
            isValid=False

        if not device.get('product'):
            _LOGGER.warning('configuration device must have a product set')
            isValid=False

    return isValid
