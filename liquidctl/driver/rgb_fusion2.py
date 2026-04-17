"""liquidctl driver for Gigabyte RGB Fusion 2.0 USB controllers.

Supported controllers:

- ITE 5702: found in Gigabyte Z490 Vision D
- ITE 8297: found in Gigabyte X570 Aorus Elite

Copyright CaseySJ, Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import struct
import sys
import threading
import time
from collections import namedtuple

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_USAGE_PAGE = 0xff89
_RGB_CONTROL_USAGE = 0xcc
_OTHER_USAGE = 0x10
_REPORT_ID = 0xcc
_REPORT_BYTE_LENGTH = 63
_INIT_CMD = 0x60

_COLOR_CHANNELS = {
    'led1': (0x20, 0x01),
    'led2': (0x21, 0x02),
    'led3': (0x22, 0x04),
    'led4': (0x23, 0x08),
    'led5': (0x24, 0x10),
    'led6': (0x25, 0x20),
    'led7': (0x26, 0x40),
    'led8': (0x27, 0x80),
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

_ColorMode = namedtuple('_ColorMode', ['name', 'value', 'pulses', 'flash_count',
                                       'cycle_count', 'max_brightness', 'takes_color',
                                       'speed_values'])

_COLOR_MODES = {
    mode.name: mode
    for mode in [
        _ColorMode('off', 0x01, pulses=False, flash_count=0, cycle_count=0,
                   max_brightness=0, takes_color=False, speed_values=None),
        _ColorMode('fixed', 0x01, pulses=False, flash_count=0, cycle_count=0,
                   max_brightness=90, takes_color=True, speed_values=None),
        _ColorMode('pulse', 0x02, pulses=True, flash_count=0, cycle_count=0,
                   max_brightness=90, takes_color=True, speed_values=_PULSE_SPEEDS),
        _ColorMode('flash', 0x03, pulses=True, flash_count=1, cycle_count=0,
                   max_brightness=100, takes_color=True, speed_values=_FLASH_SPEEDS),
        _ColorMode('double-flash', 0x03, pulses=True, flash_count=2, cycle_count=0,
                   max_brightness=100, takes_color=True, speed_values=_DOUBLE_FLASH_SPEEDS),
        _ColorMode('color-cycle', 0x04, pulses=False, flash_count=0, cycle_count=7,
                   max_brightness=100, takes_color=False, speed_values=_COLOR_CYCLE_SPEEDS),
    ]
}


class RgbFusion2(UsbHidDriver):
    """liquidctl driver for Gigabyte RGB Fusion 2.0 USB controllers."""

    _MATCHES = [
        (0x048d, 0x5702, 'Gigabyte RGB Fusion 2.0 5702 Controller', {}),
        (0x048d, 0x8297, 'Gigabyte RGB Fusion 2.0 8297 Controller', {}),
    ]

    @classmethod
    def probe(cls, handle, **kwargs):
        """Probe `handle` and yield corresponding driver instances.

        These devices have multiple top-level HID usages, and HidapiDevice
        handles matching other usages have to be ignored.
        """

        # if usage_page/usage are not available due to hidapi limitations
        # (version, platform or backend), they are unfortunately left
        # uninitialized; because of this, we explicitly exclude the undesired
        # usage_page/usage pair, and assume in all other cases that we either
        # have the desired usage page/usage pair, or that on that system a
        # single handle is returned for that device interface (see: 259)

        if (handle.hidinfo['usage_page'] == _USAGE_PAGE and
                handle.hidinfo['usage'] == _OTHER_USAGE):
            return

        yield from super().probe(handle, **kwargs)

    def initialize(self, **kwargs):
        """Initialize the device.

        Returns a list of `(property, value, unit)` tuples, containing the
        firmware version and other useful information provided by the hardware.
        """

        self._send_feature_report([_REPORT_ID, _INIT_CMD])
        data = self._get_feature_report(_REPORT_ID)
        # be tolerant: 8297 controllers support report IDs yet return 0 in the
        # first byte, which is out of spec
        assert data[0] in (_REPORT_ID, 0) and data[1] == 0x01

        null = data.index(0, 12)
        dev_name = str(bytes(data[12:null]), 'ascii', errors='replace')
        fw_version = tuple(data[4:8])
        return [
            ('Hardware name', dev_name, ''),
            ('Firmware version', '{}.{}.{}.{}'.format(*fw_version), ''),
        ]

    def get_status(self, **kwargs):
        """Get a status report.

        Currently returns an empty list, but this behavior is not guaranteed as
        in the future the device may start to report useful information.  A
        non-empty list would contain `(property, value, unit)` tuples.
        """

        _LOGGER.info('status reports not available from %s', self.description)
        return []

    def set_color(self, channel, mode, colors, speed='normal', **kwargs):
        """Set the color mode for a specific channel.

        Up to eight individual channels are available, named 'led1' through
        'led8'.  In addition to these, the 'sync' channel can be used to apply
        the same settings to all channels.

        The table bellow summarizes the available channels.

        | Mode         | Colors required | Speed is customizable |
        | ------------ | --------------- | --------------------- |
        | off          |            zero |                    no |
        | fixed        |             one |                    no |
        | pulse        |             one |                   yes |
        | flash        |             one |                   yes |
        | double-flash |             one |                   yes |
        | color-cycle  |            zero |                   yes |

        `colors` should be an iterable of zero or one `[red, blue, green]`
        triples, where each red/blue/green component is a value in the range
        0–255.

        `speed`, when supported by the `mode`, can be one of: `slowest`,
        `slower`, `normal` (default), `faster`, `fastest` or `ludicrous`.
        """

        mode = _COLOR_MODES[mode]
        colors = iter(colors)

        if mode.takes_color:
            try:
                r, g, b = next(colors)
                single_color = (b, g, r)
            except StopIteration:
                raise ValueError(f'one color required for mode={mode.name}') from None
        else:
            single_color = (0, 0, 0)
        remaining = sum(1 for _ in colors)
        if remaining:
            _LOGGER.warning('too many colors for mode=%s, dropping %d', mode.name, remaining)

        brightness = clamp(100, 0, mode.max_brightness)  # hardcode this for now
        data = [_REPORT_ID, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, mode.value, brightness, 0x00]
        data += single_color
        data += [0x00, 0x00, 0x00, 0x00, 0x00]
        if mode.speed_values:
            data += mode.speed_values[speed]
        else:
            data += [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        data += [0x00, 0x00, mode.cycle_count, int(mode.pulses), mode.flash_count]

        if channel == 'sync':
            selected_channels = _COLOR_CHANNELS.values()
        else:
            selected_channels = (_COLOR_CHANNELS[channel],)
        for addr1, addr2 in selected_channels:
            data[1:3] = addr1, addr2
            self._send_feature_report(data)
        self._execute_report()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def reset_all_channels(self):
        """Reset all LED channels."""
        for addr1, _ in _COLOR_CHANNELS.values():
            self._send_feature_report([_REPORT_ID, addr1, 0])
        self._execute_report()

    def _get_feature_report(self, report_id):
        return self.device.get_feature_report(report_id, _REPORT_BYTE_LENGTH + 1)

    def _send_feature_report(self, data):
        padding = [0x0]*(_REPORT_BYTE_LENGTH + 1 - len(data))
        self.device.send_feature_report(data + padding)

    def _execute_report(self):
        """Request for the previously sent lighting settings to be applied."""
        self._send_feature_report([_REPORT_ID, 0x28, 0xff])

    def set_screen(self, channel, mode, value, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()


# IT5711-specific constants
# Each entry: channel_name → (led_index, effect_disable_bit)
# led_index determines the header byte (0x20 + led_index) and zone bitmask (1 << led_index).
# effect_disable_bit is the bit in the 0x32 SetStripBuiltinEffectState command
# (0x00 = all enabled; individual bits disable specific headers).
_IT5711_ARGB_CHANNELS = {
    'argb1': (5, 0x01),  # D_LED1 / ARGB_V2_1
    'argb2': (6, 0x02),  # D_LED2 / ARGB_V2_2
    'argb3': (7, 0x08),  # D_LED3 / ARGB_V2_3
}

# Default calibration: GRB byte order (bo_g=0, bo_r=1, bo_b=2).
# Matches observed hardware; overridden per-channel from device during initialize().
_IT5711_DEFAULT_CAL = 0x00010002

# PktRGB header bytes for each ARGB channel (differ from PktEffect header bytes).
_IT5711_PKTRGB_HEADERS = {
    'argb1': 0x58,  # D_LED1
    'argb2': 0x59,  # D_LED2
    'argb3': 0x62,  # D_LED3 (IT5711-specific)
}

# Per-strip LED count for PktRGB gradient writes. Device ignores data for
# unconnected LEDs; 60 covers all common fan configurations (up to 7+ fans).
_IT5711_LEDS_PER_STRIP = 60

_IT5711_COLOR_CYCLE_FPS = 24

# Rotation period in seconds for each named speed.
# IT5711 ARGB fans have fewer physical LEDs than Commander ST fan slots, so
# the same rotation period looks slower — speeds are set ~2x faster than Commander ST.
# Constraint: rot_secs > n_colors / FPS so gradient offset advances < 1 color/frame.
# 'cpu-speed' maps to None — the animation thread reads /proc/stat each frame and
# selects rot_secs dynamically from _CPU_SPEED_THRESHOLDS.
_IT5711_COLOR_CYCLE_SPEEDS = {
    'slow':      10.0,
    'medium':     4.0,
    'fast':       1.5,
    'faster':     0.5,
    'ludicrous':  0.25,
    'plaid':      0.15,
    'cpu-speed':  None,   # adaptive — maps CPU % to rot_secs each frame
}

# CPU usage → speed name mapping for 'cpu-speed' mode.
# Each (upper_pct_threshold, speed_name) pair; checked in order, first match wins.
# speed_name must exist in _IT5711_COLOR_CYCLE_SPEEDS and have a non-None rot_secs value.
_CPU_SPEED_THRESHOLDS = [
    (20,  'slow'),
    (40,  'medium'),
    (60,  'fast'),
    (80,  'faster'),
    (100, 'ludicrous'),
]


class RgbFusion2IT5711(UsbHidDriver):
    """liquidctl driver for Gigabyte IT5711 RGB Fusion 2.0 USB controller.

    Supports the three addressable ARGB headers found on IT5711-equipped boards
    (D_LED1 / ARGB_V2_1, D_LED2 / ARGB_V2_2, D_LED3 / ARGB_V2_3).

    All three channels are exposed regardless of whether physical hardware is
    connected to each header.  Use the channel name that matches your physical
    wiring (argb1, argb2, argb3, or sync for all at once).

    Tested on: Gigabyte X870 AORUS ELITE WIFI7 (firmware IT5711-GIGABYTE V1.0.17.5).
    """

    _MATCHES = [
        (0x048d, 0x5711, 'Gigabyte RGB Fusion 2.0 IT5711 Controller', {}),
    ]

    @classmethod
    def probe(cls, handle, **kwargs):
        """Probe `handle` and yield corresponding driver instances.

        IT5711 exposes two USB HID interfaces.  Only the RGB control interface
        (Usage Page 0xFF89, Usage 0xCC) should be used; the other interface has
        Usage Page 0x0059 and carries no LED data.

        If hidapi cannot provide usage information (version/platform limitation),
        the handle is accepted and super().probe() decides.
        """
        usage_page = handle.hidinfo['usage_page']
        usage = handle.hidinfo['usage']
        if usage_page not in (0, _USAGE_PAGE) or usage not in (0, _RGB_CONTROL_USAGE):
            return
        yield from super().probe(handle, **kwargs)

    def __init__(self, device, description, **kwargs):
        super().__init__(device, description, **kwargs)
        self._cal        = {}    # per-channel calibration; set during initialize()
        self._anim_thread  = None  # background color-cycle thread
        self._anim_stop    = None  # threading.Event to signal stop
        self._anim_params  = None  # (channels, colors, rot_secs) for restart
        self._anim_offset  = 0.0   # current gradient offset; preserved across restarts

    def disconnect(self, **kwargs):
        """Stop animation thread before closing the HID connection."""
        self._stop_animation()
        return super().disconnect(**kwargs)

    def initialize(self, **kwargs):
        """Initialize the device and read per-channel calibration data.

        Returns a list of tuples containing the firmware version, hardware
        name, and the native LED byte order read from the device.
        """
        self._send_feature_report([_REPORT_ID, 0x60])
        resp60 = self._get_feature_report(_REPORT_ID)

        self._send_feature_report([_REPORT_ID, 0x61])
        resp61 = self._get_feature_report(_REPORT_ID)

        # Firmware version at bytes 4–7 of the 0x60 response (shared with IT8297).
        fw = tuple(resp60[4:8])

        # Device name: null-terminated ASCII starting at byte 12 of the 0x60 response.
        try:
            null = bytes(resp60).index(0, 12)
            dev_name = bytes(resp60[12:null]).decode('ascii', errors='replace')
        except ValueError:
            dev_name = ''

        # Calibration: a uint32 LE encoding which byte position (0, 1, 2) in the
        # LED data carries each colour component.
        #   bo_b = cal & 0xFF          → byte index of Blue
        #   bo_g = (cal >> 8) & 0xFF   → byte index of Green
        #   bo_r = (cal >> 16) & 0xFF  → byte index of Red
        #
        # On IT5711, the 0x60 response bytes 12+ are the device name string, so
        # ARGB calibration comes entirely from the 0x61 response:
        #   resp61[4:8]  — D_LED3 (ARGB_V2_3 / argb3)
        #   resp61[8:12] — D_LED4 (not exposed)
        # D_LED1/D_LED2 calibration is not separately available for IT5711; the
        # same byte order is used for all three headers on Gigabyte boards.
        def _read_cal(data, offset):
            cal = struct.unpack_from('<I', bytes(data), offset)[0]
            bo_b = cal & 0xFF
            bo_g = (cal >> 8) & 0xFF
            bo_r = (cal >> 16) & 0xFF
            # Validate: each component index must be a distinct value in {0, 1, 2}.
            if {bo_b, bo_g, bo_r} == {0, 1, 2}:
                return cal
            _LOGGER.warning('unexpected calibration value 0x%08x at offset %d, '
                            'falling back to default GRB', cal, offset)
            return _IT5711_DEFAULT_CAL

        cal = _read_cal(resp61, 4)
        self._cal = {'argb1': cal, 'argb2': cal, 'argb3': cal}

        # Reset all effect registers and leave the device in a known idle state.
        self._send_feature_report([_REPORT_ID, 0x48, 0x00])
        for reg in list(range(0x20, 0x28)) + list(range(0x90, 0x93)):
            self._send_feature_report([_REPORT_ID, reg])
        self._send_feature_report([_REPORT_ID, 0x28, 0xFF, 0x07])
        self._send_feature_report([_REPORT_ID, 0x31, 0x00])

        def _order_str(c):
            labels = ['?', '?', '?']
            bo_b = c & 0xFF
            bo_g = (c >> 8) & 0xFF
            bo_r = (c >> 16) & 0xFF
            if all(0 <= x <= 2 for x in (bo_b, bo_g, bo_r)):
                labels[bo_b] = 'B'
                labels[bo_g] = 'G'
                labels[bo_r] = 'R'
            return ''.join(labels)

        result = [('Firmware version', '{}.{}.{}.{}'.format(*fw), '')]
        if dev_name:
            result.append(('Hardware name', dev_name, ''))
        result.append(('ARGB byte order', _order_str(cal), ''))
        return result

    def get_status(self, **kwargs):
        """Get device status.

        No runtime status data is available from this controller.
        """
        _LOGGER.info('status reports not available from %s', self.description)
        return []

    def set_color(self, channel, mode, colors, **kwargs):
        """Set the LED color mode for the specified ARGB channel.

        Valid channels:
          'argb1'   D_LED1 / ARGB_V2_1 header
          'argb2'   D_LED2 / ARGB_V2_2 header
          'argb3'   D_LED3 / ARGB_V2_3 header
          'sync'    all three channels at once

        Valid modes:
          'fixed'   static single color (requires one color)
          'off'     turn LEDs off

        Colors should be an iterable of [red, green, blue] triples (0–255).
        """
        # Stop any running animation before switching modes.
        self._stop_animation()

        mode = mode.lower()
        colors = list(colors)

        if channel == 'sync':
            channels = list(_IT5711_ARGB_CHANNELS.keys())
        elif channel in _IT5711_ARGB_CHANNELS:
            channels = [channel]
        else:
            raise ValueError(
                f'unknown channel {channel!r}; valid: argb1, argb2, argb3, sync')

        if mode == 'off':
            r, g, b = 0, 0, 0
            brightness = 0x00
        elif mode == 'fixed':
            if not colors:
                raise ValueError('fixed mode requires one color')
            r, g, b = colors[0]
            brightness = 0xFF
        elif mode == 'color-cycle':
            if len(colors) < 2:
                raise ValueError('color-cycle mode requires at least 2 colors')
            if len(colors) > 8:
                raise ValueError('color-cycle mode supports at most 8 colors')
            speed = kwargs.get('speed', 'medium')
            if speed not in _IT5711_COLOR_CYCLE_SPEEDS:
                valid = ', '.join(_IT5711_COLOR_CYCLE_SPEEDS)
                raise ValueError(f'unknown speed {speed!r}; valid: {valid}')
            rot_secs = _IT5711_COLOR_CYCLE_SPEEDS[speed]
            self._anim_offset = 0.0  # start fresh on explicit set_color call
            self._start_animation(channels, colors, rot_secs)
            return
        else:
            raise NotSupportedByDevice()

        # Enable built-in hardware effects on all ARGB headers.
        # Bitmask 0x00 = all channels enabled.
        self._send_feature_report([_REPORT_ID, 0x32, 0x00])

        cal_map = getattr(self, '_cal', {})
        acc_mask = 0

        for ch in channels:
            led_index, _ = _IT5711_ARGB_CHANNELS[ch]
            zone_bit = 1 << led_index
            # PktEffect color0 is packed as BGR in little-endian order
            # (byte 0 = B, byte 1 = G, byte 2 = R).  The firmware applies the
            # LED strip's native byte order internally; no calibration remapping
            # is needed here (calibration applies to PktRGB direct mode only).
            color0 = b | (g << 8) | (r << 16)

            pkt = [_REPORT_ID, 0x20 + led_index,
                   zone_bit & 0xFF, (zone_bit >> 8) & 0xFF,
                   (zone_bit >> 16) & 0xFF, (zone_bit >> 24) & 0xFF,
                   0, 0, 0, 0,   # zone1 = 0
                   0,             # reserved
                   0x01,          # EFFECT_STATIC
                   brightness,
                   0,             # min_brightness
                   color0 & 0xFF, (color0 >> 8) & 0xFF,
                   (color0 >> 16) & 0xFF, (color0 >> 24) & 0xFF]
            self._send_feature_report(pkt)
            acc_mask |= zone_bit

        # Apply all pending effects at once via accumulated zone bitmask.
        apply_pkt = [_REPORT_ID, 0x28,
                     acc_mask & 0xFF, (acc_mask >> 8) & 0xFF,
                     (acc_mask >> 16) & 0xFF, (acc_mask >> 24) & 0xFF]
        self._send_feature_report(apply_pkt)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    # ---- color-cycle animation -----------------------------------------------

    @staticmethod
    def _build_gradient(colors, led_count, offset):
        """Linear gradient across led_count LEDs, rotated by offset (in color units)."""
        nc = len(colors)
        result = []
        for i in range(led_count):
            pos = ((i * nc) / led_count + offset) % nc
            ci = int(pos) % nc
            ni = (ci + 1) % nc
            t = pos - int(pos)
            r = int(colors[ci][0] * (1-t) + colors[ni][0] * t)
            g = int(colors[ci][1] * (1-t) + colors[ni][1] * t)
            b = int(colors[ci][2] * (1-t) + colors[ni][2] * t)
            result.append((r, g, b))
        return result

    def _write_pktrgb(self, header, led_data, cal):
        """Write per-LED color data for one ARGB channel using PktRGB packets.

        led_data: list of (r, g, b) tuples.
        cal: calibration uint32 encoding byte order (bo_b, bo_g, bo_r).
        """
        bo_b = cal & 0xFF
        bo_g = (cal >> 8) & 0xFF
        bo_r = (cal >> 16) & 0xFF
        n = len(led_data)
        offset = 0  # byte offset in strip
        idx = 0
        while idx < n:
            leds_in_pkt = min(n - idx, 19)  # max 57 bytes = 19 LEDs per packet
            bcount = leds_in_pkt * 3
            led_bytes = [0] * bcount
            for i in range(leds_in_pkt):
                r, g, b = led_data[idx + i]
                led_bytes[i*3 + bo_r] = r
                led_bytes[i*3 + bo_g] = g
                led_bytes[i*3 + bo_b] = b
            pkt = [_REPORT_ID, header,
                   offset & 0xFF, (offset >> 8) & 0xFF,
                   bcount] + led_bytes
            self._send_feature_report(pkt)
            offset += bcount
            idx += leds_in_pkt

    def _start_animation(self, channels, colors, rot_secs):
        """Start the color-cycle background thread."""
        self._anim_params = (list(channels), list(colors), rot_secs)
        self._anim_stop = threading.Event()
        self._anim_thread = threading.Thread(
            target=self._animation_loop,
            args=(list(channels), list(colors), rot_secs,
                  self._anim_stop, self._anim_offset),
            daemon=True,
        )
        self._anim_thread.start()

    def _stop_animation(self):
        """Signal the animation thread to stop and wait for it to exit."""
        if self._anim_thread is not None:
            if self._anim_thread.is_alive():
                self._anim_stop.set()
                self._anim_thread.join(timeout=2.0)
            self._anim_thread = None
            self._anim_params = None

    @staticmethod
    def _read_cpu_stat():
        """Read raw /proc/stat CPU idle and total counters for cpu-speed mode.

        Returns (total_jiffies, idle_jiffies).  Call once per animation frame;
        compute the delta against the previous frame's reading to get CPU usage %
        over that ~41ms interval.  No sleep required — the frame loop provides it.
        """
        with open('/proc/stat') as f:
            fields = list(map(int, f.readline().split()[1:]))
        return sum(fields), fields[3]  # total, idle (4th field)

    def _animation_loop(self, channels, colors, rot_secs, stop_event, initial_offset=0.0):
        """Background thread: streams gradient frames until stop_event is set."""
        nc = len(colors)
        frame_dt = 1.0 / _IT5711_COLOR_CYCLE_FPS
        cpu_speed_mode = rot_secs is None
        step = nc / ((rot_secs or 10.0) * _IT5711_COLOR_CYCLE_FPS)  # slow default for first frame
        off = initial_offset
        prev_cpu_stat = None  # (total, idle) from previous frame; None until first read

        # Disable the built-in effect engine for each animated channel so PktRGB
        # writes persist instead of being overwritten by the hardware effect engine.
        disable_mask = 0
        for ch in channels:
            _, effect_disable_bit = _IT5711_ARGB_CHANNELS[ch]
            disable_mask |= effect_disable_bit
        self._send_feature_report([_REPORT_ID, 0x32, disable_mask])
        self._send_feature_report([_REPORT_ID, 0x28, 0xFF, 0x07])

        while not stop_event.is_set():
            t0 = time.monotonic()
            if cpu_speed_mode:
                curr = self._read_cpu_stat()
                if prev_cpu_stat is not None:
                    dt = curr[0] - prev_cpu_stat[0]
                    di = curr[1] - prev_cpu_stat[1]
                    if dt > 0:
                        cpu_pct = max(0.0, min(100.0, (1.0 - di / dt) * 100.0))
                        for thresh, name in _CPU_SPEED_THRESHOLDS:
                            if cpu_pct <= thresh:
                                step = nc / (_IT5711_COLOR_CYCLE_SPEEDS[name] * _IT5711_COLOR_CYCLE_FPS)
                                break
                prev_cpu_stat = curr
            acc_mask = 0
            for ch in channels:
                led_index, _ = _IT5711_ARGB_CHANNELS[ch]
                header = _IT5711_PKTRGB_HEADERS[ch]
                cal = self._cal.get(ch, _IT5711_DEFAULT_CAL)
                zone_bit = 1 << led_index
                led_data = self._build_gradient(colors, _IT5711_LEDS_PER_STRIP, off)
                self._write_pktrgb(header, led_data, cal)
                acc_mask |= zone_bit

            # Activate all channels simultaneously.
            apply_pkt = [_REPORT_ID, 0x28,
                         acc_mask & 0xFF, (acc_mask >> 8) & 0xFF,
                         (acc_mask >> 16) & 0xFF, (acc_mask >> 24) & 0xFF]
            self._send_feature_report(apply_pkt)

            self._anim_offset = off
            off = (off + step) % nc
            rem = frame_dt - (time.monotonic() - t0)
            if rem > 0:
                stop_event.wait(rem)

    # --------------------------------------------------------------------------

    def _get_feature_report(self, report_id):
        return self.device.get_feature_report(report_id, _REPORT_BYTE_LENGTH + 1)

    def _send_feature_report(self, data):
        padding = [0x0] * (_REPORT_BYTE_LENGTH + 1 - len(data))
        self.device.send_feature_report(data + padding)


# Acknowledgments:
#
# Thanks to SgtSixPack for capturing USB traffic on 0x8297 and testing the driver on Windows.
