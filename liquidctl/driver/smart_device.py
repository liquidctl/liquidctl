"""liquidctl drivers for NZXT Smart Device V1/V2, Grid+ V3, HUE 2 and HUE 2 Ambient.

Smart Device (V1)
-----------------

The NZXT Smart Device is a fan and LED controller that ships with the H200i,
H400i, H500i and H700i cases.

It provides three independent fan channels with standard 4-pin connectors.
Both PWM and DC control is supported, and the device automatically chooses the
appropriate mode for each channel.

Additionally, up to four chained HUE+ LED strips, or five Aer RGB fans, can be
driven from only RGB channel available.  The firmware installed on the device
exposes several color presets, most of them common to other NZXT products.

The device recognizes the type of accessory connected by measuring the
resistance between the FD and GND lines.[1][2]  In normal usage accessories
should not be mixed.

A microphone is also present onboard, for noise level optimization through CAM
and AI.  NZXT calls this feature Adaptive Noise Reduction (ANR).

[1] https://forum.level1techs.com/t/nzxt-hue-a-look-inside/104836
[2] In parallel: 10 kOhm per HUE+ strip, 16 kOhm per Aer RGB fan.

Grid+ V3
--------

The NZXT Grid+ V3 is a fan controller very similar to the Smart Device (V1).
Comparing the two, the Grid+ has more fan channels (six in total), and no
support for LEDs.

Smart Device V2
---------------

The NZXT Smart Device V2 is a newer model of the original fan and LED controller. It
ships with NZXT's cases released in mid-2019 including the H510 Elite, H510i,
H710i, and H210i.

It provides three independent fan channels with standard 4-pin connectors. Both
PWM and DC control is supported, and the device automatically chooses the appropriate
mode for each channel.

Additionally, it features two independent lighting (Addressable RGB) channels,
unlike the single channel in the original. NZXT Aer RGB 2 fans and HUE 2 lighting
accessories (HUE 2 LED strip, HUE 2 Unerglow, HUE 2 Cable Comb) can be
connected. The firmware installed on the device exposes several color presets, most
of them common to other NZXT products.

HUE 2 and HUE+ devices (including Aer RGB and Aer RGB 2 fans) are supported, but
HUE 2 components cannot be mixed with HUE+ components in the same channel. Each
lighting channel supports up to 6 accessories and a total of 40 LEDs.

A microphone is still present onboard for noise level optimization through CAM
and AI.

RGB & Fan Controller
--------------------

The NZXT RGB & Fan Controller is a retail version of the NZXT Smart Device V2.

HUE 2
-----

The NZXT HUE 2 is an LED controller from the same generation of the Smart
Device V2.

The presets and limitations of the four LED channels are the same as in the
Smart Device V2.

HUE 2 Ambient
-------------

HUE 2 Ambient is a variant of HUE 2 featuring 2 LED control channels.

Driver
------

This driver implements all features available at the hardware level:

 - initialization
 - detection of connected fans and LED strips
 - control of fan speeds per channel
 - monitoring of fan presence, control mode, speed, voltage and current
 - control of lighting modes and colors
 - reporting of LED accessory count and type
 - monitoring of noise level (from the onboard microphone)
 - reporting of firmware version

Software based features offered by CAM, like ANR, have not been implemented.

After powering on from Mechanical Off, or if there have been hardware changes,
the devices must be manually initialized by calling `initialize()`.  This will
cause all connected fans and LED accessories to be detected, and enable status
updates.  It is recommended to initialize the devices at every boot.

Copyright (C) 2018–2021  Jonas Malaco, CaseySJ and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp, Hue2Accessory, HUE2_MAX_ACCESSORIES_IN_CHANNEL

_LOGGER = logging.getLogger(__name__)

_ANIMATION_SPEEDS = {
    'slowest':  0x0,
    'slower':   0x1,
    'normal':   0x2,
    'faster':   0x3,
    'fastest':  0x4,
}

_MIN_DUTY = 0
_MAX_DUTY = 100


class _CommonSmartDeviceDriver(UsbHidDriver):
    """Common functions of Smart Device and Grid drivers."""

    def __init__(self, device, description, speed_channels, color_channels, **kwargs):
        """Instantiate a driver with a device handle."""
        super().__init__(device, description)
        self._speed_channels = speed_channels
        self._color_channels = color_channels

    def set_color(self, channel, mode, colors, speed='normal', direction='forward', **kwargs):
        """Set the color mode.

        Only supported by Smart Device V1/V2 and HUE 2 controllers.
        """

        if not self._color_channels:
            raise NotSupportedByDevice()

        channel = channel.lower()
        mode = mode.lower()
        speed = speed.lower()
        direction = direction.lower()

        if 'backwards' in mode:
            _LOGGER.warning('deprecated mode, move to direction=backwards option')
            mode = mode.replace('backwards-', '')
            direction = 'backward'

        cid = self._color_channels[channel]
        _, _, _, mincolors, maxcolors = self._COLOR_MODES[mode]
        colors = [[g, r, b] for [r, g, b] in colors]
        if len(colors) < mincolors:
            raise ValueError(f'not enough colors for mode={mode}, at least {mincolors} required')
        elif maxcolors == 0:
            if colors:
                _LOGGER.warning('too many colors for mode=%s, none needed', mode)
            colors = [[0, 0, 0]]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            _LOGGER.warning('too many colors for mode=%s, dropping to %d',
                            mode, maxcolors)
            colors = colors[:maxcolors]

        sval = _ANIMATION_SPEEDS[speed]
        self._write_colors(cid, mode, colors, sval, direction)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed."""
        if channel == 'sync':
            selected_channels = self._speed_channels
        else:
            selected_channels = {channel: self._speed_channels[channel]}
        for cname, (cid, dmin, dmax) in selected_channels.items():
            duty = clamp(duty, dmin, dmax)
            _LOGGER.info('setting %s duty to %d%%', cname, duty)
            self._write_fixed_duty(cid, duty)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not Supported by this device."""
        raise NotSupportedByDevice()

    def _write(self, data):
        padding = [0x0]*(self._WRITE_LENGTH - len(data))
        self.device.write(data + padding)

    def _write_colors(self, cid, mode, colors, sval):
        raise NotImplementedError()

    def _write_fixed_duty(self, cid, duty):
        raise NotImplementedError()


class SmartDevice(_CommonSmartDeviceDriver):
    """NZXT Smart Device (V1) or Grid+ V3."""

    SUPPORTED_DEVICES = [
        (0x1e71, 0x1714, None, 'NZXT Smart Device (V1)', {
            'speed_channel_count': 3,
            'color_channel_count': 1
        }),
        (0x1e71, 0x1711, None, 'NZXT Grid+ V3', {
            'speed_channel_count': 6,
            'color_channel_count': 0
        }),
    ]

    _READ_LENGTH = 21
    _WRITE_LENGTH = 65

    _COLOR_MODES = {
        # (byte2/mode, byte3/variant, byte4/size, min colors, max colors)
        'off':                           (0x00, 0x00, 0x00, 0, 0),
        'fixed':                         (0x00, 0x00, 0x00, 1, 1),
        'super-fixed':                   (0x00, 0x00, 0x00, 1, 40),  # independent leds
        'fading':                        (0x01, 0x00, 0x00, 1, 8),
        'spectrum-wave':                 (0x02, 0x00, 0x00, 0, 0),
        'marquee-3':                     (0x03, 0x00, 0x00, 1, 1),
        'marquee-4':                     (0x03, 0x00, 0x08, 1, 1),
        'marquee-5':                     (0x03, 0x00, 0x10, 1, 1),
        'marquee-6':                     (0x03, 0x00, 0x18, 1, 1),
        'covering-marquee':              (0x04, 0x00, 0x00, 1, 8),
        'alternating':                   (0x05, 0x00, 0x00, 2, 2),
        'moving-alternating':            (0x05, 0x08, 0x00, 2, 2),
        'pulse':                         (0x06, 0x00, 0x00, 1, 8),
        'breathing':                     (0x07, 0x00, 0x00, 1, 8),   # colors for each step
        'super-breathing':               (0x07, 0x00, 0x00, 1, 40),  # one step, independent leds
        'candle':                        (0x09, 0x00, 0x00, 1, 1),
        'wings':                         (0x0c, 0x00, 0x00, 1, 1),
        'super-wave':                    (0x0d, 0x00, 0x00, 1, 40),  # independent ring leds

        # deprecated in favor of direction=backward
        'backwards-spectrum-wave':       (0x02, 0x00, 0x00, 0, 0),
        'backwards-marquee-3':           (0x03, 0x00, 0x00, 1, 1),
        'backwards-marquee-4':           (0x03, 0x00, 0x08, 1, 1),
        'backwards-marquee-5':           (0x03, 0x00, 0x10, 1, 1),
        'backwards-marquee-6':           (0x03, 0x00, 0x18, 1, 1),
        'covering-backwards-marquee':    (0x04, 0x00, 0x00, 1, 8),
        'backwards-moving-alternating':  (0x05, 0x08, 0x00, 2, 2),
        'backwards-super-wave':          (0x0d, 0x00, 0x00, 1, 40),
    }

    def __init__(self, device, description, speed_channel_count, color_channel_count, **kwargs):
        """Instantiate a driver with a device handle."""
        speed_channels = {f'fan{i + 1}': (i, _MIN_DUTY, _MAX_DUTY)
                          for i in range(speed_channel_count)}
        color_channels = {'led': (i)
                          for i in range(color_channel_count)}
        super().__init__(device, description, speed_channels, color_channels, **kwargs)

    def initialize(self, **kwargs):
        """Initialize the device.

        Detects all connected fans and LED accessories, and allows subsequent
        calls to get_status.
        """

        self._write([0x1, 0x5c])  # initialize/detect connected devices and their type
        self._write([0x1, 0x5d])  # start reporting

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of (key, value, unit) tuples.
        """

        status = []
        noise = []
        self.device.clear_enqueued_reports()
        for i, _ in enumerate(self._speed_channels):
            msg = self.device.read(self._READ_LENGTH)
            num = (msg[15] >> 4) + 1
            state = msg[15] & 0x3
            status.append((f'Fan {num}', ['—', 'DC', 'PWM'][state], ''))
            noise.append(msg[1])
            if state:
                status.append((f'Fan {num} speed', msg[3] << 8 | msg[4], 'rpm'))
                status.append((f'Fan {num} voltage', msg[7] + msg[8]/100, 'V'))
                status.append((f'Fan {num} current', msg[10]/100, 'A'))
            if i != 0:
                continue
            fw = '{}.{}.{}'.format(msg[0xb], msg[0xc] << 8 | msg[0xd], msg[0xe])
            status.append(('Firmware version', fw, ''))
            if self._color_channels:
                lcount = msg[0x11]
                status.append(('LED accessories', lcount, ''))
                if lcount > 0:
                    ltype, lsize = [('HUE+ Strip', 10), ('Aer RGB', 8)][msg[0x10] >> 3]
                    status.append(('LED accessory type', ltype, ''))
                    status.append(('LED count (total)', lcount*lsize, ''))
        status.append(('Noise level', round(sum(noise)/len(noise)), 'dB'))
        return sorted(status)

    def _write_colors(self, cid, mode, colors, sval, direction='forward'):
        mval, mod3, mod4, _, _ = self._COLOR_MODES[mode]
        # generate steps from mode and colors: usually each color set by the user generates
        # one step, where it is specified to all leds and the device handles the animation;
        # but in super mode there is a single step and each color directly controls a led

        if direction == 'backward':
            mod3 += 0x10

        if 'super' in mode:
            steps = [list(itertools.chain(*colors))]
        else:
            steps = [color*40 for color in colors]
        for i, leds in enumerate(steps):
            seq = i << 5
            byte4 = sval | seq | mod4
            self._write([0x2, 0x4b, mval, mod3, byte4] + leds[0:57])
            self._write([0x3] + leds[57:])

    def _write_fixed_duty(self, cid, duty):
        self._write([0x2, 0x4d, cid, 0, duty])


class SmartDevice2(_CommonSmartDeviceDriver):
    """NZXT HUE 2 lighting and, optionally, fan controller."""

    SUPPORTED_DEVICES = [
        (0x1e71, 0x2006, None, 'NZXT Smart Device V2', {
            'speed_channel_count': 3,
            'color_channel_count': 2
        }),
        (0x1e71, 0x2001, None, 'NZXT HUE 2', {
            'speed_channel_count': 0,
            'color_channel_count': 4
        }),
        (0x1e71, 0x2002, None, 'NZXT HUE 2 Ambient', {
            'speed_channel_count': 0,
            'color_channel_count': 2
        }),
        (0x1e71, 0x2009, None, 'NZXT RGB & Fan Controller', {
            'speed_channel_count': 3,
            'color_channel_count': 2
        }),
    ]

    _MAX_READ_ATTEMPTS = 12
    _READ_LENGTH = 64
    _WRITE_LENGTH = 64

    _COLOR_MODES = {
        # (mode, size/variant, moving, min colors, max colors)
        'off':                              (0x00, 0x00, 0x00, 0, 0),
        'fixed':                            (0x00, 0x00, 0x00, 1, 1),
        'super-fixed':                      (0x01, 0x00, 0x00, 1, 40),  # independent leds
        'fading':                           (0x01, 0x00, 0x00, 1, 8),
        'spectrum-wave':                    (0x02, 0x00, 0x00, 0, 0),
        'marquee-3':                        (0x03, 0x00, 0x00, 1, 1),
        'marquee-4':                        (0x03, 0x01, 0x00, 1, 1),
        'marquee-5':                        (0x03, 0x02, 0x00, 1, 1),
        'marquee-6':                        (0x03, 0x03, 0x00, 1, 1),
        'covering-marquee':                 (0x04, 0x00, 0x00, 1, 8),
        'alternating-3':                    (0x05, 0x00, 0x00, 2, 2),
        'alternating-4':                    (0x05, 0x01, 0x00, 2, 2),
        'alternating-5':                    (0x05, 0x02, 0x00, 2, 2),
        'alternating-6':                    (0x05, 0x03, 0x00, 2, 2),
        'moving-alternating-3':             (0x05, 0x00, 0x10, 2, 2),   # byte4: 0x10 = moving
        'moving-alternating-4':             (0x05, 0x01, 0x10, 2, 2),   # byte4: 0x10 = moving
        'moving-alternating-5':             (0x05, 0x02, 0x10, 2, 2),   # byte4: 0x10 = moving
        'moving-alternating-6':             (0x05, 0x03, 0x10, 2, 2),   # byte4: 0x10 = moving
        'pulse':                            (0x06, 0x00, 0x00, 1, 8),
        'breathing':                        (0x07, 0x00, 0x00, 1, 8),   # colors for each step
        'super-breathing':                  (0x03, 0x19, 0x00, 1, 40),  # independent leds
        'candle':                           (0x08, 0x00, 0x00, 1, 1),
        'starry-night':                     (0x09, 0x00, 0x00, 1, 1),
        'rainbow-flow':                     (0x0b, 0x00, 0x00, 0, 0),
        'super-rainbow':                    (0x0c, 0x00, 0x00, 0, 0),
        'rainbow-pulse':                    (0x0d, 0x00, 0x00, 0, 0),
        'wings':                            (None, 0x00, 0x00, 1, 1),   # wings requires special handling

        # deprecated in favor of direction=backward
        'backwards-spectrum-wave':          (0x02, 0x00, 0x00, 0, 0),
        'backwards-marquee-3':              (0x03, 0x00, 0x00, 1, 1),
        'backwards-marquee-4':              (0x03, 0x01, 0x00, 1, 1),
        'backwards-marquee-5':              (0x03, 0x02, 0x00, 1, 1),
        'backwards-marquee-6':              (0x03, 0x03, 0x00, 1, 1),
        'covering-backwards-marquee':       (0x04, 0x00, 0x00, 1, 8),
        'backwards-moving-alternating-3':   (0x05, 0x00, 0x01, 2, 2),
        'backwards-moving-alternating-4':   (0x05, 0x01, 0x01, 2, 2),
        'backwards-moving-alternating-5':   (0x05, 0x02, 0x01, 2, 2),
        'backwards-moving-alternating-6':   (0x05, 0x03, 0x01, 2, 2),
        'backwards-rainbow-flow':           (0x0b, 0x00, 0x00, 0, 0),
        'backwards-super-rainbow':          (0x0c, 0x00, 0x00, 0, 0),
        'backwards-rainbow-pulse':          (0x0d, 0x00, 0x00, 0, 0),
    }

    def __init__(self, device, description, speed_channel_count, color_channel_count, **kwargs):
        """Instantiate a driver with a device handle."""
        speed_channels = {f'fan{i + 1}': (i, _MIN_DUTY, _MAX_DUTY)
                          for i in range(speed_channel_count)}
        color_channels = {f'led{i + 1}': (1 << i)
                          for i in range(color_channel_count)}
        color_channels['sync'] = (1 << color_channel_count) - 1
        super().__init__(device, description, speed_channels, color_channels, **kwargs)

    def initialize(self, **kwargs):
        """Initialize the device.

        Detects and reports all connected fans and LED accessories, and allows
        subsequent calls to get_status.

        Returns a list of (key, value, unit) tuples.
        """

        self.device.clear_enqueued_reports()
        # initialize
        update_interval = (lambda secs: 1 + round((secs - .5) / .25))(.5)  # see issue #128
        self._write([0x60, 0x02, 0x01, 0xe8, update_interval, 0x01, 0xe8, update_interval])
        self._write([0x60, 0x03])
        # request static infos
        self._write([0x10, 0x01])  # firmware info
        self._write([0x20, 0x03])  # lighting info
        status = []

        def parse_firm_info(msg):
            fw = f'{msg[0x11]}.{msg[0x12]}.{msg[0x13]}'
            status.append(('Firmware version', fw, ''))

        def parse_led_info(msg):
            channel_count = msg[14]
            offset = 15  # offset of first channel/first accessory
            for c in range(channel_count):
                for a in range(HUE2_MAX_ACCESSORIES_IN_CHANNEL):
                    accessory_id = msg[offset + c * HUE2_MAX_ACCESSORIES_IN_CHANNEL + a]
                    if accessory_id == 0:
                        break
                    status.append((f'LED {c + 1} accessory {a + 1}',
                                   Hue2Accessory(accessory_id), ''))

        self._read_until({b'\x11\x01': parse_firm_info, b'\x21\x03': parse_led_info})
        return sorted(status)

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
                    status.append((f'Fan {i + 1} speed', msg[rpm_offset + 1] << 8 | msg[rpm_offset], 'rpm'))
                    status.append((f'Fan {i + 1} duty', msg[duty_offset + i], '%'))
                rpm_offset += 2
            status.append(('Noise level', msg[noise_offset], 'dB'))

        self.device.clear_enqueued_reports()
        self._read_until({b'\x67\x02': parse_fan_info})
        return sorted(status)

    def _read_until(self, parsers):
        for _ in range(self._MAX_READ_ATTEMPTS):
            msg = self.device.read(self._READ_LENGTH)
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                func(msg)
            if not parsers:
                return
        assert False, f'missing messages (attempts={self._MAX_READ_ATTEMPTS}, missing={len(parsers)})'

    def _write_colors(self, cid, mode, colors, sval, direction='forward',):
        mval, mod3, movingFlag, mincolors, maxcolors = self._COLOR_MODES[mode]

        color_count = len(colors)
        if maxcolors == 40:
            led_padding = [0x00, 0x00, 0x00]*(maxcolors - color_count)  # turn off remaining LEDs
            leds = list(itertools.chain(*colors)) + led_padding
            self._write([0x22, 0x10, cid, 0x00] + leds[0:60])  # send first 20 colors to device (3 bytes per color)
            self._write([0x22, 0x11, cid, 0x00] + leds[60:])  # send remaining colors to device
            self._write([0x22, 0xa0, cid, 0x00, mval, mod3, 0x00, 0x00, 0x00,
                         0x00, 0x64, 0x00, 0x32, 0x00, 0x00, 0x01])
        elif mode == 'wings':  # wings requires special handling
            for [g, r, b] in colors:
                self._write([0x22, 0x10, cid])  # clear out all independent LEDs
                self._write([0x22, 0x11, cid])  # clear out all independent LEDs
                color_lists = [] * 3
                color_lists[0] = [g, r, b] * 8
                color_lists[1] = [int(x // 2.5) for x in color_lists[0]]
                color_lists[2] = [int(x // 4) for x in color_lists[1]]
                for i in range(8):   # send color scheme first, before enabling wings mode
                    mod = 0x05 if i in [3, 7] else 0x01
                    msg = ([0x22, 0x20, cid, i, 0x04, 0x39, 0x00, mod,
                            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06,
                            0x05, 0x85, 0x05, 0x85, 0x05, 0x85, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00])
                    self._write(msg + color_lists[i % 4])
                self._write([0x22, 0x03, cid, 0x08])   # this actually enables wings mode
        else:
            byte7 = movingFlag  # sets 'moving' flag for moving alternating modes
            byte8 = direction == 'backward'  # sets 'backwards' flag
            byte9 = mod3 if mval == 0x03 else color_count  # specifies 'marquee' LED size
            byte10 = mod3 if mval == 0x05 else 0x00  # specifies LED size for 'alternating' modes
            header = [0x28, 0x03, cid, 0x00, mval, sval, byte7, byte8, byte9, byte10]
            self._write(header + list(itertools.chain(*colors)))

    def _write_fixed_duty(self, cid, duty):
        msg = [0x62, 0x01, 0x01 << cid, 0x00, 0x00, 0x00]  # fan channel passed as bitflag in last 3 bits of 3rd byte
        msg[cid + 3] = duty  # duty percent in 4th, 5th, and 6th bytes for, respectively, fan1, fan2 and fan3
        self._write(msg)


# backwards compatibility
NzxtSmartDeviceDriver = SmartDevice
SmartDeviceDriver = SmartDevice
SmartDeviceV2Driver = SmartDevice2
