"""liquidctl drivers for Gigabyte RGB Fusion via ITE Tech USB Device 0x5072

RGB Fusion 2.0
--------------
Gigabyte RGB Fusion 2.0 is a lighting controller that supports 12V RGB and
5V Addressable RGB lighting effects. It is built into motherboards that contain
the RGB Fusion 2.0 logo, and supports both (a) RGB/ARGB lighting elements on
the motherboard itself, (b) RGB/ARGB elements on memory modules, and 
(c) RGB/ARGB elements connected to 12V RGB and 5V ARGB headers.

Lighting is controlled on these motherboards via an ITE Tech chip with 
product ID 0x5072 that is mapped to a USB 2 port. On the Gigabyte Z490 Vision D,
for example, the lighting controller is mapped to USB port HS12.

Driver
------

This driver implements the following features available at the hardware level:

 - initialization
 - control of lighting modes and colors
 - reporting of firmware version

The driver supports 7 color channels and a 'sync' channel. Channel names must
be specified exactly as shown (upper/lower case matters):
 - IOLED    : This is the LED next to the IO panel
 - LED1     : This is one of two 12V RGB headers
 - PCHLED   : This is the LED on the PCH chip ("Designare" on Vision D)
 - PCILED   : This is an array of LEDs behind the PCI slots on *back side* of motherboard
 - LED2     : This is second 12V RGB header
 - DLED1    : This is one of two 5V addressable RGB headers
 - DLED2    : This is second 5V addressable RGB header

Each of these channels can be controlled individually. However, channel name 'sync'
can be used to control all 7 channels at once.

The driver supports 6 color modes:
 - Off
 - static
 - pulse
 - flash
 - double-flash
 - color-cycle
 
The more elaborate Addressable RGB color/animation schemes permissable on DLED1
and DLED2 headers are not currently supported.

For color modes pulse, flash, double-flash and color-cycle, the speed of color change
is governed by the --speed parameter on command line. It may be set to:
 - slowest
 - slower
 - normal (default)
 - faster
 - fastest
 - ludicrous

The driver also supports brightness levels via --brightness argument on the command
line. Brightness is specified in percentage from 0 to 100. Example:

liquidctl set DLED1 color static FF0000 --brightness 75


Copyright (C) 2020–2020  CaseySJ
Copyright (C) 2018–2020  each contribution's author

SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver

LOGGER = logging.getLogger(__name__)

_ANIMATION_SPEEDS = {
    'slowest':   0x0,
    'slower':    0x1,
    'normal':    0x2,
    'faster':    0x3,
    'fastest':   0x4,
    'ludicrous': 0x5,
}


class CommonRGBFusionDriver(UsbHidDriver):
    """Common functions of Smart Device and Grid drivers."""

    def __init__(self, device, description, speed_channels, color_channels, **kwargs):
        """Instantiate a driver with a device handle."""
        super().__init__(device, description)
        self._speed_channels = speed_channels
        self._color_channels = color_channels

    def set_color(self, channel, mode, colors, speed='normal', brightness=-1, **kwargs):
        """Set the color mode."""
        if not self._color_channels:
            raise NotImplementedError()

        if brightness == -1:
            brightness = 100
        elif (brightness < 0 or brightness > 100):
            raise ValueError('invalid brightness, must be between 0 and 100 (percent)')

        _, _, _, _, _, _, mincolors, maxcolors = self._COLOR_MODES[mode]
        colors = [[g, r, b] for [r, g, b] in colors]
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
        
        if channel == 'sync':
            selected_channels = self._color_channels
        else:
            selected_channels = {channel: self._color_channels[channel]}
        
        self._write_colors(selected_channels, mode, colors, speed, brightness)
        self.device.release()

    def set_fixed_speed(self, channel, duty, **kwargs):
        raise NotImplementedError()

    def _write(self, data):
        padding = [0x0]*(self._WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        self.device.write(data + padding)

    def _read(self):
        data = self.device.read(self._READ_LENGTH)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in data))
        return data

    def _get_feature_report(self, report_id):
        data = self.device.get_feature_report(report_id, self._READ_LENGTH)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in data))
        return data
        
    def _send_feature_report(self, data):
        padding = [0x0]*(self._WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        self.device.send_feature_report(data + padding, self._WRITE_LENGTH)
        
    def _write_colors(self, cid, mode, colors, sval):
        raise NotImplementedError()

    def _write_fixed_duty(self, cid, duty):
        raise NotImplementedError()


class RGBFusionDriver(CommonRGBFusionDriver):
    """liquidctl driver for Gigabyte RGB Fusion 2.0 motherboards."""

    SUPPORTED_DEVICES = [
        (0x048d, 0x5702, None, 'Gigabyte RGB Fusion 2.0 (experimental)', {
            'speed_channel_count': 0,
            'color_channel_count': 7
        }),
    ]

    _READ_LENGTH = 64
    _WRITE_LENGTH = 64
    _REPORT_ID = 0xCC	# RGB Fusion Device USB Request Report ID

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

    def __init__(self, device, description, speed_channel_count, color_channel_count, **kwargs):
        """Instantiate a driver with a device handle."""
        speed_channels = {'fan{}'.format(i + 1): (1 << i)
                          for i in range(speed_channel_count)}
        color_channels = {
            'IOLED':  (0x20, 0x01),
            'LED1':   (0x21, 0x02),
            'PCHLED': (0x22, 0x04),
            'PCILED': (0x23, 0x08),
            'LED2':   (0x24, 0x10),
            'DLED1':  (0x25, 0x20),
            'DLED2':  (0x26, 0x40),
        }
        super().__init__(device, description, speed_channels, color_channels, **kwargs)

    def initialize(self, **kwargs):
        """Initialize the device.

        Detects and reports all connected fans and LED accessories, and allows
        subsequent calls to get_status.

        Returns a list of (key, value, unit) tuples.
        """
        self.device.clear_enqueued_reports()
        status = []
        # initialize
        self._write_single(0x60) # 0x60 = Initialize code
        data=self._get_feature_report(self._REPORT_ID)
        if data[0]==0xcc and data[1]==0x01:
            num_devices = data[3]
            ver_major = data[4]
            ver_minor = data[5]
            ver_build = data[6]
            ver_sub = data[7]
            index = 12  # first letter of device name in 'data'
            dev_name = ""
            while data[index] != 0 and index < self._READ_LENGTH:
                dev_name += chr(data[index])
                index += 1

            status.append(('Name', dev_name, ''))
            status.append(('Version', '{}.'.format(ver_major)+'{}.'.format(ver_minor)+
                    '{}.'.format(ver_build)+'{}'.format(ver_sub), ''))
            status.append(('LED channels', num_devices, ''))
        self.device.release()
        return status

    def _write_one_cycle(self):
        self._write_series()
        self._write_end_block()
        
    def _write_single(self, code):
        self._send_feature_report([self._REPORT_ID, code])
        
    def _write_series(self):
        """Send a series of initializer data packets"""
        for x in range(0x20,0x28):
            self._send_feature_report([self._REPORT_ID, x])
            
    def _write_end_block(self):
        self._send_feature_report([self._REPORT_ID, 0x28, 0xff])

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of (key, value, unit) tuples.
        """
        if not self._speed_channels:
            return []
        status = []
        status.append(('Lighting channels only. Nothing to report', '', ''))
        return sorted(status)

    def _write_colors(self, selected_channels, mode, colors, speed, brightness):
        # self.device.clear_enqueued_reports()
        mval, cycle, flash, num_flash, min_bright, max_bright, mincolors, maxcolors = self._COLOR_MODES[mode]

        # bright = max_bright # temp place holder; need to get brightness from CLI
        bright = min_bright + ((max_bright - min_bright) * (brightness / 100))
        LOGGER.debug('Brightness %i', bright)

        header = [self._REPORT_ID, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                  0x00, 0x00, 0x00, mval, brightness, 0x00]
        header += list(itertools.chain(*colors))
        header += [0x00, 0x00, 0x00, 0x00, 0x00]
        if mval == 1: # this modes does not support color flashing or pulsing
            header += [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        else:
            mode_speeds = self._RGB_FUSION_SPEEDS[mode]
            animation_speed = mode_speeds[speed]
            header += animation_speed
        header += [0x00, 0x00, cycle, flash, num_flash]

        for cname, (adr1, adr2) in selected_channels.items():
            header[1]=adr1
            header[2]=adr2
            # self._write_series()
            self._write_single(adr1) # this clears previous setting to allow new setting for that channel
            self._write_end_block()
            self._send_feature_report(header)
        self._write_end_block() 
        self.device.release()

