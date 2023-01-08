"""liquidctl driver for ASUS Aura LED USB controllers.

Supported controllers:

- ASUS Aura LED Controller: idVendor=0x0b05, idProduct=0x19af

This controller is found on ASUS ProArt Z690-Creator WiFi and other boards

Additional controllers (requires user testing and feedback):

- idVendor=0x0B05, idProduct=0x1939
- idVendor=0x0B05, idProduct=0x18F3

These controllers have not been sufficiently tested. Users are asked to test and
report issues.

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

- Aura Addressable Header Controller (for list of color mode names)
  https://gitlab.com/cneil02/aura-addressable-header-controller

- OpenRGB Project (for list of color mode names)
  https://github.com/CalcProgrammer1/OpenRGB

- @dehjomz for discovering color modes 0x10, 0x11, 0x12, 0x13

Aura LED control codes were independently obtained from USB traffic captured using
Wireshark on Windows. This Aura LED controller uses very different control codes
from previous Aura LED controllers.

Copyright CaseySJ and contributors
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

_RESET_CHANNEL_ITERATIONS = 5  # Aura Crate software uses 38

_CMD_CODE = 0xEC

_FUNCTION_CODE = {
    "direct": [_CMD_CODE, 0x40],
    "end_direct": [_CMD_CODE, 0x35, 0x00, 0x00, 0x00, 0x00],
    "end_effect": [_CMD_CODE, 0x35, 0x00, 0x00, 0x00, 0xFF],
    "start_seq1": [_CMD_CODE, 0x35],
    "start_seq2": [_CMD_CODE, 0x36, 0x00],
    "end_seq1": [_CMD_CODE, 0x35, 0x00, 0x00, 0x01, 0x05],
    "end_seq2": [_CMD_CODE, 0x3F, 0x55, 0x00, 0x00],
    "reset_seq1": [_CMD_CODE, 0x38, 0x01, 0x01],
    "reset_seq2": [_CMD_CODE, 0x38, 0x00, 0x01],
    "channel_off_pre1": [_CMD_CODE, 0x38, 0x01, 0x00],
    "channel_off_pre2": [_CMD_CODE, 0x38, 0x00, 0x00],
    "channel_off_prefix": [_CMD_CODE, 0x35, 0x01, 0x00, 0x00, 0xFF],
    "firmware": [_CMD_CODE, 0x82],
    "config": [_CMD_CODE, 0xB0],
}

# channel_type 0 designates RGB bus
# channel_type 1 designates ARGB bus
# "effect" mode channel IDs are different from "direct" mode channel IDs
_ColorChannel = namedtuple(
    "_ColorChannel", ["name", "channel_id", "direct_channel_id", "channel_type", "rgb_offset"]
)

_COLOR_CHANNELS = {
    channel.name: channel
    for channel in [
        _ColorChannel("led1", 0x01, 0x00, 0x00, 0x0),  # rgb channel
        _ColorChannel("led2", 0x02, 0x00, 0x01, 0x01),  # argb channel
        _ColorChannel("led3", 0x04, 0x01, 0x01, 0x02),  # argb channel
        _ColorChannel("led4", 0x08, 0x02, 0x01, 0x03),  # argb channel
    ]
}

_ColorMode = namedtuple("_ColorMode", ["name", "value", "takes_color"])

_COLOR_MODES = {
    mode.name: mode
    for mode in [
        _ColorMode("off", 0x00, takes_color=False),
        _ColorMode("static", 0x01, takes_color=True),
        _ColorMode("breathing", 0x02, takes_color=True),
        _ColorMode("flashing", 0x03, takes_color=True),
        _ColorMode("spectrum_cycle", 0x04, takes_color=False),
        _ColorMode("rainbow", 0x05, takes_color=False),
        _ColorMode("spectrum_cycle_breathing", 0x06, takes_color=False),
        _ColorMode("chase_fade", 0x07, takes_color=True),
        _ColorMode("spectrum_cycle_chase_fade", 0x08, takes_color=False),
        _ColorMode("chase", 0x09, takes_color=True),
        _ColorMode("spectrum_cycle_chase", 0x0A, takes_color=False),
        _ColorMode("spectrum_cycle_wave", 0x0B, takes_color=False),
        _ColorMode("chase_rainbow_pulse", 0x0C, takes_color=False),
        _ColorMode("rainbow_flicker", 0x0D, takes_color=False),
        _ColorMode("gentle_transition", 0x10, takes_color=False),
        _ColorMode("wave_propagation", 0x11, takes_color=False),
        _ColorMode("wave_propagation_pause", 0x12, takes_color=False),
        _ColorMode("red_pulse", 0x13, takes_color=False),
    ]
}


class AuraLed(UsbHidDriver):
    """
    liquidctl driver for ASUS Aura LED USB controllers.
    This driver only supports 'effect' mode, hence no speed/color channels

    Devices 0x1939 and 0x18F3 are not fully supported at this time; users are asked
    to experiment with this driver and provide feedback
    """

    _MATCHES = [
        (0x0B05, 0x19AF, "ASUS Aura LED Controller (experimental)", {}),
        (0x0B05, 0x1939, "ASUS Aura LED Controller (experimental)", {}),
        (0x0B05, 0x18F3, "ASUS Aura LED Controller (experimental)", {}),
    ]

    def initialize(self, **kwargs):
        """Initialize the device.
        Returns a list of `(property, value, unit)` tuples, containing the
        firmware version and other useful information provided by the hardware.
        """
        # Get firmware version
        self._write(_FUNCTION_CODE["firmware"])

        # Build reply string
        status = []
        data = self.device.read(_READ_LENGTH)
        if data[1] == 0x02:
            status.append(("Firmware version", "".join(map(chr, data[2:17])), ""))
        else:
            status.append("Unexpected reply for firmware", "", "")
            return status

        # This stops Direct mode if it was previously applied
        self._write(_FUNCTION_CODE["end_direct"])

        """
        Extra operations during initialization
        This is experimental and may not be necessary
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
        """Get a status report."""
        status = []
        # Get config table
        self._write(_FUNCTION_CODE["config"])
        data = self.device.read(_READ_LENGTH)
        if data[1] == 0x30:
            start_index = 4  # index of first record

            argb_channels = data[start_index + 2]
            rgb_channels = data[start_index + 3]
            status.append(("ARGB channels: " + str(argb_channels), "", ""))
            status.append((" RGB channels: " + str(rgb_channels), "", ""))

            if "debug" in kwargs and kwargs["debug"] == True:
                num = 6  # number of bytes per record
                count = 1
                while start_index + num < _READ_LENGTH:
                    status.append(
                        (
                            "Device Config: " + str(count),
                            ", ".join(
                                "0x{:02x}".format(x) for x in data[start_index : start_index + num]
                            ),
                            "",
                        )
                    )
                    start_index += num
                    count += 1
        else:
            status.append("Unexpected reply for config", "", "")
        return status

    def set_color(self, channel, mode, colors, speed="normal", **kwargs):
        """Set the color mode for a specific channel.

        `colors` should be an iterable of zero or one `[red, green, blue]`
        triples, where each red/green/blue component is a value in the range
        0–255.
        """
        colors = iter(colors)
        if _COLOR_MODES[mode].takes_color:
            try:
                r, g, b = next(colors)
                single_color = (r, g, b)
            except:
                raise ValueError(f"one color required for this mode") from None
        else:
            single_color = (0, 0, 0)

        if channel != "sync" and channel not in _COLOR_CHANNELS:
            message = "valid channels are "
            for chan in _COLOR_CHANNELS:
                message += chan + " "
            raise KeyError(message) from None
            return

        """
        This is experimental (it's an example of direct mode)
        if mode == 'off':
            self.channel_off(channel)
            self.reset_all_channels()
            return
        """

        if channel == "sync":
            selected_channels = _COLOR_CHANNELS.values()
        else:
            selected_channels = (_COLOR_CHANNELS[channel],)
        full_cmd_seq = []  # entire series of commands are added to this list

        """
        Experimental code for treating RGB channel differently from others
        if channel == "led1":
            cmd_tuple=self.construct_color_commands(channel, mode, single_color)
            self._write(cmd_tuple[0])
            self._write(cmd_tuple[1])
            self._write(_FUNCTION_CODE["end_seq2"])
            self.end_color_sequence()
            self._write(cmd_tuple[0])
            self._write(cmd_tuple[1])
            self._write(_FUNCTION_CODE["end_seq2"])
        else:
        """

        for chan in selected_channels:
            cmd_tuple = self.construct_color_commands(chan.name, mode, single_color)
            full_cmd_seq.append(cmd_tuple[0])
            full_cmd_seq.append(cmd_tuple[1])
            full_cmd_seq.append(_FUNCTION_CODE["end_seq2"])

            """
            ASUS Aura Crate sends command sequence twice, but our tests show
            that this may be redundant. Nevertheless, let's keep this code here
            in case we need to send commands twice as well
            #full_cmd_seq.append(cmd_tuple[0])
            #full_cmd_seq.append(cmd_tuple[1])
            #full_cmd_seq.append(_FUNCTION_CODE["end_seq2"])
            """

        for cmd_seq in full_cmd_seq:
            self._write(cmd_seq)
        self.end_color_sequence()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def reset_all_channels(self):
        """Reset all LED channels."""
        for i in range(_RESET_CHANNEL_ITERATIONS):
            self._write(_FUNCTION_CODE["reset_seq1"])
            self._write(_FUNCTION_CODE["reset_seq2"])

    def channel_off(self, channel):
        """
        Uses direct mode to disable a specific channel
        """
        self._write(_FUNCTION_CODE["end_effect"])

        for i in range(_RESET_CHANNEL_ITERATIONS):
            self._write(_FUNCTION_CODE["channel_off_pre1"])
            self._write(_FUNCTION_CODE["channel_off_pre2"])

        self._write(_FUNCTION_CODE["channel_off_prefix"])

        # set all LEDs to off, 20 at a time
        for i in (0, 20, 40, 60, 80, 100):
            self._write(
                _FUNCTION_CODE["direct"]
                + [_COLOR_CHANNELS[channel].direct_channel_id | (0x80 * (i == 100)), i, 20]
            )
        self.end_color_sequence()
        self._write(_FUNCTION_CODE["end_direct"])

    def construct_color_commands(self, channel, mode, single_color):
        """
        Create command strings for specified color channel
        """
        mode = _COLOR_MODES[mode]
        channel_type = _COLOR_CHANNELS[channel].channel_type  # 0=RGB, 1=ARGB
        channel_id = _COLOR_CHANNELS[channel].channel_id
        rgb_offset = _COLOR_CHANNELS[channel].rgb_offset
        data1 = _FUNCTION_CODE["start_seq1"] + [channel_type, 0x00, 0x00, mode.value]
        data2 = _FUNCTION_CODE["start_seq2"] + [channel_id, 0x00] + [0, 0, 0] * rgb_offset
        data2 += single_color
        return (data1, data2)

    def end_color_sequence(self):
        self._write(_FUNCTION_CODE["end_seq1"])
        self._write(_FUNCTION_CODE["end_seq2"])

    def _write(self, data):
        padding = [0x0] * (_WRITE_LENGTH - len(data))
        self.device.write(data + padding)

    def set_screen(self, channel, mode, value, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()
