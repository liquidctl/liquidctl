"""liquidctl driver for Asus Aura LED USB controllers.

Supported controllers:

- AsusTek Aura LED Controller: idVendor=0x0b05, idProduct=0x19af

This controller is found on Asus ProArt Z690-Creator WiFi and other boards

Limitations:

This controller only supports 'effect' modes that are managed entirely by the
controller. The other mode is 'direct' that is managed by software, but this
requires the continuous transmission of command codes to control dynamic lighting
effects (i.e. all lighting modes in which colors either change or the LED 
blinks/fades/pulses).

In 'effect' mode, the software simply issues a  'fire-and-forget' command to the
controller, which subsequently manages the lighting effect on its own. There are
some limitations in 'effect' mode, as follows:

- Dynamic color modes (spectrum, rainbow, etc.) cannot be applied to individual
  color channels, but apply to all channels

- Static color modes (static) can be applied to individual color channels

- Off mode turns all channels off regardless of which channel is selected. However,
  individual channels can subsequently be enabled, while others will remain off.
  This applies only to static modes.


Acknowledgements:

Aura LED light mode names were obtained from these sources:

- Aura Addressable Header Controller
  https://gitlab.com/cneil02/aura-addressable-header-controller

- OpenRGB Project
  https://github.com/CalcProgrammer1/OpenRGB

Aura LED control codes, however, were independently obtained from USB traffic 
capture with Wireshark on Windows. This Aura LED controller uses completely 
different control codes from previous Aura LED controllers.


Copyright (C) 2022  CaseySJ
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import sys
from collections import namedtuple

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 65
_WRITE_LENGTH = 65

_RESET_CHANNEL_ITERATIONS = 38

_CMD_CODE = 0xec

_FUNCTION_CODE = {
    'direct': [_CMD_CODE, 0x40],
    'end_direct': [_CMD_CODE, 0x35, 0x00, 0x00, 0x00, 0x00],
    'end_effect': [_CMD_CODE, 0x35, 0x00, 0x00, 0x00, 0xff],
    'start_seq1': [_CMD_CODE, 0x35],
    'start_seq2': [_CMD_CODE, 0x36, 0x00],
    'end_seq1': [_CMD_CODE, 0x35, 0x00, 0x00, 0x01, 0x05],
    'end_seq2': [_CMD_CODE, 0x3f, 0x55, 0x00, 0x00],
    'reset_seq1': [_CMD_CODE, 0x38, 0x01, 0x01],
    'reset_seq2': [_CMD_CODE, 0x38, 0x00, 0x01],
    'channel_off_pre1': [_CMD_CODE, 0x38, 0x01, 0x00],
    'channel_off_pre2': [_CMD_CODE, 0x38, 0x00, 0x00],
    'channel_off_prefix': [_CMD_CODE, 0x35, 0x01, 0x00, 0x00, 0xff],
    'firmware': [_CMD_CODE, 0x82],
    'config': [_CMD_CODE, 0xb0],
}

_ColorChannel = namedtuple('_ColorChannel', ['name', 'value', 'key', 'rgb_offset'])

_COLOR_CHANNELS = {
    channel.name: channel
    for channel in [
        _ColorChannel('rgb', 0x01, 0x00, 0x0),
        _ColorChannel('argb1', 0x02, 0x01, 0x01),
        _ColorChannel('argb2', 0x04, 0x01, 0x02),
        _ColorChannel('argb3', 0x08, 0x01, 0x03),
    ]
}

_ColorMode = namedtuple('_ColorMode', ['name', 'value', 'takes_color'])

_COLOR_MODES = {
    mode.name: mode
    for mode in [
        _ColorMode('off', 0x00, takes_color=False),
        _ColorMode('static', 0x01, takes_color=True),
        _ColorMode('breathing', 0x02, takes_color=True),
        _ColorMode('flashing', 0x03, takes_color=True),
        _ColorMode('spectrum_cycle', 0x04, takes_color=False),
        _ColorMode('rainbow', 0x05, takes_color=False),
        _ColorMode('spectrum_cycle_breathing', 0x06, takes_color=False),
        _ColorMode('chase_fade', 0x07, takes_color=True),
        _ColorMode('spectrum_cycle_chase_fade', 0x08, takes_color=False),
        _ColorMode('chase', 0x09, takes_color=True),
        _ColorMode('spectrum_cycle_chase', 0x0a, takes_color=False),
        _ColorMode('spectrum_cycle_wave', 0x0b, takes_color=False),
        _ColorMode('chase_rainbow_pulse', 0x0c, takes_color=False),
        _ColorMode('rainbow_flicker', 0x0d, takes_color=False),
    ]
}


class AuraLed(UsbHidDriver):
    """liquidctl driver for Asus Aura LED USB controllers."""

    """This driver only supports 'effect' mode, hence no speed/color channels"""
    SUPPORTED_DEVICES = [
        (0x0b05, 0x19af, None, 'AsusTek Aura LED Controller', {}),
    ]

    def initialize(self, **kwargs):
        """Initialize the device.

        Returns a list of `(property, value, unit)` tuples, containing the
        firmware version and other useful information provided by the hardware.
        """

        # Get firmware version
        self._write(_FUNCTION_CODE['firmware'])
        
        status = []
        data = self.device.read(_READ_LENGTH)
        if (data[1] == 0x02):
            status.append(('Firmware version', "".join(map(chr, data[2:17])), ''))
        else:
            status.append('Unexpected reply for firmware', '', '')
            return status

        # Get config table
        self._write(_FUNCTION_CODE['config'])

        data = self.device.read(_READ_LENGTH)
        if (data[1] == 0x30):
            start_index = 4 # index of first record
            num = 6 # number of bytes per record
            count = 1
            while (start_index + num < _READ_LENGTH):
                status.append(('Device Config: '+str(count), data[start_index:start_index+num], ''))
                start_index += num
                count += 1
        else:
            status.append('Unexpected reply for config', '', '')

        # This stops Direct mode if it was previous applied
        data = _FUNCTION_CODE['end_direct']
        self._write(data)
        
        """
        Extra operations during initialization
        This is experimental and appears to not be necessary
        
        self._write([0xec, 0x31, 0x0d, 0x00]);
        self._write([0xec, 0xb1, 0x00, 0x00]);
        self.device.read(_READ_LENGTH)
            
        self._write([0xec, 0x31, 0x0e, 0x00]);
        self._write([0xec, 0xb1, 0x00, 0x00]);
        self.device.read(_READ_LENGTH)

        self._write([0xec, 0x31, 0x0f, 0x00]);
        self._write([0xec, 0xb1, 0x00, 0x00]);
        self.device.read(_READ_LENGTH)

        self._write([0xec, 0x83, 0x00, 0x00]);
        self.device.read(_READ_LENGTH)
        """
        
        return status

    def get_status(self, **kwargs):
        """Get a status report.

        """
        status = []

        # Get config table
        self._write(_FUNCTION_CODE['config'])

        data = self.device.read(_READ_LENGTH)
        if (data[1] == 0x30):
            start_index = 4 # index of first record
            num = 6 # number of bytes per record
            count = 1
            while (start_index + num < _READ_LENGTH):
                status.append(('Device Config: '+str(count), data[start_index:start_index+num], ''))
                start_index += num
                count += 1
        else:
            status.append('Unexpected reply for config', '', '')
        
        return status

    def set_color(self, channel, mode, colors, speed='normal', **kwargs):
        """Set the color mode for a specific channel.

        `colors` should be an iterable of zero or one `[red, blue, green]`
        triples, where each red/blue/green component is a value in the range
        0–255.
        """
        if not channel in _COLOR_CHANNELS:
            _LOGGER.error('channel %s not valid', channel)
            message = "valid channels are "
            for chan in _COLOR_CHANNELS:
                message += chan + ' '
            _LOGGER.error(message)
            return

        """
        This is experimental (it's an example of direct mode)
        if mode == 'off':
            self.channel_off(channel)
            self.reset_all_channels()
            return
        """
        
        if channel == 'rgb':
            data_tuple=self.construct_color_commands(channel, mode, colors)
            self._write(data_tuple[0])
            self._write(data_tuple[1])
            self._write(_FUNCTION_CODE['end_seq2'])
            self.end_color_sequence()
            self._write(data_tuple[0])
            self._write(data_tuple[1])
            self._write(_FUNCTION_CODE['end_seq2'])
        else:
            data_tuple=self.construct_color_commands(channel, mode, colors)
            self._write(data_tuple[0])
            self._write(data_tuple[1])
            self._write(_FUNCTION_CODE['end_seq2'])
            self._write(data_tuple[0])
            self._write(data_tuple[1])
        
        self.end_color_sequence()

        """
        if channel == 'sync':
            selected_channels = _COLOR_CHANNELS.values()
        else:
            selected_channels = (_COLOR_CHANNELS[channel],)
        for addr1, addr2 in selected_channels:
            data[1:3] = addr1, addr2
            self._send_feature_report(data)
        self._execute_report()
        """

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def reset_all_channels(self):
        """Reset all LED channels."""
        #for i in range(_RESET_CHANNEL_ITERATIONS):
        for i in range(5):
            self._write(_FUNCTION_CODE['reset_seq1'])
            self._write(_FUNCTION_CODE['reset_seq2'])

    def channel_off(self, channel):
        """
        Uses direct mode to disable a specific channel
        """
        self._write(_FUNCTION_CODE['end_effect'])
        for i in range(5):
            self._write(_FUNCTION_CODE['channel_off_pre1'])
            self._write(_FUNCTION_CODE['channel_off_pre2'])
        self._write(_FUNCTION_CODE['channel_off_prefix'])
        # set all LEDs to off, 20 at a time
        for i in (0, 20, 40, 60, 80, 100):
            self._write(_FUNCTION_CODE['direct'] + [_COLOR_CHANNELS[channel].value | (0x80 * (i==100)), i, 20])
        self.end_color_sequence()
        self._write(_FUNCTION_CODE['end_direct'])

    def construct_color_commands(self, channel, mode, colors):
        """
        Create command strings for specified color channel
        """
        mode = _COLOR_MODES[mode]
        colors = iter(colors)

        if mode.takes_color:
            try:
                r, g, b = next(colors)
                single_color = (r, g, b)
            except StopIteration:
                raise ValueError(f'one color required for mode={mode.name}') from None
        else:
            single_color = (0, 0, 0)
        remaining = sum(1 for _ in colors)
        if remaining:
            _LOGGER.warning('too many colors for mode=%s, dropping %d', mode.name, remaining)

        key = _COLOR_CHANNELS[channel].key
        channel_id = _COLOR_CHANNELS[channel].value
        rgb_offset = _COLOR_CHANNELS[channel].rgb_offset

        data1 = _FUNCTION_CODE['start_seq1'] + [key, 0x00, 0x00, mode.value]
        data2 = _FUNCTION_CODE['start_seq2'] + [channel_id, 0x00] + [0, 0, 0]*rgb_offset
        data2 += single_color
        return (data1, data2)

    def end_color_sequence(self):       
        self._write(_FUNCTION_CODE['end_seq1'])
        self._write(_FUNCTION_CODE['end_seq2'])

    def _write(self, data):
        padding = [0x0]*(_WRITE_LENGTH - len(data))
        self.device.write(data + padding)

