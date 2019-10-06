"""USB driver for the NZXT Smart Device and Grid+ V3.


Smart Device
------------

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
[2] In parallel: 10 kOhm per Hue+ strip, 16 kOhm per Aer RGB fan.


Grid+ V3
--------

The NZXT Grid+ V3 is a fan controller very similar to the Smart Device.
Comparing the two, the Grid+ has more fan channels (six in total), and no
support for LEDs.


Smart Device V2  (added by CaseySJ)
---------------

The NZXT Smart Device V2 is a newer model of the original fan and LED controller. It
ships with NZXT's cases released in mid-2019 including the H510 Elite, H510i,
H710i, and H210i.

It provides three independent fan channels with standard 4-pin connectors. Both
PWM and DC control is supported, and the device automatically chooses the appropriate
mode for each channel.

Additionally, it features two independent daisy chain capable lighting (Addressable
RGB) channels, unlike the single channel in the original. NZXT Aer RGB 2 fans and 
HUE 2 lighting devices (HUE 2 LED strip, HUE 2 Unerglow, HUE 2 Cable Comb) can be
connected. The firmware installed on the device exposes several color presets, most
of them common to other NZXT products.

A microphone is also present onboard, for noise level optimization through CAM
and AI. NZXT calls this feature Adaptive Noise Reduction (ANR).

When invoking the liquidctl command line, fan channels are specified as:
fan1, fan2, fan3

When invoking the liquidctl command line, lighting channels are specified as:
sync1, sync2

*** IMPORTANT INFORMATION ***

* Always call "liquidctl initialize" first on a cold start of the operating system.
* If you have multiple compatible devices, use "-d" to specify device index (type "liquidctl list"
  to show list of compatible devices).
* It supports "set <channel> speed" as a duty percentage from 0 to 100.

  Example 1: Set fan2 speed to 45%
     liquidctl set fan1 speed 45


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


Copyright (C) 2018  Jonas Malaco
Copyright (C) 2018  each contribution's author

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver


LOGGER = logging.getLogger(__name__)

_COLOR_MODES = {
    # (byte2/mode, byte3/variant, byte4/size, v2modeflag, min colors, max colors)
    # v2modeflag is for NZXT SmartDevice V2 only
    'off':                           (0x00, 0x00, 0x00, 0x00, 0, 0),
    'fixed':                         (0x00, 0x00, 0x00, 0x00, 1, 1),
    'super-fixed':                   (0x00, 0x00, 0x00, 0x00, 1, 40),  # independent leds
    'fading':                        (0x01, 0x00, 0x00, 0x00, 1, 8),
    'spectrum-wave':                 (0x02, 0x00, 0x00, 0x00, 0, 0),
    'backwards-spectrum-wave':       (0x02, 0x10, 0x00, 0x01, 0, 0),
    'marquee-3':                     (0x03, 0x00, 0x00, 0x00, 1, 1),
    'marquee-4':                     (0x03, 0x00, 0x08, 0x00, 1, 1),
    'marquee-5':                     (0x03, 0x00, 0x10, 0x00, 1, 1),
    'marquee-6':                     (0x03, 0x00, 0x18, 0x00, 1, 1),
    'backwards-marquee-3':           (0x03, 0x10, 0x00, 0x01, 1, 1),
    'backwards-marquee-4':           (0x03, 0x10, 0x08, 0x01, 1, 1),
    'backwards-marquee-5':           (0x03, 0x10, 0x10, 0x01, 1, 1),
    'backwards-marquee-6':           (0x03, 0x10, 0x18, 0x01, 1, 1),
    'covering-marquee':              (0x04, 0x00, 0x00, 0x00, 1, 8),
    'covering-backwards-marquee':    (0x04, 0x10, 0x00, 0x01, 1, 8),
    'alternating':                   (0x05, 0x00, 0x00, 0x00, 2, 2),
    'moving-alternating':            (0x05, 0x08, 0x00, 0x01, 2, 2),
    'backwards-moving-alternating':  (0x05, 0x18, 0x00, 0x01, 2, 2),
    'pulse':                         (0x06, 0x00, 0x00, 0x00, 1, 8),
    'breathing':                     (0x07, 0x00, 0x00, 0x00, 1, 8),   # colors for each step
    'super-breathing':               (0x07, 0x00, 0x00, 0x00, 1, 40),  # one step, independent leds
    'candle':                        (0x09, 0x00, 0x00, 0x00, 1, 1),
    'wings':                         (0x0c, 0x00, 0x00, 0x00, 1, 1),
    'super-wave':                    (0x0d, 0x00, 0x00, 0x00, 1, 40),  # independent ring leds
    'backwards-super-wave':          (0x0d, 0x10, 0x00, 0x01, 1, 40),  # independent ring leds
}
_ANIMATION_SPEEDS = {
    'slowest':  0x0,
    'slower':   0x1,
    'normal':   0x2,
    'faster':   0x3,
    'fastest':  0x4,
}
_MIN_DUTY = 0
_MAX_DUTY = 100
_READ_ENDPOINT = 0x81
_READ_LENGTH = 21
_READ_LENGTH_V2 = 60     # for Smart Device V2
_WRITE_ENDPOINT = 0x1
_WRITE_LENGTH = 65

class NzxtSmartDeviceDriver(UsbHidDriver):
    """USB driver for the NZXT Smart Device and Grid+ V3."""

    DEVICE_SMARTDEV_V1 = 'Smart Device V1'
    DEVICE_GRID_V3  = 'Grid V3'
    DEVICE_SMARTDEV_V2 = 'Smart Device V2'

    SUPPORTED_DEVICES = [
        (0x1e71, 0x1714, None, 'NZXT Smart Device', {
            'speed_channel_count': 3,
            'color_channel_count': 1,
            'device_type': DEVICE_SMARTDEV_V1
        }),
        (0x1e71, 0x1711, None, 'NZXT Grid+ V3 (experimental)', {
            'speed_channel_count': 6,
            'color_channel_count': 0,
            'device_type': DEVICE_GRID_V3
        }),
        (0x1e71, 0x2006, None, 'NZXT Smart Device V2 (experimental)', {
            'speed_channel_count': 3,
            'color_channel_count': 2,
            'device_type': DEVICE_SMARTDEV_V2
        }),
    ]

    def __init__(self, device, description, speed_channel_count, color_channel_count, device_type=DEVICE_SMARTDEV_V1,  **kwargs):
        """Instantiate a driver with a device handle."""
        super().__init__(device, description)
        self._speed_channels = {'fan{}'.format(i + 1): (i, _MIN_DUTY, _MAX_DUTY)
                                for i in range(speed_channel_count)}
        self._color_channels = {'sync{}'.format(i + 1): (i)
                                for i in range(color_channel_count)}
        self.device_type = device_type

    def initialize(self, **kwargs):
        """Initialize the device.

        Detects all connected fans and LED accessories, and allows subsequent
        calls to get_status.
        """
        if self.device_type == self.DEVICE_SMARTDEV_V2:
            self._write([0x60, 0x02, 0x01, 0xE8, 0x03, 0x01, 0xE8, 0x03])
        else:
            self._write([0x1, 0x5c])  # initialize/detect connected devices and their type
            self._write([0x1, 0x5d])  # start reporting
        self.device.release()

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of (key, value, unit) tuples.
        """
        status = []
        noise = []
        
        if self.device_type == self.DEVICE_SMARTDEV_V2:
            numValidRepliesReceived = 0
            msg1101Reply = False
            msg2103Reply = False
            msg6702Reply = False
            msg6704Reply = False
            # Get configuration information from device
            wmsg = [0x10, 0x01, 0x00, 0x00, 0x00, 0x00]
            LOGGER.info('Issuing command 0x10 0x01 to get firmware info')
            self._write(wmsg)
            wmsg = [0x20, 0x03, 0x00, 0x00, 0x00, 0x00]
            LOGGER.info('Issuing command 0x20 0x03 to get lighting info')
            self._write(wmsg)
            #wmsg = [0x60, 0x03, 0x00, 0x00, 0x00, 0x00]
            #LOGGER.info('Issuing command 0x20 0x03 to get lighting info')
            #self._write(wmsg)
            # After issuing the above 2 commands, we will get a series of replies that
            # will include everything we want to extract and display to the user.
            # It may take 10 or 12 reply messages before we get all of the expected replies.
            for x in range(12):     # we may not get reply right away, so try up to 12 times
                if numValidRepliesReceived == 4:
                    break   
                msg = self.device.read(_READ_LENGTH_V2)
                LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
                if msg1101Reply == False and msg[0] == 0x11 and msg[1] == 0x01:  # the correct reply must start with 0x11, 0x01
                    fw = '{}.{}.{}'.format(msg[0x11], msg[0x12], msg[0x13])
                    status.append(('Firmware:', fw, ''))
                    numValidRepliesReceived += 1 
                    msg1101Reply = True
                    continue
                if msg2103Reply == False and msg[0] == 0x21 and msg[1] == 0x03:  # the correct reply must start with 0x21, 0x03
                    ledStripCount = 0
                    ledUnderglowCount = 0
                    ledCableCombCount = 0
                    ledAerFan120Count = 0
                    ledAerFan140Count = 0
                    for ledIter in range(15):
                        ledCode = msg[0x0f + ledIter]
                        if ledCode == 0x04:
                            ledStripCount += 1
                            ledName = '  LED Strip #{}'.format(ledStripCount)
                        elif ledCode == 0x08:
                            ledCableCombCount += 1
                            ledName = ' Cable Comb #{}'.format(ledCableCombCount)
                        elif ledCode == 0x0a:
                            ledUnderglowCount += 1
                            ledName = '  Underglow #{}'.format(ledUnderglowCount)
                        elif ledCode == 0x0b:
                            ledAerFan120Count += 1
                            ledName = 'AER Fan 120 #{}'.format(ledAerFan120Count)
                        elif ledCode == 0x0c:
                            ledAerFan140Count += 1
                            ledName = 'AER Fan 140 #{}'.format(ledAerFan140Count)
                        if ledCode != 0:
                            status.append(('    HUE2:', ledName, ''))
                    numValidRepliesReceived += 1
                    msg2103Reply = True
                    continue
                if msg6702Reply == False and msg[0] == 0x67 and msg[1] == 0x02:
                    rpm_offset = 24
                    duty_offset = 40
                    noise_offset = 56
                    for i, _ in enumerate(self._speed_channels):
                        # LOGGER.debug('Iteration {}'.format(i))
                        if ((msg[rpm_offset] != 0x0) and (msg[rpm_offset+1] != 0x0)): 
                            status.append(('   Speed: Fan {}'.format(i+1), msg[rpm_offset+1] << 8 | msg[rpm_offset], 'rpm'))
                            status.append(('    Duty: Fan {}'.format(i+1), msg[duty_offset+i], '%'))
                        # else:
                            # status.append(('Speed: Fan {}'.format(i+1), 'not', 'connected'))
                        rpm_offset += 2
                    status.append(('   Noise:', msg[noise_offset], 'dB'))
                    numValidRepliesReceived += 1    
                    msg6702Reply = True 
                    continue            
                if msg6704Reply == False and msg[0] == 0x67 and msg[1] == 0x04:
                    #status.append((' Unknown:', 'status', 'pending'))
                    numValidRepliesReceived += 1
                    msg6704Reply = True
                    continue
            self.device.release()
            return status
        else:        
            for i, _ in enumerate(self._speed_channels):
                msg = self.device.read(_READ_LENGTH)
                LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
                num = (msg[15] >> 4) + 1
                state = msg[15] & 0x3
                status.append(('Fan {}'.format(num), ['—', 'DC', 'PWM'][state], ''))
                noise.append(msg[1])
                if state:
                    status.append(('Fan {} speed'.format(num), msg[3] << 8 | msg[4], 'rpm'))
                    status.append(('Fan {} voltage'.format(num), msg[7] + msg[8]/100, 'V'))
                    status.append(('Fan {} current'.format(num), msg[10]/100, 'A'))
                if i != 0:
                    continue
                fw = '{}.{}.{}'.format(msg[0xb], msg[0xc] << 8 | msg[0xd], msg[0xe])
                status.append(('Firmware version', fw, ''))
                if self._color_channels:
                    lcount = msg[0x11]
                    status.append(('LED accessories', lcount, ''))
                    if lcount > 0:
                        ltype, lsize = [('Hue+ Strip', 10), ('Aer RGB', 8)][msg[0x10] >> 3]
                        status.append(('LED accessory type', ltype, ''))
                        status.append(('LED count (total)', lcount*lsize, ''))
                status.append(('Noise level', round(sum(noise)/len(noise)), 'dB'))
        self.device.release()
        return sorted(status)

    def set_color(self, channel, mode, colors, speed='normal', **kwargs):
        """Set the color mode.

        Only available for the Smart Device.
        """
        if not self._color_channels:
            raise NotImplementedError()
        selected_channels = { channel: self._color_channels[channel] }
        for cname, (cid) in selected_channels.items():
            mval, mod3, mod4, v2modeflag, mincolors, maxcolors = _COLOR_MODES[mode]
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
            # generate steps from mode and colors: usually each color set by the user generates
            # one step, where it is specified to all leds and the device handles the animation;
            # but in super mode there is a single step and each color directly controls a led
            if 'super' in mode:
                steps = [list(itertools.chain(*colors))]
            else:
                if self.device_type == self.DEVICE_SMARTDEV_V2:
                    steps = [color for color in colors]
                else:
                    steps = [color*40 for color in colors]
            sval = _ANIMATION_SPEEDS[speed]
            if self.device_type == self.DEVICE_SMARTDEV_V2:
                numColors = len(steps)
                wmsg = [0x28, 0x03, cid+1, [0x01, 0x20][cid], mval, sval, 0x0, v2modeflag, numColors, 0x0]
                for i, leds in enumerate(steps):
                    wmsg += (leds[0:3])
                #LOGGER.debug('write %s', ' '.join(format(i, '02x') for i in wmsg))
                self._write(wmsg)
            else:
                for i, leds in enumerate(steps):
                    seq = i << 5
                    byte4 = sval | seq | mod4
                    self._write([0x2, 0x4b, mval, mod3, byte4] + leds[0:57])
                    self._write([0x3] + leds[57:])
        self.device.release()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed."""
        if channel == 'sync':
            selected_channels = self._speed_channels
        else:
            selected_channels = { channel: self._speed_channels[channel] }
        for cname, (cid, smin, smax) in selected_channels.items():
            if duty < smin:
                duty = smin
            elif duty > smax:
                duty = smax
            if self.device_type == self.DEVICE_SMARTDEV_V2:
                wmsg = [0x62, 0x01, 0x00, 0x00, 0x00, 0x00]
                wmsg[2] = 0x01 << cid  # fan channel in last 3 bits of 3rd byte
                wmsg[cid+3] = duty # duty percent in 4th, 5th, and 6th bytes for Fans 1, 2, 3
                LOGGER.info('setting %s duty to %i%%', cname, duty)
                self._write(wmsg)
            else:
                LOGGER.info('setting %s duty to %i%%', cname, duty)
                self._write([0x2, 0x4d, cid, 0, duty])
        self.device.release()

    def _write(self, data):
        padding = [0x0]*(_WRITE_LENGTH - len(data))
        LOGGER.debug('write %s (and %i padding bytes)',
                     ' '.join(format(i, '02x') for i in data), len(padding))
        self.device.write(data + padding)

