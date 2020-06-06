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

... to do ...
Additionally, it features two independent lighting (Addressable RGB) channels,
unlike the single channel in the original. NZXT Aer RGB 2 fans and HUE 2 lighting
accessories (HUE 2 LED strip, HUE 2 Unerglow, HUE 2 Cable Comb) can be
connected. The firmware installed on the device exposes several color presets, most
of them common to other NZXT products.

HUE 2 and HUE+ devices (including Aer RGB and Aer RGB 2 fans) are supported, but
HUE 2 components cannot be mixed with HUE+ components in the same channel. Each
lighting channel supports up to 6 accessories and a total of 40 LEDs.
...

Driver
------

This driver implements all features available at the hardware level:

 - initialization
 - control of lighting modes and colors
 - reporting of LED accessory count and type
 - reporting of firmware version

After powering on from Mechanical Off, or if there have been hardware changes,
the devices must be manually initialized by calling `initialize()`.  This will
cause all connected fans and LED accessories to be detected, and enable status
updates.  It is recommended to initialize the devices at every boot.

Copyright (C) 2020–2020  CaseySJ
Copyright (C) 2018–2020  each contribution's author

SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver

LOGGER = logging.getLogger(__name__)

_ANIMATION_SPEEDS = {
    'slowest':  0x0,
    'slower':   0x1,
    'normal':   0x2,
    'faster':   0x3,
    'fastest':  0x4,
}


class CommonRGBFusionDriver(UsbHidDriver):
    """Common functions of Smart Device and Grid drivers."""

    def __init__(self, device, description, speed_channels, color_channels, **kwargs):
        """Instantiate a driver with a device handle."""
        super().__init__(device, description)
        self._speed_channels = speed_channels
        self._color_channels = color_channels

    def set_color(self, channel, mode, colors, speed='normal', **kwargs):
        """Set the color mode."""
        if not self._color_channels:
            raise NotImplementedError()

        adr1, adr2, adr3 = self._color_channels[channel]
        LOGGER.info('channel address %s %s %s', hex(adr1), hex(adr2), hex(adr3))
        #    ' '.join(format(adr2, '02x')), ' '.join(format(adr3, '02x')))

        _, _, _, mincolors, maxcolors = self._COLOR_MODES[mode]
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
        sval = _ANIMATION_SPEEDS[speed]
        self._write_colors(adr1, adr2, adr3, mode, colors, sval)
        self.device.release()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed."""
        if not self._speed_channels:
            raise NotImplementedError()
        if channel == 'sync':
            selected_channels = self._speed_channels
        else:
            selected_channels = {channel: self._speed_channels[channel]}
        for cname, (cid, dmin, dmax) in selected_channels.items():
            duty = clamp(duty, dmin, dmax)
            LOGGER.info('setting %s duty to %i%%', cname, duty)
            self._write_fixed_duty(cid, duty)
        self.device.release()

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

    _MAX_READ_ATTEMPTS = 12
    _READ_LENGTH = 64
    _WRITE_LENGTH = 64

    _COLOR_MODES = {
        # (mode, size/variant, moving/backwards, min colors, max colors)
        'off':                              (0x00, 0x00, 0x00, 0, 0),
        'static':                           (0x01, 0x00, 0x00, 1, 1),
        'flash':                            (0x02, 0x00, 0x00, 1, 1),  
        'double flash':                     (0x03, 0x00, 0x00, 1, 1),
        'spectrum-wave':                    (0x02, 0x00, 0x00, 0, 0),
        'backwards-spectrum-wave':          (0x02, 0x00, 0x01, 0, 0),
        'marquee-3':                        (0x03, 0x00, 0x00, 1, 1),
        'marquee-4':                        (0x03, 0x01, 0x00, 1, 1),
        'marquee-5':                        (0x03, 0x02, 0x00, 1, 1),
        'marquee-6':                        (0x03, 0x03, 0x00, 1, 1),
        'backwards-marquee-3':              (0x03, 0x00, 0x01, 1, 1),
        'backwards-marquee-4':              (0x03, 0x01, 0x01, 1, 1),
        'backwards-marquee-5':              (0x03, 0x02, 0x01, 1, 1),
        'backwards-marquee-6':              (0x03, 0x03, 0x01, 1, 1),
        'covering-marquee':                 (0x04, 0x00, 0x00, 1, 8),
        'covering-backwards-marquee':       (0x04, 0x00, 0x01, 1, 8),
        'alternating-3':                    (0x05, 0x00, 0x00, 2, 2),
        'alternating-4':                    (0x05, 0x01, 0x00, 2, 2),
        'alternating-5':                    (0x05, 0x02, 0x00, 2, 2),
        'alternating-6':                    (0x05, 0x03, 0x00, 2, 2),
        'moving-alternating-3':             (0x05, 0x00, 0x10, 2, 2),   # byte4: 0x10 = moving
        'moving-alternating-4':             (0x05, 0x01, 0x10, 2, 2),   # byte4: 0x10 = moving
        'moving-alternating-5':             (0x05, 0x02, 0x10, 2, 2),   # byte4: 0x10 = moving
        'moving-alternating-6':             (0x05, 0x03, 0x10, 2, 2),   # byte4: 0x10 = moving
        'backwards-moving-alternating-3':   (0x05, 0x00, 0x11, 2, 2),   # byte4: 0x11 = moving + backwards
        'backwards-moving-alternating-4':   (0x05, 0x01, 0x11, 2, 2),   # byte4: 0x11 = moving + backwards
        'backwards-moving-alternating-5':   (0x05, 0x02, 0x11, 2, 2),   # byte4: 0x11 = moving + backwards
        'backwards-moving-alternating-6':   (0x05, 0x03, 0x11, 2, 2),   # byte4: 0x11 = moving + backwards
        'pulse':                            (0x06, 0x00, 0x00, 1, 8),
        'breathing':                        (0x07, 0x00, 0x00, 1, 8),   # colors for each step
        'super-breathing':                  (0x03, 0x19, 0x00, 1, 40),  # independent leds
        'candle':                           (0x08, 0x00, 0x00, 1, 1),
        'starry-night':                     (0x09, 0x00, 0x00, 1, 1),
        'rainbow-flow':                     (0x0b, 0x00, 0x00, 0, 0),
        'super-rainbow':                    (0x0c, 0x00, 0x00, 0, 0),
        'rainbow-pulse':                    (0x0d, 0x00, 0x00, 0, 0),
        'backwards-rainbow-flow':           (0x0b, 0x00, 0x01, 0, 0),
        'backwards-super-rainbow':          (0x0c, 0x00, 0x01, 0, 0),
        'backwards-rainbow-pulse':          (0x0d, 0x00, 0x01, 0, 0),
        'wings':                            (None, 0x00, 0x00, 1, 1),   # wings requires special handling
    }
        
    def __init__(self, device, description, speed_channel_count, color_channel_count, **kwargs):
        """Instantiate a driver with a device handle."""
        speed_channels = {'fan{}'.format(i + 1): (i, _MIN_DUTY, _MAX_DUTY)
                          for i in range(speed_channel_count)}
        color_channels = {
            'IOLED':  (0xcc, 0x20, 0x01),
            'LED1':   (0xcc, 0x21, 0x02),
            'PCHLED': (0xcc, 0x22, 0x04),
            'PCILED': (0xcc, 0x23, 0x08),
            'LED2':   (0xcc, 0x24, 0x10),
            'DLED1':  (0xcc, 0x25, 0x20),
            'DLED2':  (0xcc, 0x26, 0x40),
        }
        # color_channels['sync'] = (1 << color_channel_count) - 1
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
        data=self._get_feature_report(0xcc)
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
        # self.device.release()
        # return (status)
        """
        self._write_single(0x34) # 0x34 might refer to DIMM Module
        self._write_series()
        self._write_end_block()
        self._write_single(0x32) # 0x32 might refer to DIMM Module
        self._send_feature_report([0xcc, 0x20, 0xff]) # another termination block?
        self._write_end_block()
        self._write_series()
        self._write_end_block()
        """
        # self._write_series();
        # self._write_end_block()        

        self.device.release()
        return status
        
    def _write_single(self, code):
        self._send_feature_report([0xcc, code])
        
    def _write_series(self):
        """Send a series of initializer data packets"""
        for x in range(0x20,0x28):
            self._send_feature_report([0xcc, x])
            
    def _write_end_block(self):
        self._send_feature_report([0xcc, 0x28, 0xff])

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of (key, value, unit) tuples.
        """
        if not self._speed_channels:
            return []
        status = []

        def parse_fan_info(msg):
            rpm_offset = 24
            duty_offset = 40
            noise_offset = 56
            for i, _ in enumerate(self._speed_channels):
                if ((msg[rpm_offset] != 0x0) and (msg[rpm_offset + 1] != 0x0)):
                    status.append(('Fan {} speed'.format(i + 1), msg[rpm_offset + 1] << 8 | msg[rpm_offset], 'rpm'))
                    status.append(('Fan {} duty'.format(i + 1), msg[duty_offset + i], '%'))
                rpm_offset += 2
            status.append(('Noise level', msg[noise_offset], 'dB'))

        self.device.clear_enqueued_reports()
        self._read_until({b'\x67\x02': parse_fan_info})
        self.device.release()
        return sorted(status)


    def _write_colors(self, adr1, adr2, adr3, mode, colors, sval):
        self.device.clear_enqueued_reports()
        """
        header = [0xcc, 0x20, 0x00]
        self._write(header)        
        while True:
            data=self._read()
            byte2=data[1]
            byte3=data[2]
            if byte3 == 0xff:
                break
            header = [0xcc, byte2, 0x00]
            self._write(header)
        header = [0xcc, byte2-1, 0x00]
        self._write(header)
        data=self_.read()
        byte2=data[1]
        header = [0xcc, byte2, byte3]
        """
        # self._write_series()
        # self._write_end_block()
        # data=self._read()

        mval, mod3, mod4, mincolors, maxcolors = self._COLOR_MODES[mode]
        color_count = len(colors)
        brightness = 0x5a        
        header = [adr1, adr2, adr3, 0x00, 0x00, 0x00, 0x00, 0x00,
                  0x00, 0x00, 0x00, mval, brightness, 0x00]
        self._send_feature_report(header + list(itertools.chain(*colors)))
        # self._read()
        
        # self._write_end_block()
        # self._read()
        
        self.device.release()

    def _write_fixed_duty(self, cid, duty):
        msg = [0x62, 0x01, 0x01 << cid, 0x00, 0x00, 0x00] # fan channel passed as bitflag in last 3 bits of 3rd byte
        msg[cid + 3] = duty # duty percent in 4th, 5th, and 6th bytes for, respectively, fan1, fan2 and fan3
        self._write(msg)

