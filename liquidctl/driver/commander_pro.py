"""liquidctl drivers for Corsair Commander Pro devices.

Supported devices:

- Corsair Commander Pro

Copyright (C) 2020–2020  Marshall Asch and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging
import re

from enum import Enum, unique

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.pmbus import compute_pec
from liquidctl.util import clamp, fraction_of_byte, u16be_from, u16le_from, normalize_profile


LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 64
_RESPONSE_LENGTH = 16


_CMD_GET_FIRMWARE = 0x02
_CMD_GET_BOOTLOADER = 0x06
_CMD_GET_TEMP_CONFIG = 0x10
_CMD_GET_TEMP = 0x11
_CMD_GET_VOLTS = 0x12
_CMD_GET_FAN_MODES = 0x20
_CMD_GET_FAN_RPM = 0x21
_CMD_SET_FAN_DUTY = 0x23
_CMD_SET_FAN_PROFILE = 0x25
_TEMP1_MASK = 0b0001
_TEMP2_MASK = 0b0010
_TEMP3_MASK = 0b0100
_TEMP4_MASK = 0b1000


_FAN_MODE_DISCONNECTED = 0x00
_FAN_MODE_DC = 0x01
_FAN_MODE_PWM = 0x02


_PROFILE_LENGTH = 6
_CRITICAL_TEMPERATURE = 60
_MAX_FAN_RPM = 5000             # I have no idea if this is a good value or not


# FAN TYPES

# SP RGB - 100% = 1540     - 1 led
# SP RGB PRO - 100% = 1540 - 8 leds
# HD RGB - 800 - 1725      - 12 leds
# LL RGB - 600 - 1500      - 16 leds
# QL RGB - 525 - 1500      - 34 leds
# AF      - 1400
# ML RGB - 400 - 2400      - 4 leds



## old values (remove)
#_FEATURE_COOLING = 0b000
#_CMD_GET_STATUS = 0xFF
#_CMD_SET_COOLING = 0x14
#
#_FEATURE_LIGHTING = None
#_CMD_SET_LIGHTING1 = 0b100
#_CMD_SET_LIGHTING2 = 0b101
#
## cooling data starts at offset 3 and ends just before the PEC byte
#_SET_COOLING_DATA_LENGTH = _REPORT_LENGTH - 4
#_SET_COOLING_DATA_PREFIX = [0x0, 0xFF, 0x5, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
#_FAN_MODE_OFFSETS = [0x0B - 3, 0x11 - 3]
#_FAN_DUTY_OFFSETS = [offset + 5 for offset in _FAN_MODE_OFFSETS]
#_FAN_PROFILE_OFFSETS = [0x1E - 3, 0x2C - 3]
#_FAN_OFFSETS = list(zip(_FAN_MODE_OFFSETS, _FAN_DUTY_OFFSETS, _FAN_PROFILE_OFFSETS))
#_PUMP_MODE_OFFSET = 0x17 - 3
#_PROFILE_LENGTH_OFFSET = 0x1D - 3
#_PROFILE_LENGTH = 7
#_CRITICAL_TEMPERATURE = 60
#
#
#@unique
#class _FanMode(Enum):
#    CUSTOM_PROFILE = 0x0
#    CUSTOM_PROFILE_WITH_EXTERNAL_SENSOR = 0x1
#    FIXED_DUTY = 0x2
#    FIXED_RPM = 0x4
#
#    @classmethod
#    def _missing_(cls, value):
#        LOGGER.debug("falling back to FIXED_DUTY for _FanMode(%s)", value)
#        return _FanMode.FIXED_DUTY

def _prepare_profile(original):
    clamped = ((temp, clamp(duty, 0, _MAX_FAN_RPM)) for temp, duty in original)
    normal = normalize_profile(clamped, _CRITICAL_TEMPERATURE, _MAX_FAN_RPM)
    missing = _PROFILE_LENGTH - len(normal)
    if missing < 0:
        raise ValueError(f'Too many points in profile (remove {-missing})')
    if missing > 0:
        normal += missing * [(_CRITICAL_TEMPERATURE, _MAX_FAN_RPM)]
    return normal


def _quoted(*names):
    return ', '.join(map(repr, names))


class CommanderPro(UsbHidDriver):
    """Corsair Commander Pro LED and fan hub"""

    SUPPORTED_DEVICES = [
        (0x1B1C, 0x0C10, None, 'Corsair Commander Pro (experimental)',
            {'fan_count': 6, 'temp_probs': 4, 'led_channels': 2}),
    ]

    def __init__(self, device, description, fan_count, temp_probs, led_channels, **kwargs):
        super().__init__(device, description, **kwargs)
        
        # the following fields are only initialized in connect()
        self._data = None
        self._fan_names = [f'fan{i+1}' for i in range(fan_count)]



    def connect(self, **kwargs):
        """Connect to the device."""
        super().connect(**kwargs)
        ids = f'vid{self.vendor_id:04x}_pid{self.product_id:04x}'
        # must use the HID path because there is no serial number; however,
        # these can be quite long on Windows and macOS, so only take the
        # numbers, since they are likely the only parts that vary between two
        # devices of the same model
        loc = 'loc' + '_'.join(re.findall(r'\d+', self.address))
        self._data = RuntimeStorage(key_prefixes=[ids, loc])

    def initialize(self, pump_mode='balanced', **kwargs):
        """Initialize the device and get the fan modes.

        The device should be initialized every time it is powered on, including when
        the system resumes from suspending to memory.

        Returns a list of `(property, value, unit)` tuples.
        """
        
        res = self._send_command(_CMD_GET_FIRMWARE)
        fw_version = (res[1], res[2], res[3])
        
        res = self._send_command(_CMD_GET_BOOTLOADER)
        bootloader_version = (res[1], res[2])               # is it possible for there to be a third value?
        
        res = self._send_command(_CMD_GET_TEMP_CONFIG)
        
        temp1_con = res[1] == 0x01
        temp2_con = res[2] == 0x01
        temp3_con = res[3] == 0x01
        temp4_con = res[4] == 0x01

        connected_temp_sensors = temp4_con << 3 | temp3_con << 2 | temp2_con << 1 | temp1_con 
        self._data.store('temp_sensors_connected', connected_temp_sensors)

        # get the information about how the fans are connected, probably want to save this for later
        res = self._send_command(_CMD_GET_FAN_MODES)
        fanModes = res[1:7]

        self._data.store('fan1_mode', fanModes[0])
        self._data.store('fan2_mode', fanModes[1])
        self._data.store('fan3_mode', fanModes[2])
        self._data.store('fan4_mode', fanModes[3])
        self._data.store('fan5_mode', fanModes[4])
        self._data.store('fan6_mode', fanModes[5])


        return [
            ('Firmware version', '%d.%d.%d' % fw_version, ''),
            ('Bootloader version', '%d.%d' % bootloader_version, ''),
            ('Temp sensor 1', 'Connected' if temp1_con else 'Not Connected', ''),
            ('Temp sensor 2', 'Connected' if temp2_con else 'Not Connected', ''),
            ('Temp sensor 3', 'Connected' if temp3_con else 'Not Connected', ''),
            ('Temp sensor 4', 'Connected' if temp4_con else 'Not Connected', ''),
            ('Fan 1 Mode', self._get_fan_mode_description(fanModes[0]), ''),
            ('Fan 2 Mode', self._get_fan_mode_description(fanModes[1]), ''),
            ('Fan 3 Mode', self._get_fan_mode_description(fanModes[2]), ''),
            ('Fan 4 Mode', self._get_fan_mode_description(fanModes[3]), ''),
            ('Fan 5 Mode', self._get_fan_mode_description(fanModes[4]), ''),
            ('Fan 6 Mode', self._get_fan_mode_description(fanModes[5]), ''),
        ]

    def _get_fan_mode_description(self, mode):
        """This will convert the fan mode value to a descriptive name.

        """
        if mode == _FAN_MODE_DISCONNECTED:
            return 'Auto/Disconnected'
        elif mode == _FAN_MODE_DC:
            return 'DC'
        elif mode == _FAN_MODE_PWM:
            return 'PWM'
        else:
            return 'UNKNOWN'

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        connected_temp_sensors = self._data.load('temp_sensors_connected', of_type=int, default=0)

        fan_modes = [0]*6
        for i in range(6):
            fan_modes[i] = self._data.load(f'fan{i+1}_mode', of_type=int, default=0)

        # get the tempature sensor values
        temp = [0]*4
        if connected_temp_sensors & _TEMP1_MASK == _TEMP1_MASK:
            temp[0] = self._get_temp(1)

        if connected_temp_sensors & _TEMP2_MASK == _TEMP2_MASK:
            temp[1] = self._get_temp(2)

        if connected_temp_sensors & _TEMP3_MASK == _TEMP3_MASK:
            temp[2] = self._get_temp(3)

        if connected_temp_sensors & _TEMP4_MASK == _TEMP4_MASK:
            temp[3] = self._get_temp(4)

        # get the real power supply voltages
        res = self._send_command(_CMD_GET_VOLTS, [0])
        volt_12 = u16be_from(res, offset=1) / 1000

        res = self._send_command(_CMD_GET_VOLTS, [1])
        volt_5 = u16be_from(res, offset=1) / 1000

        res = self._send_command(_CMD_GET_VOLTS, [2])
        volt_3 = u16be_from(res, offset=1) / 1000

        
        # get fan RPMs of connected fans
        fanspeeds = [0]*6
        for fan_num, mode in enumerate(fan_modes):
            if mode == _FAN_MODE_DC or mode == _FAN_MODE_PWM:
                fanspeeds[fan_num] = self._get_fan_rpm(fan_num+1)

        return [
            ('Temp sensor 1', temp[0], '°C'),
            ('Temp sensor 2', temp[1], '°C'),
            ('Temp sensor 3', temp[2], '°C'),
            ('Temp sensor 4', temp[3], '°C'),
            ('12 volt rail', volt_12, 'V'),
            ('5 volt rail', volt_5, 'V'),
            ('3.3 volt rail', volt_3, 'V'),
            ('Fan 1 speed', fanspeeds[0], 'rpm'),
            ('Fan 2 speed', fanspeeds[1], 'rpm'),
            ('Fan 3 speed', fanspeeds[2], 'rpm'),
            ('Fan 4 speed', fanspeeds[3], 'rpm'),
            ('Fan 5 speed', fanspeeds[4], 'rpm'),
            ('Fan 6 speed', fanspeeds[5], 'rpm'),
        ]

    def _get_temp(self, sensor_num):
        """This will get the tempature in degrees celsius for the specified temp sensor.

        sensor number MUST be in range of 1-4
        """
        if sensor_num < 1 or sensor_num > 4:
            raise ValueError(f'sensor_num {sensor_num} invalid, must be between 1 and 4')


        res = self._send_command(_CMD_GET_TEMP, [sensor_num - 1])
        temp = u16be_from(res, offset=1) / 100

        return temp

    def _get_fan_rpm(self, fan_num):
        """This will get the rpm value of the fan.

        fan number MUST be in range of 1-6
        """
        if fan_num < 1 or fan_num > 6:
            raise ValueError(f'fan_num {fan_num} invalid, must be between 1 and 6')


        res = self._send_command(_CMD_GET_FAN_RPM, [fan_num - 1])
        speed = u16be_from(res, offset=1)

        return speed


    def _get_hw_fan_channels(self, channel):
        """This will get a list of all the fan channels that the command should be sent to
        It will look up the name of the fan channel given and return a list of the real fan number
        """
        channel = channel.lower()
        if channel == 'fan':
            return [i for i in range(len(self._fan_names))]
        elif channel in self._fan_names:
            return [self._fan_names.index(channel)]
        else:
            raise ValueError(f'Unknown channel, should be one of: {_quoted("fan", *self._fan_names)}')

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set fan or fans to a fixed speed duty.

        Valid channel values are 'fanN', where N >= 1 is the fan number, and
        'fan', to simultaneously configure all fans.  Unconfigured fan channels
        may default to 100% duty.

        Different commands for sending fixed percent (0x23) and fixed rpm (0x24)
        Probably want to use fixed percent for this untill the rpm flag is enabled.
        Can only send one fan command at a time, if fan mode is unset will need to send 6?
        messages (or 1 per enabled fan)
        """

        duty = clamp(duty, 0, 100)
        fan_channels = self._get_hw_fan_channels(channel)

        for fan in fan_channels:
            mode = self._data.load(f'fan{fan+1}_mode', of_type=int, default=0)
            if mode == _FAN_MODE_DC or mode == _FAN_MODE_PWM:
                self._send_command(_CMD_SET_FAN_DUTY,[fan, duty])


    def set_speed_profile(self, channel, profile, **kwargs):
        """Set fan or fans to follow a speed duty profile.

        Valid channel values are 'fanN', where N >= 1 is the fan number, and
        'fan', to simultaneously configure all fans.  Unconfigured fan channels
        may default to 100% duty.

        Up to six (temperature, duty) pairs can be supplied in `profile`,
        with temperatures in Celsius and duty values in percentage.  The last
        point should set the fan to 100% duty cycle, or be omitted; in the
        latter case the fan will be set to max out at 60°C.


        there are 6 points on the fan curve, temp, rpm pairs
        Send one message per fan that is being set
        """

        # send fan num, temp sensor, check to make sure it is actually enabled, and do not let the user send external sensor
        # 6 2-byte big endian temps (celsius * 100), then 6 2-byte big endian rpms 
        # need to figure out how to find out what the max rpm is for the given fan

        profile = list(profile)
        profile = _prepare_profile(profile)

        # fan_type = kwargs['fan_type'] # need to make sure this is set
        temp_sensor = kwargs.get('temp_sensor', 1) # need to make sure this is set and in range 1-4 or ext
        temp_sensor = clamp(temp_sensor, 1, 4) 

        # generate the  profile in the correct format, 6 temp, 6 speeds

        buf = bytearray(26)
        buf[1] = temp_sensor-1 # 0  # use temp sensor 1 

        for i,entry in enumerate(profile):
            temp = entry[0]*100
            rpm  = entry[1]

            # convert both values to 2 byte big endian values
            buf[2 + i*2] = temp.to_bytes(2, byteorder='big')[0]
            buf[2 + i*2 + 1] = temp.to_bytes(2, byteorder='big')[1]
            buf[2 + i*2 + 12] = rpm.to_bytes(2, byteorder='big')[0]
            buf[2 + i*2 + 12 + 1] = rpm.to_bytes(2, byteorder='big')[1]



        fan_channels = self._get_hw_fan_channels(channel)

        for fan in fan_channels:
            mode = self._data.load(f'fan{fan+1}_mode', of_type=int, default=0)
            if mode == _FAN_MODE_DC or mode == _FAN_MODE_PWM:
                buf[0] = fan
                self._send_command(_CMD_SET_FAN_PROFILE, buf)


    def set_color(self, channel, mode, colors, unsafe=None, **kwargs):
        """Set the color of each LED.

        In reality the device does not have the concept of different channels
        or modes, but this driver provides a few for convenience.  Animations
        still require successive calls to this API.

        The 'led' channel can be used to address individual LEDs, and supports
        the 'super-fixed', 'fixed' and 'off' modes.

        In 'super-fixed' mode, each color in `colors` is applied to one
        individual LED, successively.  LEDs for which no color has been
        specified default to off/solid black.  This is closest to how the
        device works.

        In 'fixed' mode, all LEDs are set to the first color taken from
        `colors`.  The `off` mode is equivalent to calling this function with
        'fixed' and a single solid black color in `colors`.

        The `colors` argument should be an iterable of one or more `[red, blue,
        green]` triples, where each red/blue/green component is a value in the
        range 0–255.

        The table bellow summarizes the available channels, modes, and their
        associated maximum number of colors for each device family.

        | Channel  | Mode        | LEDs         | Platinum | PRO XT |
        | -------- | ----------- | ------------ | -------- | ------ |
        | led      | off         | synchronized |        0 |      0 |
        | led      | fixed       | synchronized |        1 |      1 |
        | led      | super-fixed | independent  |       24 |     16 |

        Note: lighting control of PRO XT devices is experimental and requires
        the `pro_xt_lighting` constant to be supplied in the `unsafe` iterable.
        """


        # Need to find a way to determine what types of devices are connected and how many leds that they have and what channel they are on
        # maybe do this as part of initilization? (inform fan channel and num and type of LED)
        # also in initilization perhaps also say what types of fans are connected to each fan port? (optional becuase this info is saved to hardware)
        
        # 2 channels, led1 led2
        # brightness flag (percentage) - this is a seperate command that is sent
        # can set some hardware modes, and can set static colors

        # icue seems to be able to set led orders for effects, need to look into that. 


        #if 'PRO XT' in self.description and not (unsafe and 'pro_xt_lighting' in unsafe):
        #    LOGGER.warning('Lighting control of PRO XT devices is experimental and only enabled with the `pro_xt_lighting` unsafe flag')

        #channel, mode, colors = channel.lower(), mode.lower(), list(colors)
        #self._check_color_args(channel, mode, colors)
        #if mode == 'off':
        #    expanded = []
        #elif (channel, mode) == ('led', 'super-fixed'):
        #    expanded = colors[:self._led_count]
        #elif (channel, mode) == ('led', 'fixed'):
        #    expanded = list(itertools.chain(*([color] * self._led_count for color in colors[:1])))
        #else:
        #    assert False, 'assumed unreacheable'
        #

        #if self._data.load('leds_enabled', of_type=int, default=0) == 0:
        #    # These hex strings are currently magic values that work but Im not quite sure why.
        #    d1 = bytes.fromhex("0101ffffffffffffffffffffffffff7f7f7f7fff00ffffffff00ffffffff00ffffffff00ffffffff00ffffffff00ffffffffffffffffffffffffffffff")
        #    d2 = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f2021222324252627ffffffffffffffffffffffffffffffffffffffffff")
        #    d3 = bytes.fromhex("28292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4fffffffffffffffffffffffffffffffffffffffffff")

        #    # Send the magic messages to enable setting the LEDs to statuC values
        #    self._send_command(None, 0b001, data=d1)
        #    self._send_command(None, 0b010, data=d2)
        #    self._send_command(None, 0b011, data=d3)
        #    self._data.store('leds_enabled', 1)

        #data1 = bytes(itertools.chain(*((b, g, r) for r, g, b in expanded[0:20])))
        #data2 = bytes(itertools.chain(*((b, g, r) for r, g, b in expanded[20:])))
        #self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING1, data=data1)
        #self._send_command(_FEATURE_LIGHTING, _CMD_SET_LIGHTING2, data=data2)

        raise NotImplementedError('Not yet implemented')


    def _send_command(self, command, data=None):
        # self.device.write expects buf[0] to be the report number or 0 if not used
        buf = bytearray(_REPORT_LENGTH + 1)
        buf[1] = command 
        start_at = 2
        
        if data:
            buf[start_at : start_at + len(data)] = data
        
        self.device.clear_enqueued_reports()
        self.device.write(buf)
        buf = bytes(self.device.read(_RESPONSE_LENGTH))
        return buf

