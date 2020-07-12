"""liquidctl driver for Gigabyte RGB Fusion 2.0

RGB Fusion 2.0
--------------
Gigabyte RGB Fusion 2.0 is a lighting controller that supports 12V RGB and
5V Addressable RGB lighting effects. It is built into motherboards that contain
the RGB Fusion 2.0 logo, and supports both (a) RGB/ARGB lighting elements on
the motherboard itself, (b) RGB/ARGB elements on memory modules, and 
(c) RGB/ARGB elements connected to 12V RGB and 5V ARGB headers.

Lighting is controlled on these motherboards via an ITE Tech chip with 
product ID 0x5072 or 0x8297 that is mapped to a USB 2 port. On the Gigabyte Z490
Vision D, for example, the lighting controller is mapped to USB port HS12.

Driver
------

This driver implements the following features available at the hardware level:

 - initialization
 - control of lighting modes and colors
 - reporting of firmware version


Channel Names
-------------
Each lighting channel has a unique numerical address. These numerical addresses
are not consistent across various Gigabyte motherboards. As much as we would
like to use descriptive channel names, it's not currently practical to do so.
Hence, lighting channels are given generic names: led1, led2, etc.

At this time, 7 lighting channels are defined. A 'sync' channel is also provided,
which applies the specified setting to all lighting channels.

Each user may need to create a table that associates generic channel names to
specific areas or headers on their motherboard. For example, a map for the Gigabyte
Z490 Vision D might look like this:

 - led1     : This is the LED next to the IO panel
 - led2     : This is one of two 12V RGB headers
 - led3     : This is the LED on the PCH chip ("Designare" on Vision D)
 - led4     : This is an array of LEDs behind the PCI slots on *back side* of motherboard
 - led5     : This is second 12V RGB header
 - led6     : This is one of two 5V addressable RGB headers
 - led7     : This is second 5V addressable RGB header

Each of these channels can be controlled individually. However, channel name 'sync'
can be used to control all 7 channels at once.

The driver supports 6 color modes:

 - Off
 - static
 - pulse
 - flash
 - double-flash
 - color-cycle
 
The more elaborate Addressable RGB color/animation schemes permissable on dled1
and dled2 headers are not currently supported.

For color modes pulse, flash, double-flash and color-cycle, the speed of color change
is governed by the --speed parameter on command line. It may be set to:

 - slowest
 - slower
 - normal (default)
 - faster
 - fastest
 - ludicrous

Caveats
-------
On wake-from-sleep, the ITE controller will be reset and all color modes will default
to static blue. On macOS, the "sleepwatcher" utility can be installed via Homebrew
along with a script to be run on wake that will issue the necessary liquidctl 
commands to restore desired lighting effects. Similar solutions may be necessary on
Windows and Linux.

Acknowledgements
----------------
1. Thanks to Jonas Malaco for identifying the need for 'get_report' and 'set_report'
functions at the USB driver level, and assisting in their implementation.

2. Thanks to SgtSixPack for capturing USB traffic on 0x8297 and testing the driver
on Windows.


Copyright (C) 2020–2020  CaseySJ
Copyright (C) 2018–2020  each contribution's author

SPDX-License-Identifier: GPL-3.0-or-later
"""

import sys
import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver

LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64  # TODO double check, probably 65 (64 + report ID)
_REPORT_ID = 0xCC	# RGB Fusion USB Feature Report ID
_INIT_CMD = 0x60	# Command ID to initialize device

_ANIMATION_SPEEDS = {
    'slowest':   0x0,
    'slower':    0x1,
    'normal':    0x2,
    'faster':    0x3,
    'fastest':   0x4,
    'ludicrous': 0x5,
}

_COLOR_CHANNELS = {
    'led1': (0x20, 0x01),
    'led2': (0x21, 0x02),
    'led3': (0x22, 0x04),
    'led4': (0x23, 0x08),
    'led5': (0x24, 0x10),
    'led6': (0x25, 0x20),
    'led7': (0x26, 0x40),
}

_COLOR_MODES = {
    # (mode, cycle, flash/pulse, number of flashes, min bright, max bright, min colors, max colors)
    'off':                              (0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0, 0),
    'static':                           (0x01, 0x00, 0x00, 0x00, 0x0f, 0x5a, 1, 1),
    'pulse':                            (0x02, 0x00, 0x01, 0x00, 0x0f, 0x5a, 1, 1),  
    'flash':                            (0x03, 0x00, 0x01, 0x01, 0x0f, 0x64, 1, 1),
    'double-flash':                     (0x03, 0x00, 0x01, 0x02, 0x0f, 0x64, 1, 1),
    'color-cycle':                      (0x04, 0x07, 0x00, 0x00, 0x0f, 0x64, 0, 0),
}
    
_PULSE_SPEEDS = {
    'slowest':                          (0x40, 0x06, 0x40, 0x06, 0x20, 0x03),
    'slower':                           (0x78, 0x05, 0x78, 0x05, 0xbc, 0x02),
    'normal':                           (0xb0, 0x04, 0xb0, 0x04, 0xf4, 0x01),
    'faster':                           (0xe8, 0x03, 0xe8, 0x03, 0xf4, 0x01),
    'fastest':                          (0x84, 0x03, 0x84, 0x03, 0xc2, 0x01),
    'ludicrous':                        (0x20, 0x03, 0x20, 0x03, 0x90, 0x01),
}
    
_FLASH_SPEEDS = {
    'slowest':                          (0x64, 0x00, 0x64, 0x00, 0x60, 0x09),
    'slower':                           (0x64, 0x00, 0x64, 0x00, 0x90, 0x08),
    'normal':                           (0x64, 0x00, 0x64, 0x00, 0xd0, 0x07),
    'faster':                           (0x64, 0x00, 0x64, 0x00, 0x08, 0x07),
    'fastest':                          (0x64, 0x00, 0x64, 0x00, 0x40, 0x06),
    'ludicrous':                        (0x64, 0x00, 0x64, 0x00, 0x78, 0x05),
}

_DOUBLE_FLASH_SPEEDS = {
    'slowest':                          (0x64, 0x00, 0x64, 0x00, 0x28, 0x0a),
    'slower ':                          (0x64, 0x00, 0x64, 0x00, 0x60, 0x09),
    'normal':                           (0x64, 0x00, 0x64, 0x00, 0x90, 0x08),
    'faster':                           (0x64, 0x00, 0x64, 0x00, 0xd0, 0x07),
    'fastest':                          (0x64, 0x00, 0x64, 0x00, 0x08, 0x07),
    'ludicrous':                        (0x64, 0x00, 0x64, 0x00, 0x40, 0x06),
}

_COLOR_CYCLE_SPEEDS = {
    'slowest':                          (0x78, 0x05, 0xb0, 0x04, 0x00, 0x00),
    'slower':                           (0x7e, 0x04, 0x1a, 0x04, 0x00, 0x00),
    'normal':                           (0x52, 0x03, 0xee, 0x02, 0x00, 0x00),
    'faster':                           (0xf8, 0x02, 0x94, 0x02, 0x00, 0x00),
    'fastest':                          (0x26, 0x02, 0xc2, 0x01, 0x00, 0x00),
    'ludicrous':                        (0xcc, 0x01, 0x68, 0x01, 0x00, 0x00),
}
    
_RGB_FUSION_SPEEDS = {
    'pulse':                            (_PULSE_SPEEDS),
    'flash':                            (_FLASH_SPEEDS),
    'double-flash':                     (_DOUBLE_FLASH_SPEEDS),
    'color-cycle':                      (_COLOR_CYCLE_SPEEDS),    
}

class RGBFusion2Driver(UsbHidDriver):
    """liquidctl driver for Gigabyte RGB Fusion 2.0 motherboards."""

    SUPPORTED_DEVICES = [
        (0x048d, 0x5702, None, 'Gigabyte RGB Fusion 2.0 5702 Controller (experimental)', {}),
        (0x048d, 0x8297, None, 'Gigabyte RGB Fusion 2.0 8297 Controller (experimental)', {}),
    ]

    @classmethod
    def probe(cls, handle, **kwargs):
        """Probe `handle` and yield corresponding driver instances.

        These devices have multiple top-level HID usages.  On Windows and Mac
        each usage results in a different HID handle and, specifically on
        Windows, only one of them is usable.  So HidapiDevice handles matching
        other usages have to be ignored.
        """
        if (not sys.platform.startswith('linux')) and (handle.hidinfo['usage'] != _REPORT_ID):
            return
        yield from super().probe(handle, **kwargs)

    def initialize(self, **kwargs):
        """Initialize the device.

        Returns a list of `(property, value, unit)` tuples, containing the
        firmware version and other useful information provided by the hardware.
        """
        self._send_feature_report([_REPORT_ID, _INIT_CMD])
        data = self._get_feature_report(_REPORT_ID)
        self.device.release()
        assert data[0] == _REPORT_ID and data[1] == 0x01

        null = data.index(0, 12)
        dev_name = str(bytes(data[12:null]), 'ascii', errors='ignore')
        fw_version = tuple(data[4:8])
        return [
            ('Hardware name', dev_name, ''),
            ('Firmware version', '%d.%d.%d.%d' % fw_version, ''),
            ('LED channnels', data[3], '')
        ]

    def get_status(self, **kwargs):
        """Get a status report.

        Currently returns an empty list, but this behavior is not garanteed as
        in the future the device may start to report useful information.  A
        non-empty list would contain `(property, value, unit)` tuples.
        """
        return []

    def set_color(self, channel, mode, colors, speed='normal', **kwargs):
        """Set the color mode."""

        mval, cycle, flash, num_flash, min_bright, max_bright, mincolors, maxcolors = _COLOR_MODES[mode.lower()]

        colors = [[b, g, r] for [r, g, b] in colors]
        if len(colors) < mincolors:
            raise ValueError('Not enough colors for mode={}, at least {} required'
                             .format(mode, mincolors))
        elif maxcolors == 0:
            if colors:
                LOGGER.warning('too many colors for mode=%s, none needed', mode)
            colors = [[0, 0, 0]]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            LOGGER.warning('too many colors for mode=%s, dropping to %i',
                           mode, maxcolors)
            colors = colors[:maxcolors]
        
        channel = channel.lower()
        if channel == 'sync':
            selected_channels = _COLOR_CHANNELS
        else:
            selected_channels = {channel: _COLOR_CHANNELS[channel]}

        # bright = max_bright # temp place holder; need to get brightness from CLI
        brightness = 100 # hardcode this for now
        bright = int(min_bright + ((max_bright - min_bright) * (brightness / 100)))
        LOGGER.debug('Brightness %i', bright)

        header = [_REPORT_ID, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                  0x00, 0x00, 0x00, mval, bright, 0x00]
        header += list(itertools.chain(*colors))
        header += [0x00, 0x00, 0x00, 0x00, 0x00]
        if mval == 1: # this mode does not support color flashing or pulsing
            header += [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        else:
            mode_speeds = _RGB_FUSION_SPEEDS[mode.lower()]
            animation_speed = mode_speeds[speed.lower()]
            header += animation_speed
        header += [0x00, 0x00, cycle, flash, num_flash]

        for cname, (adr1, adr2) in selected_channels.items():
            header[1]=adr1
            header[2]=adr2
            # this clears previous setting to allow new setting for that channel
            self._send_feature_report([_REPORT_ID, adr1])
            self._execute_report()  # TODO might not need to clear indivudally since [1]
            self._send_feature_report(header)
        self._execute_report()  # [1] for setting a single execute is sufficient
        self.device.release()

    def _get_feature_report(self, report_id):
        """Get Feature Report from USB device. Used to query the device."""
    	
        data = self.device.get_feature_report(report_id, _READ_LENGTH)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in data))
        return data
        
    def _send_feature_report(self, data):
        """Send Feature Report to USB device. Used to command the device."""
        padding = [0x0]*(_WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        self.device.send_feature_report(data + padding)

    def _reset_all_channels(self):
        """Reset all LED channels. Each channel must be reset before it can be changed.
        This may be used in the future."""
        for x in range(0x20,0x28):
            self._send_feature_report([_REPORT_ID, x])
        self._execute_report()
            
    def _execute_report(self):
        """After sending new lighting modes to all channels, this must be called
        to trigger the change."""
        self._send_feature_report([_REPORT_ID, 0x28, 0xff])
