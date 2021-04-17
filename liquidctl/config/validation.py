import logging
from liquidctl.util import color_from_str
from functools import reduce

_LOGGER = logging.getLogger(__name__)

####################################################################
#    channel validation
####################################################################

# note to self done this block
def _validate_cooling_profile_item(block):
    isValid = True

    rpm = block.get('rpm')
    duty = block.get('duty')
    temp = block.get('temp')

    if temp is not None and ( type(temp) is not int or temp < 0):
        _LOGGER.warning('temp is a required field and must be greater than 0')
        isValid = False

    num = (rmp is not None) + (duty is not None)
    if num != 1:
        _LOGGER.warning('Must specify only one of `rmp` or `duty` for the profile point')
        isValid = False

    if rpm is not None and ( type(rpm) is not int or rpm < 0):
        _LOGGER.warning('rpm is not a valid number')
        isValid = False

    if duty is not None and ( type(duty) is not int or duty < 0 or duty > 100):
        _LOGGER.warning('duty is not a valid number in the range 0-100')
        isValid = False

    return isValid

# note to self done this block
def _validate_lighting_channel(block):
    """
    This will validate a single led channel block.
    It will print any of the errors at the `warning` level
    It will return True if it is valid and False if there are any issues.
    """
    isValid = True

    if block.get('mode') is None:
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

# note to self done this block
def _validate_cooling_channel(block):
    isValid = True

    rpm = block.get('rpm')
    duty = block.get('duty')
    profile = block.get('profile')

    # count the number of the mutually exclusive sections that are present
    num = (rmp is not None) + (duty is not None) + (profile is not None)
    if num != 1:
        _LOGGER.warning('Must specify only one of `rmp`, `duty` or `profile` for the cooling channel')
        isValid = False

    if rpm is not None and ( type(rpm) is not int or rpm < 0):
        _LOGGER.warning('rpm is not a valid number')
        isValid = False

    if duty is not None and ( type(duty) is not int or duty < 0 or duty > 100):
        _LOGGER.warning('duty is not a valid number in the range 0-100')
        isValid = False

    if profile is not None and isinstance(profile, list):
        isValid = isValid and reduce((lambda v, b: v and _validate_cooling_profile_item(b)), profile)
    elif profile is not None:
        isValid = False

    return isValid

# note to self done this block
def _validate_cooling_block(block):
    isValid = True

    if not isinstance(block, list):
        _LOGGER.warning('the cooling block for the device must be a list of channels')
        return False

    for channel in block:
        isValid = isValid and _validate_cooling_channel(channel)

    return isValid

# note to self done this block
def _validate_lighting_block(block):
    isValid = True

    if not isinstance(block, list):
        _LOGGER.warning('the lighting block for the device must be a list of channels')
        return False

    for channel in block:
        isValid = isValid and _validate_lighting_channel(channel)

    return isValid

####################################################################
#    Device type validation
####################################################################

# note to self done this block
def _validate_psu(device):
    """
    This will validate a top level device.
    These blocks should be in the top scope of the config file.

    Each of the device validator functions is responsible for ensuring that everything
    nested under it is also valid.

    Return False if there are any issues with parsing the block, True if it is good.
    """
    isValid = True

    if device.get('lighting'):
        _LOGGER.warning('psu device can not have a lighting block')
        isValid = False

    if device.get('cooling'):
        isValid = isValid and _validate_cooling_block(device.get('cooling'))

    return isValid

# note to self done this block
def _validate_gpu(device):
    isValid = True

    if device.get('cooling'):
        _LOGGER.warning('gpu device can not have a cooling block')
        isValid = False

    if device.get('lighting'):
        isValid = isValid and _validate_lighting_block(device.get('lighting'))

    return isValid

# note to self done this block
def _validate_ram(device):
    isValid = True

    if device.get('cooling'):
        _LOGGER.warning('ram device can not have a cooling block')
        isValid = False

    if device.get('lighting'):
        isValid = isValid and _validate_lighting_block(device.get('lighting'))

    return isValid

# note to self done this block
def _validate_aio(device):
    isValid = True

    if device.get('cooling'):
        isValid = isValid and _validate_cooling_block(device.get('cooling'))

    if device.get('lighting'):
        isValid = isValid and _validate_lighting_block(device.get('lighting'))

    return isValid

# note to self done this block
def _validate_fan_controller(device):
    isValid = True

    if device.get('cooling'):
        isValid = isValid and _validate_cooling_block(device.get('cooling'))

    if device.get('lighting'):
        isValid = isValid and _validate_lighting_block(device.get('lighting'))

    return isValid

# note to self done this block
def _validate_led_controller(device):
    isValid = True

    if device.get('cooling'):
        _LOGGER.warning('ram device can not have a cooling block')
        isValid = False

    if device.get('lighting'):
        isValid = isValid and _validate_lighting_block(device.get('lighting'))

    return isValid

# There currently are no global level configurations but they will go here
# note to self done this block
def _validate_global(block):
    """
    This function will validate the global block of the configuration file that is not specific to any one particular device.
    Returns False if there are any issues
    """
    return True


_device_validators =  {
    "aio": _validate_aio,
    "ram": _validate_ram,
    "gpu": _validate_gpu,
    "psu": _validate_psu,
    "fan": _validate_fan_controller,
    "led": _validate_led_controller
}


def validate(config):
    """
    validate that all of the fields in the config file are correct
    this will also check to make sure that all of the required values are set
    This will print any errors at the warning log level

    will return True if it is valid, False otherwise
    """

    isValid = True

    if not config.get('version') or isinstance(config.get('version'), str):
        _LOGGER.warning('`version` is a required field and must be set to the file version number')
        isValid=False

    if config.get('global'):
            isValid = isValid and _validate_global(config.get('global'))

    devices = config.get('devices')
    if isinstance(devices, list):
        _LOGGER.warning('the `devices` block must be a list of devices')
        isValid=False

    for name, device in devices:

        if not device.get('type'):
            _LOGGER.warning(f'configuration device must have a type set')
            isValid=False

        if not device.get('vendor'):
            _LOGGER.warning('configuration device must have a vendor set')
            isValid=False

        if not device.get('product'):
            _LOGGER.warning('configuration device must have a product set')
            isValid=False


        if not device.get('type') in _device_validators.keys():
            _LOGGER.warning(f'configuration device must have a type set as {_device_validators.keys()}')
            isValid=False
        else:
            validator = _device_validators.get(device.get('type'))
            isValid = isValid and validator(device)



    return isValid
