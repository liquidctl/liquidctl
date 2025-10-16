"""liquidctl driver for NZXT Control Hub.

The NZXT Control Hub is a digital RGB lighting and fan speed controller.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_ANIMATION_SPEEDS = {
    'slowest':  0x0,
    'slower':   0x1,
    'normal':   0x2,
    'faster':   0x3,
    'fastest':  0x4,
}

_COLOR_MODES = {
        # (mode, size/variant, moving, min colors, max colors)
        'off':                              (0x00, 0x00, 0x00, 0, 0),
        'fixed':                            (0x00, 0x00, 0x00, 1, 1),
        'super-fixed':                      (0x01, 0x00, 0x00, 1, 40),  # independent leds
        'fading':                           (0x01, 0x00, 0x00, 1, 8),
        'spectrum-wave':                    (0x02, 0xfa, 0x00, 0, 0),
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
        'breathing':                        (0x07, 0x14, 0x03, 1, 8),   # colors for each step
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

_MIN_DUTY = 0
_MAX_DUTY = 100


class NzxtControlHub(UsbHidDriver):
    """NZXT Control Hub RGB and fan controller."""

    _MATCHES = [
        (0x1e71, 0x2022, 'NZXT Control Hub', {
            'speed_channel_count': 5,
            'color_channel_count': 5
        }),
    ]

    _MAX_READ_ATTEMPTS = 12
    _READ_LENGTH = 512
    _WRITE_LENGTH = 512
    _WRITE_ENDPOINT = 0x02

    def __init__(self, device, description, speed_channel_count, color_channel_count, **kwargs):
        """Instantiate a driver with a device handle."""
        super().__init__(device, description, **kwargs)
        self._speed_channels = {f'fan{i + 1}': (i, _MIN_DUTY, _MAX_DUTY)
                                for i in range(speed_channel_count)}
        self._color_channels = {f'led{i + 1}': i for i in range(color_channel_count)}
        if self._color_channels:
            self._color_channels['sync'] = 0xFF  # Special value for all channels

    def initialize(self, direct_access=False, **kwargs):
        """Initialize the device and the driver.

        This method should be called every time the systems boots, resumes from
        a suspended state, or if the device has just been (re)connected.

        Returns None or a list of `(property, value, unit)` tuples.
        """
        self.device.clear_enqueued_reports()
        
        # TODO: Add initialization commands if needed
        # Based on the capture, the device seems to work without explicit initialization
        
        return [
            ('Firmware version', 'Unknown', ''),
        ]

    def get_status(self, direct_access=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        # TODO: Implement status reading based on USB capture analysis
        # For now, return basic status for available channels
        ret = []
        
        # Add fan channel information
        for i in range(len(self._speed_channels)):
            ret.append((f'Fan {i + 1} speed', None, 'rpm'))
            ret.append((f'Fan {i + 1} voltage', None, 'V'))
            ret.append((f'Fan {i + 1} current', None, 'A'))
            ret.append((f'Fan {i + 1} control mode', 'PWM', ''))
        
        return ret

    def get_available_color_modes(self):
        """Get available color modes for this device."""
        return list(_COLOR_MODES.keys())

    def set_color(self, channel, mode, colors, speed='normal', direction='forward', **kwargs):
        """Set the color mode for a specific channel.

        Supported modes:
        - off: Turn off the channel
        - fixed: Set a fixed color
        - super-fixed: Set independent colors for each LED
        - fading: Fade between colors
        - spectrum-wave: Spectrum wave effect
        - marquee-3/4/5/6: Marquee effect with different sizes
        - covering-marquee: Covering marquee effect
        - alternating: Alternating colors
        - moving-alternating: Moving alternating colors
        - pulse: Pulsing effect
        - breathing: Breathing effect
        - super-breathing: Super breathing with independent LEDs
        - candle: Candle effect
        - wings: Wings effect
        - super-wave: Super wave with independent LEDs
        """
        if channel not in self._color_channels:
            raise ValueError(f"Invalid channel: {channel}")

        if mode not in _COLOR_MODES:
            raise ValueError(f"Invalid mode: {mode}. Supported modes: {list(_COLOR_MODES.keys())}")

        # Get mode parameters
        mode_byte, variant_byte, moving_byte, min_colors, max_colors = _COLOR_MODES[mode]

        # Convert colors to list if it's a map object
        colors_list = list(colors) if hasattr(colors, '__iter__') and not isinstance(colors, (list, tuple)) else colors

        # Validate color count
        if len(colors_list) < min_colors:
            raise ValueError(f"Mode '{mode}' requires at least {min_colors} colors")
        if len(colors_list) > max_colors:
            raise ValueError(f"Mode '{mode}' supports at most {max_colors} colors")

        # Handle off mode
        if mode == 'off':
            colors_list = [(0, 0, 0)]

        # Determine channel ID
        cid = self._color_channels[channel]

        _LOGGER.info('setting %s channel %s to mode %s with %d colors', 
                     self.description, channel, mode, len(colors_list))

        # Set color mode and data
        if cid == 0xFF:  # sync mode - set all channels
            for ch_id in range(len(self._color_channels) - 1):  # -1 to exclude 'sync'
                self._set_channel_color_mode(ch_id, mode_byte, variant_byte, moving_byte, colors_list, speed, direction)
        else:
            self._set_channel_color_mode(cid, mode_byte, variant_byte, moving_byte, colors_list, speed, direction)

    def _set_channel_color_mode(self, channel_id, mode_byte, variant_byte, moving_byte, colors, speed, direction):
        """Set color mode for a specific channel."""
        # Based on USB capture analysis:
        # Format: 26 04 [channel] 00 [color_data]
        # Channel mapping: led1=02, led2=04, led3=06, led4=08, led5=10
        channel_byte_map = {0: 0x02, 1: 0x04, 2: 0x06, 3: 0x08, 4: 0x10}
        channel_byte = channel_byte_map.get(channel_id, 0x08)
        _LOGGER.info('setting %s channel %s to mode %s with %d colors speed %s direction %s', 
                     self.description, channel_id, mode_byte, len(colors), speed, direction)
        # Build the command packet - fixed mode for now
        if mode_byte != 0x00:
            # Handle spectrum wave mode (0x02) with speed and direction
            if mode_byte == 0x02:  # spectrum-wave
                # Speed mapping from capture analysis (microsecond delays)
                speed_map = {
                    'slowest': [0x5e, 0x01],  # 24065 microseconds (slowest)
                    'slower': [0x2c, 0x01],   # 11265 microseconds (slow)
                    'normal': [0xfa, 0x00],   # 64000 microseconds (normal)
                    'faster': [0x96, 0x00],   # 38400 microseconds (fast)
                    'fastest': [0x50, 0x00]   # 20480 microseconds (fastest)
                }
                speed_bytes = speed_map.get(speed, [0xfa, 0x00])
                
                # Direction: 0x00 = forward, 0x02 = backward
                direction_byte = 0x02 if direction == 'backward' else 0x00
                
                # Build the spectrum wave packet with proper structure
                data = [0x2a, 0x04, channel_byte, channel_byte, mode_byte]
                
                # Add speed bytes (16-bit value, little-endian)
                data.extend(speed_bytes)
                
                # Add padding zeros until position 56 (28 in hex)
                data.extend([0x00] * (56 - len(data) -1))
                
                # Add direction byte at position 56
                data.append(direction_byte)
                
                # Add the remaining structure bytes (12 03 00 00...)
                data.extend([0x00, 0x00, 0x12, 0x03, 0x00, 0x00])
            elif mode_byte == 0x01:  # fading mode
                # Speed mapping for fading mode (different from spectrum wave)
                speed_map = {
                    'slowest': [0x50, 0x00],  # slowest
                    'slower': [0x3c, 0x00],   # slow
                    'normal': [0x28, 0x00],   # normal
                    'faster': [0x14, 0x00],   # fast
                    'fastest': [0x0a, 0x00]   # fastest
                }
                speed_bytes = speed_map.get(speed, [0x14, 0x00])
                
                # Build fading packet: 2a 04 08 08 01 [speed] 00 00 [colors] [count] 08 18 03...
                data = [0x2a, 0x04, channel_byte, channel_byte, mode_byte]
                data.extend(speed_bytes)
                
                # Add color data (GRB format)
                if colors:
                    for r, g, b in colors:
                        data.extend([g, r, b])  # GRB order
                    # Add padding to align with structure
                    while len(data) < 56:
                        data.append(0x00)
                    
                    # Add color count at position 56
                    data.append(len(colors))
                    
                    # Add structure bytes
                    data.extend([0x08, 0x18, 0x03, 0x00, 0x00])
                else:
                    # No colors - just padding
                    data.extend([0x00] * (61 - len(data)))
            elif mode_byte == 0x04:  # covering-marquee mode
                # Speed mapping for covering marquee (different from other modes)
                speed_map = {
                    'slowest': [0x5e, 0x01],  # slowest
                    'slow': [0x2c, 0x01],  # slow
                    'normal': [0xfa, 0x00],   # normal
                    'faster': [0x96, 0x00],   # fast
                    'fastest': [0x50, 0x00]   # fastest
                }
                speed_bytes = speed_map.get(speed, [0xfa, 0x00])
                
                # Build covering marquee packet: 2a 04 08 08 04 [speed] 00 00 [colors] [direction] [count] 00 18 03...
                data = [0x2a, 0x04, channel_byte, channel_byte, mode_byte]
                data.extend(speed_bytes)
                
                # Add color data (GRB format)
                if colors:
                    for r, g, b in colors:
                        data.extend([g, r, b])  # GRB order
                    # Add padding to align with structure
                    while len(data) < 56 - 1:
                        data.append(0x00)
                    
                    # Add direction byte at position 56
                    direction_byte = 0x02 if direction == 'backward' else 0x00
                    data.append(direction_byte)
                    
                    # Add color count at position 57
                    data.append(len(colors))
                    
                    # Add structure bytes
                    data.extend([0x00, 0x18, 0x03, 0x00, 0x00])
                else:
                    # No colors - just padding
                    data.extend([0x00] * (61 - len(data)))
            elif mode_byte == 0x0c:  # super-rainbow mode
                # Speed mapping for super rainbow (same as covering marquee)
                speed_map = {
                    'slowest': [0x5e, 0x01],  # slowest
                    'slow': [0x2c, 0x01],     # slow
                    'normal': [0xfa, 0x00],   # normal
                    'faster': [0x96, 0x00],   # fast
                    'fastest': [0x50, 0x00]   # fastest
                }
                speed_bytes = speed_map.get(speed, [0xfa, 0x00])
                
                # Build super rainbow packet: 2a 04 08 08 0c [speed] 00 00 [padding] [direction] 00 18 03...
                data = [0x2a, 0x04, channel_byte, channel_byte, mode_byte]
                data.extend(speed_bytes)
                data.extend([0x00, 0x00])
                
                # Add padding zeros until position 56
                while len(data) < 56:
                    data.append(0x00)
                
                # Add direction byte at position 56
                direction_byte = 0x02 if direction == 'backward' else 0x00
                data.append(direction_byte)
                
                # Add structure bytes
                data.extend([0x00, 0x18, 0x03, 0x00, 0x00])
            else:
                # Other modes use the standard format
                data = [0x2a, 0x04, channel_byte, channel_byte, mode_byte, variant_byte, moving_byte]
            
            # Pad to full packet size
            padding = [0x00] * (self._WRITE_LENGTH - len(data))
            data.extend(padding)
            
            self._write(data)
            
        else:
            data = [0x26, 0x04, channel_byte, 0x00]
            # Add color data - repeat GRB for each LED (24 LEDs based on capture)
            if colors:
                r, g, b = colors[0]
                # Pattern from capture: GG RR BB repeated for each LED (GRB order)
                for _ in range(24):  # 24 LEDs based on capture analysis
                    data.extend([g, r, b])  # GRB order instead of RGB
            else:
                data.extend([0x00] * (24 * 3))  # 24 LEDs * 3 bytes each
        
            # Pad to full packet size
            padding = [0x00] * (self._WRITE_LENGTH - len(data))
            data.extend(padding)
            
            self._write(data)
            self._apply_color_settings(channel_byte)


    def _apply_color_settings(self, channel_byte):
        """Apply/commit the color settings to the device."""
        # Based on USB capture analysis:
        # Format: 26 06 [channel] 00 01 00 00 18 00 00 80 00 32 00 00 01 00 00...
        data = [0x26, 0x06, channel_byte, 0x00, 0x01, 0x00, 0x00, 0x18, 0x00, 0x00, 0x80, 0x00, 0x32, 0x00, 0x00, 0x01, 0x00, 0x00]
        
        # Pad to full packet size
        padding = [0x00] * (self._WRITE_LENGTH - len(data))
        data.extend(padding)
        
        self._write(data)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        if channel == 'sync':
            selected_channels = self._speed_channels
        else:
            selected_channels = {channel: self._speed_channels[channel]}

        for cname, (cid, dmin, dmax) in selected_channels.items():
            duty = clamp(duty, dmin, dmax)
            _LOGGER.info('setting %s duty to %d%%', cname, int(duty))
            self._write_fixed_duty(cid, duty)

    def _write_fixed_duty(self, cid, duty):
        """Write fixed duty command to device."""
        # Based on Smart Device V2 protocol: 0x62, 0x01, 0x01 << cid, 0x00, 0x00, 0x00
        # Fan channel passed as bitflag in last 3 bits of 3rd byte
        # Duty percent in 4th, 5th, and 6th bytes for fan1, fan2, fan3 respectively
        # For Control Hub with 5 fans, we need to extend this protocol
        
        # Build the command packet
        msg = [0x62, 0x01, 0x01 << cid, 0x00, 0x00, 0x00, 0x00, 0x00]  # Extended for 5 fans
        
        # Set duty for the specific fan channel
        # For Control Hub, we need to set the duty in the appropriate byte position
        if cid < 5:  # Ensure we don't exceed 5 fans
            msg[cid + 3] = duty  # duty percent in bytes 3-7 for fan1-fan5
        
        # Pad to full packet size
        padding = [0x00] * (self._WRITE_LENGTH - len(msg))
        msg.extend(padding)
        
        self._write(msg)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set speed profile for a channel."""
        raise NotSupportedByDevice("Speed profiles are not supported by this device")

    def _write(self, data):
        """Write data to the device."""
        if len(data) != self._WRITE_LENGTH:
            raise ValueError(f"Data length must be {self._WRITE_LENGTH} bytes")
        self.device.write(data)

    def _read(self):
        """Read data from the device."""
        return self.device.read(self._READ_LENGTH)

