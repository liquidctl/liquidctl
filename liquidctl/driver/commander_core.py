"""liquidctl drivers for Corsair Commander Core.

Supported devices:

- Corsair Commander Core

Copyright ParkerMc and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import json
import logging
import os
import threading
import time
from contextlib import contextmanager

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet, NotSupportedByDriver, NotSupportedByDevice
from liquidctl.util import clamp, u16le_from

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 96
_RESPONSE_LENGTH = 96

_INTERFACE_NUMBER = 0

_FAN_COUNT = 6

# Persist LED state across liqctld restarts / fresh device connections.
# Stored in /run (tmpfs) so it survives service restarts but not reboots.
_LED_STATE_DIR  = '/run/liquidctl'
_LED_STATE_FILE = '/run/liquidctl/commander_core_led_state.json'

_CMD_WAKE = (0x01, 0x03, 0x00, 0x02)
_CMD_SLEEP = (0x01, 0x03, 0x00, 0x01)
_CMD_GET_FIRMWARE = (0x02, 0x13)
_CMD_CLOSE_ENDPOINT = (0x05, 0x01, 0x00)
_CMD_OPEN_ENDPOINT = (0x0d, 0x00)
_CMD_READ_INITIAL = (0x08, 0x00, 0x01)
_CMD_READ_MORE = (0x08, 0x00, 0x02)
_CMD_READ_FINAL = (0x08, 0x00, 0x03)
_CMD_WRITE = (0x06, 0x00)
_CMD_WRITE_MORE = (0x07, 0x00)

_MODE_LED_COUNT = (0x20,)
_MODE_GET_SPEEDS = (0x17,)
_MODE_GET_TEMPS = (0x21,)
_MODE_CONNECTED_SPEEDS = (0x1a,)
_MODE_HW_SPEED_MODE = (0x60, 0x6d)
_MODE_HW_FIXED_PERCENT = (0x61, 0x6d)
_MODE_HW_CURVE_PERCENT = (0x62, 0x6d)

# Firmware 2.x shifted the hardware-profile endpoint IDs by one position.
# Data types and payload formats are unchanged between firmware versions.
_MODE_HW_SPEED_MODE_V2    = (0x61, 0x6d)
_MODE_HW_FIXED_PERCENT_V2 = (0x62, 0x6d)
_MODE_HW_CURVE_PERCENT_V2 = (0x64, 0x6d)

_DATA_TYPE_SPEEDS = (0x06, 0x00)
_DATA_TYPE_LED_COUNT = (0x0f, 0x00)
_DATA_TYPE_TEMPS = (0x10, 0x00)
_DATA_TYPE_CONNECTED_SPEEDS = (0x09, 0x00)
_DATA_TYPE_HW_SPEED_MODE = (0x03, 0x00)
_DATA_TYPE_HW_FIXED_PERCENT = (0x04, 0x00)
_DATA_TYPE_HW_CURVE_PERCENT = (0x05, 0x00)

# fw2.x write-mode endpoint — fan speed direct control (no SLEEP required).
# All four command variants confirmed via iCUE usbmon capture (2026-04-17).
_CMD_OPEN_ENDPOINT_WRITE  = (0x0d, 0x01)        # write-mode open  (vs read 0x0d,0x00)
_CMD_PREP_WRITE           = (0x09, 0x01)        # required pre-write command
_CMD_WRITE_DIRECT         = (0x06, 0x01)        # write variant for write-mode endpoints
_CMD_CLOSE_ENDPOINT_WRITE = (0x05, 0x01, 0x01)  # write-mode close (vs read 0x05,0x01,0x00)

_MODE_FAN_DIRECT          = (0x18, 0x00)        # fan speed direct control endpoint
_DATA_TYPE_FAN_DIRECT     = (0x07, 0x00)        # data type tag for (0x18,0x00) writes

# LED endpoints — fw2.x only (Commander ST, 0x0c32)
# Packet size: device uses USB FS 64-byte interrupt reports for LED writes.
# Fan speed writes fit in 64 bytes, so _REPORT_LENGTH=96 works for those.
# LED writes span multiple packets; 96-byte buffers silently truncate to 64,
# corrupting color data. Use _LED_REPORT_LENGTH=64 for all LED commands.
_LED_REPORT_LENGTH    = 64

_MODE_LED_COLORS      = (0x22, 0x00)
_MODE_LED_TYPE        = (0x1e, 0x00)
_DATA_TYPE_LED_COLORS = (0x12, 0x00)
_DATA_TYPE_LED_TYPE   = (0x0d, 0x00)

_AIO_LED_COUNT  = 29   # pump head LED slots (confirmed)
_FAN_LED_SLOTS  = 34   # always 34 slots per fan port (QL mode, confirmed)
                       # device fills first N LEDs; extra slots are zero-padded

# Fan type payload: forces all 6 fan ports to QL mode (0x06, 34 slots).
# Mirrors OpenRGB SetFanMode(false). Works for both QL and SP physical fans.
# Must be written BEFORE WAKE (hardware mode). WAKE after reinitializes device.
_LED_TYPE_PAYLOAD = bytes([
    0x07,
    0x01, 0x08,   # ch0: AIO pump head
    0x01, 0x06,   # ch1–ch6: QL fan (34 slots each) — confirmed working
    0x01, 0x06,
    0x01, 0x06,
    0x01, 0x06,
    0x01, 0x06,
    0x01, 0x06,
])

_FAN_MODE_FIXED_PERCENT = 0x00
_FAN_MODE_CURVE_PERCENT = 0x02

_COLOR_CYCLE_FPS = 24  # hardware sustains ~27fps; 24 keeps step<1 down to 0.125s/rotation

# Rotation period in seconds for each named speed.
# Constraint: rot_secs > n_colors / FPS so gradient offset advances < 1 color/frame
# (keeps rotation visually coherent and directional rather than strobing).
# 'cpu-speed' maps to None — the animation thread reads /proc/stat each frame and
# selects rot_secs dynamically from _CPU_SPEED_THRESHOLDS.
_COLOR_CYCLE_SPEEDS = {
    'slow':      20.0,
    'medium':     8.0,
    'fast':       3.0,
    'faster':     1.0,
    'ludicrous':  0.5,
    'plaid':      0.15,
    'cpu-speed':  None,   # adaptive — maps CPU % to rot_secs each frame
    'fan-speed':  -1.0,   # adaptive — maps fan RPM to rot_secs each frame
}

# CPU usage → speed name mapping for 'cpu-speed' mode.
# Each (upper_pct_threshold, speed_name) pair; checked in order, first match wins.
# speed_name must exist in _COLOR_CYCLE_SPEEDS and have a non-None rot_secs value.
_CPU_SPEED_THRESHOLDS = [
    (20,  'slow'),
    (40,  'medium'),
    (60,  'fast'),
    (80,  'faster'),
    (100, 'ludicrous'),
]

# Fan RPM → speed name mapping for 'fan-speed' mode.
# Covers the typical Commander ST fan range (0–2000+ RPM).
# Zone 0 reads pump RPM; zones 1–6 read the matching fan port RPM.
_FAN_SPEED_THRESHOLDS = [
    (300,   'slow'),      # stopped / very low
    (700,   'medium'),    # idle / low speed
    (1100,  'fast'),      # moderate speed
    (1500,  'faster'),    # high speed
    (99999, 'ludicrous'), # max speed
]

# Speed multipliers applied on top of threshold-selected rotation periods.
# >1.0 = faster animation, <1.0 = slower.
_CPU_SPEED_BOOST = 1.5   # cpu-speed mode
_FAN_SPEED_BOOST = 0.7   # fan-speed mode

class CommanderCore(UsbHidDriver):
    """Corsair Commander Core"""

    # For a non-exhaustive list of issues, see: #520, #583, #598, #623, #705
    _MATCHES = [
        (0x1b1c, 0x0c1c, 'Corsair Commander Core (broken)', {"has_pump": True}),
        (0x1b1c, 0x0c2a, 'Corsair Commander Core XT (broken)', {"has_pump": False}),
        (0x1b1c, 0x0c32, 'Corsair Commander ST (broken)', {"has_pump": True}),
    ]

    def __init__(self, device, description, has_pump, **kwargs):
        super().__init__(device, description, **kwargs)
        self._has_pump = has_pump
        self._fw_major = None
        # fw2.x cache: avoids read-modify-write which overflows the 54-byte
        # USB FS packet limit when all 7 channels have 2-pt curves (71 bytes).
        self._curve_cache = {}      # channel index -> [(temp, duty), ...]
        self._pump_duty_1pt = 70    # pump fixed duty for the fw2.x 1-pt entry
        self._led_payload      = None  # cached color payload; None = LED not set
        self._led_type_sent    = False # fan type write done once per session
        self._port_led_counts  = None  # [leds_per_port, ...] length _FAN_COUNT; set by initialize()
        self._anim_thread      = None  # background color-cycle thread
        self._anim_stop        = None  # threading.Event to signal thread stop
        self._zone_states      = {}    # {zone_idx: {'colors', 'rot_secs', 'offset'}}
        self._fan_rpms         = {}    # {zone_idx: rpm} last known speeds; updated by get_status()
        self._anim_lock     = threading.Lock()  # serializes HID access between animation
                                                # thread and main thread; prevents concurrent
                                                # reads from stealing each other's responses
        self._committed_duties = {}           # {channel_index: duty} last written to device;
                                              # skip redundant writes when coolercontrold
                                              # re-sends same duty on each poll

    def initialize(self, **kwargs):
        """Initialize the device and get the fan modes."""

        with self._wake_device_context(commit_speed=True):
            # Get Firmware
            res = self._send_command(_CMD_GET_FIRMWARE)
            fw_version = (res[3], res[4], res[5])
            self._fw_major = fw_version[0]

            status = [('Firmware version', '{}.{}.{}'.format(*fw_version), '')]

            # Get LEDs per fan
            res = self._read_data(_MODE_LED_COUNT, _DATA_TYPE_LED_COUNT)
            num_devices = res[0]
            led_data = res[1:1 + num_devices * 4]
            port_led_counts = []
            for i in range(0, num_devices):
                connected = u16le_from(led_data, offset=i * 4) == 2
                num_leds = u16le_from(led_data, offset=i * 4 + 2)
                if self._has_pump:
                    label = 'AIO LED count' if i == 0 else f'RGB port {i} LED count'
                else:
                    label = f'RGB port {i+1} LED count'

                status += [(label, num_leds if connected else None, '')]

                # Collect fan port LED counts (skip zone 0 = pump when has_pump).
                if not (self._has_pump and i == 0):
                    port_led_counts.append(num_leds if connected else 0)

            # Pad to _FAN_COUNT so zone indices are always valid.
            while len(port_led_counts) < _FAN_COUNT:
                port_led_counts.append(0)
            self._port_led_counts = port_led_counts[:_FAN_COUNT]

            # Get what fans are connected
            res = self._read_data(_MODE_CONNECTED_SPEEDS, _DATA_TYPE_CONNECTED_SPEEDS)
            num_devices = res[0]
            for i in range(0, num_devices):
                if self._has_pump:
                    label = 'AIO port connected' if i == 0 else f'Fan port {i} connected'
                else:
                    label = f'Fan port {i+1} connected'

                status += [(label, res[i + 1] == 0x07, '')]

            # Get what temp sensors are connected
            for i, temp in enumerate(self._get_temps()):
                connected = temp is not None
                if self._has_pump:
                    label = 'Water temperature sensor' if i == 0 and self._has_pump else f'Temperature sensor {i}'
                else:
                    label = f'Temperature sensor {i+1}'

                status += [(label, connected, '')]

            # fw2.x: bootstrap speed-mode endpoint if uninitialized.
            # On a fresh device or after USB reset, (0x61, 0x6d) returns (0x00, 0x00)
            # inside a wake context. _write_data's guard would refuse to write to it;
            # use _write_data_bootstrap instead.  Default: all channels in fixed-percent
            # mode (0x00).  set_fixed_speed() and set_speed_profile() flip individual
            # channels as needed on each call.
            if self._fw_major >= 2:
                try:
                    self._read_data(_MODE_HW_SPEED_MODE_V2, _DATA_TYPE_HW_SPEED_MODE)
                except ExpectationNotMet:
                    n_ch = _FAN_COUNT + (1 if self._has_pump else 0)
                    bootstrap = bytes([n_ch] + [_FAN_MODE_FIXED_PERCENT] * n_ch)
                    self._write_data_bootstrap(
                        _MODE_HW_SPEED_MODE_V2, _DATA_TYPE_HW_SPEED_MODE, bootstrap)

        return status

    def get_status(self, **kwargs):
        """Get all the fan speeds and temps"""
        status = []

        with self._wake_device_context():
            speeds = list(self._get_speeds())
            for i, speed in enumerate(speeds):
                self._fan_rpms[i] = speed  # cache for fan-speed LED mode
            for i, speed in enumerate(speeds):
                if self._has_pump:
                    label = 'Pump speed' if i == 0 else f'Fan speed {i}'
                else:
                    label = f'Fan speed {i+1}'

                status += [(label, speed, 'rpm')]

            for i, temp in enumerate(self._get_temps()):
                if temp is None:
                    continue

                if self._has_pump:
                    label = 'Water temperature' if i == 0 else f'Temperature {i}'
                else:
                    label = f'Temperature {i}'

                status += [(label, temp, '°C')]

        return status

    def set_color(self, channel, mode, colors, **kwargs):
        """Set LED color for the specified channel.

        Valid channels:
          'pump'         pump head only (zone 0, 29 LEDs)  ['aio' accepted as alias]
          'all'          all zones (pump head + all fan ports)  ['led', 'sync' accepted as aliases]
          'led1'–'led6'  individual fan ports (zone 1–6, 34 slots each)

        Valid modes: 'static', 'color-cycle', 'off'

        Each zone is independently configurable — setting one zone does not affect
        others.  'led'/'sync' overrides all zones.  The animation thread blends all
        active zones into one 699-byte payload each frame.

        Only supported on firmware 2.x (Commander ST, 0x0c32).
        """
        if self._fw_major is not None and self._fw_major < 2:
            raise NotSupportedByDevice()

        mode = mode.lower()
        colors = list(colors)

        # Resolve channel → set of zone indices (0=pump head, 1-6=fan ports)
        if channel in ('pump', 'aio', 'led0'):
            zones = {0}
        elif channel in ('all', 'led', 'sync'):
            zones = set(range(7))
        elif channel.startswith('led') and channel[3:].isdigit():
            z = int(channel[3:])
            if z < 1 or z > _FAN_COUNT:
                raise ValueError(f'unknown channel, should be pump, led, sync, or led1–led{_FAN_COUNT}')
            zones = {z}
        else:
            raise ValueError(f'unknown channel, should be pump, led, sync, or led1–led{_FAN_COUNT}')

        # Resolve mode → (colors_list, rot_secs)
        #   color-cycle: rot_secs = seconds per full rotation (None = cpu-speed)
        #   static:      rot_secs = 0.0  (no rotation; gradient renders as solid)
        #   off:         remove zones from _zone_states
        if mode == 'color-cycle':
            if len(colors) < 2:
                raise ValueError('color-cycle mode requires at least 2 colors')
            if len(colors) > 8:
                raise ValueError('color-cycle mode supports at most 8 colors')
            speed = kwargs.get('speed', 'medium')
            if speed not in _COLOR_CYCLE_SPEEDS:
                valid = ', '.join(_COLOR_CYCLE_SPEEDS)
                raise ValueError(f'unknown speed {speed!r}; valid: {valid}')
            rot_secs = _COLOR_CYCLE_SPEEDS[speed]
        elif mode == 'static':
            if not colors:
                raise ValueError('static mode requires at least one color')
            colors = [colors[0]]  # only the first color matters
            rot_secs = 0.0
        elif mode == 'off':
            colors = [(0, 0, 0)]
            rot_secs = 0.0
        else:
            raise NotSupportedByDriver(f'unsupported mode {mode!r}; valid: static, color-cycle, off')

        if not self._led_type_sent:
            # Fan type write must happen while device is in HARDWARE mode (before WAKE).
            self._send_command(_CMD_SLEEP)
            self._write_led_data(_MODE_LED_TYPE, _DATA_TYPE_LED_TYPE, _LED_TYPE_PAYLOAD)
            self._led_type_sent = True

        # Update per-zone state under the animation lock.
        # The running thread reads _zone_states each frame while holding this lock,
        # so this update takes effect on the very next frame (≤42ms latency).
        with self._anim_lock:
            for z in zones:
                if mode == 'off':
                    self._zone_states.pop(z, None)
                else:
                    # Preserve existing offset so animation continues smoothly
                    # when only speed/color changes (avoids a visible jump).
                    existing_offset = self._zone_states.get(z, {}).get('offset', 0.0)
                    self._zone_states[z] = {
                        'colors':   list(colors),
                        'rot_secs': rot_secs,
                        'offset':   existing_offset,
                    }

        if self._zone_states:
            self._ensure_animation_thread()
        else:
            self._stop_animation()
            # Device is still in WAKE mode (animation left it there). Write a
            # black payload so LEDs actually go dark rather than showing the
            # last animated frame indefinitely.
            if self._led_type_sent:
                self._send_command(_CMD_WAKE)
                port_counts = self._port_led_counts or [_FAN_LED_SLOTS] * _FAN_COUNT
                black_payload = bytes(_AIO_LED_COUNT * 3 + sum(port_counts) * 3)
                self._write_led_data(_MODE_LED_COLORS, _DATA_TYPE_LED_COLORS, black_payload)
            self._led_payload = None

    def _ensure_fw_version(self):
        """Fetch and cache firmware major version. Must be called inside a wake context."""
        if self._fw_major is None:
            res = self._send_command(_CMD_GET_FIRMWARE)
            self._fw_major = res[3]

    # ---- color-cycle animation -----------------------------------------------

    @staticmethod
    def _build_gradient(colors, led_count, offset):
        """Linear gradient across led_count LEDs, rotated by offset (in color units)."""
        nc = len(colors)
        result = bytearray(led_count * 3)
        for i in range(led_count):
            pos = ((i * nc) / led_count + offset) % nc
            ci = int(pos) % nc
            ni = (ci + 1) % nc
            t = pos - int(pos)
            result[i*3]   = int(colors[ci][0] * (1-t) + colors[ni][0] * t)
            result[i*3+1] = int(colors[ci][1] * (1-t) + colors[ni][1] * t)
            result[i*3+2] = int(colors[ci][2] * (1-t) + colors[ni][2] * t)
        return result

    def _ensure_animation_thread(self):
        """Start the frame-pump thread if not already running.

        Does NOT reset zone states or offsets — zones updated in _zone_states
        under _anim_lock take effect on the very next frame.
        """
        if self._anim_thread is not None and self._anim_thread.is_alive():
            return
        self._anim_stop = threading.Event()
        self._anim_thread = threading.Thread(
            target=self._animation_loop,
            args=(self._anim_stop,),
            daemon=True,
        )
        self._anim_thread.start()

    def _stop_animation(self):
        """Signal the animation thread to stop and wait for it to exit."""
        if self._anim_thread is not None:
            if self._anim_thread.is_alive():
                self._anim_stop.set()
                # join() is bounded: at most one _write_led_data() call (~42ms at
                # 24fps with fast HID) plus remaining inter-frame sleep.
                self._anim_thread.join()
            self._anim_thread = None

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

    def _animation_loop(self, stop_event):
        """Frame-pump thread: blends all active zones into one 699-byte payload per frame.

        Each zone in _zone_states animates independently with its own colors, speed,
        and phase offset.  All zones are written atomically in a single
        OPEN_ENDPOINT → WRITE → WRITE_MORE... → CLOSE_ENDPOINT sequence.

        _anim_lock is held for the entire frame (build + write ≈ 45ms at 24fps).
        set_color() acquires the same lock to update _zone_states — changes take
        effect on the next frame (≤45ms latency), with no thread restart required.

        _wake_device_context() also acquires _anim_lock to serialize fan ops with
        the animation thread without stopping it.
        """
        first_frame = True
        prev_cpu_stat = None
        cpu_rot_secs = _COLOR_CYCLE_SPEEDS.get('slow', 20.0)  # fallback for first frame

        while not stop_event.is_set():
            try:
                t0 = time.monotonic()

                with self._anim_lock:
                    if stop_event.is_set() or not self._zone_states:
                        break

                    # Read CPU stat once per frame (shared by all cpu-speed zones).
                    curr = self._read_cpu_stat()
                    if prev_cpu_stat is not None:
                        dt = curr[0] - prev_cpu_stat[0]
                        di = curr[1] - prev_cpu_stat[1]
                        if dt > 0:
                            cpu_pct = max(0.0, min(100.0, (1.0 - di / dt) * 100.0))
                            for thresh, name in _CPU_SPEED_THRESHOLDS:
                                if cpu_pct <= thresh:
                                    cpu_rot_secs = _COLOR_CYCLE_SPEEDS[name]
                                    break
                    prev_cpu_stat = curr

                    # Build payload from all active zone states.
                    # Fan LED data is packed contiguously using actual per-port LED
                    # counts (read from device during initialize()).  This gives each
                    # zone the correct byte range for independent per-port control.
                    port_counts = self._port_led_counts or [_FAN_LED_SLOTS] * _FAN_COUNT
                    payload = bytearray(_AIO_LED_COUNT * 3 + sum(port_counts) * 3)
                    for zone_idx, state in self._zone_states.items():
                        if state['rot_secs'] is None:       # cpu-speed
                            rot = cpu_rot_secs
                            boost = _CPU_SPEED_BOOST
                        elif state['rot_secs'] < 0:         # fan-speed
                            rpm = self._fan_rpms.get(zone_idx, 0)
                            rot = _COLOR_CYCLE_SPEEDS['slow']   # fallback until first get_status()
                            for thresh, name in _FAN_SPEED_THRESHOLDS:
                                if rpm <= thresh:
                                    rot = _COLOR_CYCLE_SPEEDS[name]
                                    break
                            boost = _FAN_SPEED_BOOST
                        else:                               # fixed speed
                            rot = state['rot_secs']
                            boost = 1.0
                        nc = len(state['colors'])
                        if rot > 0 and nc > 1:
                            step = nc * boost / (rot * _COLOR_CYCLE_FPS)
                        else:
                            step = 0.0
                        if zone_idx == 0:
                            led_count = _AIO_LED_COUNT
                            gradient = self._build_gradient(state['colors'], led_count, state['offset'])
                            payload[0:_AIO_LED_COUNT * 3] = gradient
                        else:
                            led_count = port_counts[zone_idx - 1]
                            gradient = self._build_gradient(state['colors'], led_count, state['offset'])
                            start = _AIO_LED_COUNT * 3 + sum(port_counts[:zone_idx - 1]) * 3
                            payload[start:start + led_count * 3] = gradient
                        state['offset'] = (state['offset'] + step) % max(nc, 1)

                    if first_frame:
                        self._send_command(_CMD_WAKE)
                        first_frame = False
                    self._write_led_data(_MODE_LED_COLORS, _DATA_TYPE_LED_COLORS, payload)
                    self._led_payload = bytes(payload)

                self._save_led_state()  # outside lock: file I/O; _led_payload already set
                rem = (1.0 / _COLOR_CYCLE_FPS) - (time.monotonic() - t0)
                if rem > 0:
                    stop_event.wait(rem)  # interruptible sleep
            except Exception as e:
                _LOGGER.warning('animation frame failed, retrying in 2s: %s', e)
                first_frame = True  # force WAKE before next write; device may be in SLEEP
                stop_event.wait(2.0)

    # --------------------------------------------------------------------------

    # ---- fw2.x curve-payload helpers -----------------------------------------

    def _fw2_1pt_entry(self, duty_pct, temp_c=10.0):
        """Build a 6-byte 1-point curve entry (effectively constant duty).

        Using temp_c=10 ensures the entry is active at all realistic water
        temperatures (always > 10 C), giving a stable constant-duty curve.
        """
        t = round(temp_c * 10)
        d = clamp(duty_pct, 0, 100)
        return bytes([0x00, 0x01, t & 0xFF, (t >> 8) & 0xFF, d & 0xFF, (d >> 8) & 0xFF])

    def _fw2_2pt_entry(self, pt0, pt1):
        """Build a 10-byte 2-point temperature-curve entry."""
        t0 = round(pt0[0] * 10)
        t1 = round(pt1[0] * 10)
        d0 = clamp(round(pt0[1]), 0, 100)
        d1 = clamp(round(pt1[1]), 0, 100)
        return bytes([
            0x00, 0x02,
            t0 & 0xFF, (t0 >> 8) & 0xFF, d0 & 0xFF, (d0 >> 8) & 0xFF,
            t1 & 0xFF, (t1 >> 8) & 0xFF, d1 & 0xFF, (d1 >> 8) & 0xFF,
        ])

    def _fw2_reduce_to_2pt(self, profile):
        """Reduce a multi-point profile to 2 representative points.

        Keeps points[0] (low-temperature anchor) and the last point where
        duty is still increasing (first point at which duty stops climbing).
        """
        pts = list(profile)
        if len(pts) <= 2:
            if len(pts) == 2:
                return pts
            if len(pts) == 1:
                return [pts[0], pts[0]]
            return [(0, 0), (100, 0)]
        last_ramp_idx = len(pts) - 1
        for ri in range(len(pts) - 1):
            if pts[ri][1] >= pts[ri + 1][1]:
                last_ramp_idx = ri
                break
        return [pts[0], pts[last_ramp_idx]]

    def _fw2_interp_duty(self, profile, design_temp):
        """Linearly interpolate duty at design_temp from a profile."""
        pts = sorted(profile, key=lambda p: p[0])
        if not pts:
            return 70
        if design_temp <= pts[0][0]:
            return int(pts[0][1])
        if design_temp >= pts[-1][0]:
            return int(pts[-1][1])
        for i in range(len(pts) - 1):
            t0, d0 = pts[i]
            t1, d1 = pts[i + 1]
            if t0 <= design_temp <= t1:
                return round(d0 + (d1 - d0) * (design_temp - t0) / (t1 - t0))
        return int(pts[-1][1])

    def _fw2_build_curve_payload(self):
        """Build the 51-byte curve payload for fw2.x.

        The Corsair Commander ST uses USB Full-Speed interrupt endpoints with
        wMaxPacketSize=64 bytes.  The CMD_WRITE HID report header occupies 10
        bytes, leaving exactly 54 bytes of curve data per write.  The device
        firmware only processes the first USB packet; CMD_WRITE_MORE is silently
        ignored.

        Encoding (1 + 6+6+6+6+10+10+6 = 51 bytes, all within HID[10..60]):
          ch0 (pump):  1-pt [10C -> pump_duty]     (constant speed)
          ch1 (fan1):  1-pt [10C -> duty@33C]      (constant, profile-derived)
          ch2 (fan2):  1-pt [10C -> duty@33C]
          ch3 (fan3):  1-pt [10C -> duty@33C]
          ch4 (fan4):  2-pt temperature curve      (hardware-responsive)
          ch5 (fan5):  2-pt temperature curve      (hardware-responsive)
          ch6 (fan6):  1-pt [10C -> duty@33C]

        Fan4 and fan5 receive full temperature-curve treatment because they
        sit early enough in the payload (HID[45..54]) to be completely within
        the first 64-byte USB packet.  Channels 0-3 and 6 use 1-pt constant
        entries derived from the profile at a 33 C design temperature.
        """
        _DESIGN_TEMP = 33.0   # representative operating temperature for 1-pt duty

        entries = []
        for ch in range(7):
            profile = self._curve_cache.get(ch)
            if ch == 0:
                # Pump: always 1-pt at the cached fixed duty.
                entries.append(self._fw2_1pt_entry(self._pump_duty_1pt))
            elif ch in (4, 5):
                # Fan4 / Fan5: 2-pt hardware temperature curve.
                if profile:
                    pt0, pt1 = self._fw2_reduce_to_2pt(profile)
                else:
                    pt0, pt1 = (20, 0), (35, 100)   # safe default
                entries.append(self._fw2_2pt_entry(pt0, pt1))
            else:
                # Fan1-3, Fan6: 1-pt constant at duty interpolated from profile.
                duty = self._fw2_interp_duty(profile, _DESIGN_TEMP) if profile else 70
                entries.append(self._fw2_1pt_entry(duty))

        payload = bytes([7]) + b''.join(entries)
        assert len(payload) == 51, f"fw2 payload size mismatch: {len(payload)}"
        return payload

    # --------------------------------------------------------------------------

    def set_speed_profile(self, channel, profile, **kwargs):
        channels = self._parse_channels(channel)
        curve_points = list(profile)
        if len(curve_points) < 2:
            raise ValueError('a minimum of 2 speed curve points must be configured.')
        if len(curve_points) > 7:
            raise ValueError('a maximum of 7 speed curve points may be configured.')

        with self._wake_device_context(commit_speed=True):
            self._ensure_fw_version()

            if self._fw_major >= 2:
                # Cache the profile and write the compact 51-byte fw2.x payload.
                # Read-modify-write would overflow the 54-byte USB FS packet limit
                # when all 7 channels carry 2-pt curves (71 bytes total), silently
                # truncating fan5 and fan6 data.  Using a cache-based approach with
                # mixed 1-pt/2-pt encoding keeps the payload within one USB packet.
                for chan in channels:
                    self._curve_cache[chan] = curve_points
                # Ensure target channels are in curve-percent mode (0x02) on the
                # speed-mode endpoint.  This mirrors the fw1.x path.  Without this
                # write, a channel previously set to fixed-percent mode (0x00) by
                # set_fixed_speed() would ignore the curve data.
                mode_ep = _MODE_HW_SPEED_MODE_V2
                res = self._read_data(mode_ep, _DATA_TYPE_HW_SPEED_MODE)
                device_count = res[0]
                data = bytearray(res[0:device_count + 1])
                for chan in channels:
                    data[chan + 1] = _FAN_MODE_CURVE_PERCENT
                self._write_data(mode_ep, _DATA_TYPE_HW_SPEED_MODE, data)
                self._write_data(_MODE_HW_CURVE_PERCENT_V2,
                                 _DATA_TYPE_HW_CURVE_PERCENT,
                                 self._fw2_build_curve_payload())
                return

            # ---- Firmware 1.x path -------------------------------------------
            mode_ep = _MODE_HW_SPEED_MODE
            # Set hardware speed mode to curve for target channels
            res = self._read_data(mode_ep, _DATA_TYPE_HW_SPEED_MODE)
            device_count = res[0]

            data = bytearray(res[0:device_count + 1])
            for chan in channels:
                data[chan + 1] = _FAN_MODE_CURVE_PERCENT
            self._write_data(mode_ep, _DATA_TYPE_HW_SPEED_MODE, data)

            curve_ep = _MODE_HW_CURVE_PERCENT

            # Read in data and split by device
            res = self._read_data(curve_ep, _DATA_TYPE_HW_CURVE_PERCENT)
            device_count = res[0]
            data_by_device = []

            i = 1
            for _ in range(0, device_count):
                count = res[i+1]
                start = i
                end = i + 4 * count + 2
                i = end
                data_by_device.append(res[start:end])

            # Modify data for channels in channels array
            for chan in channels:
                new_data = []

                # set temperature sensor
                new_data.append(b"\x00")

                # set number of curve points
                new_data.append(int.to_bytes(len(curve_points), length=1, byteorder="big"))

                # set curve points -- temps are in decidegrees (0.1 C resolution);
                # use round() so float inputs like 31.3 -> 313, not 312 via truncation.
                for (temp, duty) in curve_points:
                    new_data.append(int.to_bytes(round(temp * 10), length=2, byteorder="little", signed=False))
                    new_data.append(int.to_bytes(clamp(duty, 0, 100), length=2, byteorder="little", signed=False))

                # Update device data
                data_by_device[chan] = b''.join(new_data)

            out = bytes([device_count]) + b''.join(data_by_device)
            self._write_data(curve_ep, _DATA_TYPE_HW_CURVE_PERCENT, out)

    def set_fixed_speed(self, channel, duty, **kwargs):
        channels = self._parse_channels(channel)
        clamped = clamp(duty, 0, 100)

        # Duty-change guard: skip USB write entirely if every target channel is
        # already at this duty.  coolercontrold re-sends the same duty on every
        # poll when temp is stable — without this guard each poll incurs a USB
        # round-trip for no effect.
        if all(self._committed_duties.get(ch) == clamped for ch in channels):
            return

        # fw2.x uses a write-mode endpoint that commits immediately — no SLEEP needed.
        # fw1.x writes to speed endpoints that require SLEEP to commit.
        commit = self._fw_major is None or self._fw_major < 2
        with self._wake_device_context(commit_speed=commit):
            self._ensure_fw_version()
            if self._fw_major >= 2:
                # fw2.x: write directly to (0x18,0x00) using write-mode protocol.
                # Commits immediately on CLOSE_WRITE — no SLEEP required.
                # Device stays in WAKE mode; LED colors never revert.
                self._write_fan_direct({ch: clamped for ch in channels})
            else:
                # Firmware 1.x: select fixed mode, then write the fixed-percent table.
                mode_ep = _MODE_HW_SPEED_MODE
                res = self._read_data(mode_ep, _DATA_TYPE_HW_SPEED_MODE)
                device_count = res[0]

                data = bytearray(res[0:device_count + 1])
                for chan in channels:
                    data[chan + 1] = _FAN_MODE_FIXED_PERCENT
                self._write_data(mode_ep, _DATA_TYPE_HW_SPEED_MODE, data)

                fixed_ep = _MODE_HW_FIXED_PERCENT
                res = self._read_data(fixed_ep, _DATA_TYPE_HW_FIXED_PERCENT)
                device_count = res[0]
                data = bytearray(res[0:device_count * 2 + 1])
                duty_le = int.to_bytes(clamped, length=2, byteorder="little", signed=False)
                for chan in channels:
                    i = chan * 2 + 1
                    data[i: i + 2] = duty_le
                self._write_data(fixed_ep, _DATA_TYPE_HW_FIXED_PERCENT, data)

        for ch in channels:
            self._committed_duties[ch] = clamped

    def disconnect(self, **kwargs):
        """Stop animation thread before closing the HID connection."""
        self._stop_animation()
        return super().disconnect(**kwargs)

    @classmethod
    def probe(cls, handle, **kwargs):
        """Ensure we get the right interface"""

        if handle.hidinfo['interface_number'] != _INTERFACE_NUMBER:
            return

        yield from super().probe(handle, **kwargs)

    def _get_speeds(self):
        speeds = []

        res = self._read_data(_MODE_GET_SPEEDS, _DATA_TYPE_SPEEDS)

        num_speeds = res[0]
        speeds_data = res[1:1 + num_speeds * 2]
        for i in range(0, num_speeds):
            speeds.append(u16le_from(speeds_data, offset=i * 2))

        return speeds

    def _get_temps(self):
        temps = []

        res = self._read_data(_MODE_GET_TEMPS, _DATA_TYPE_TEMPS)

        num_temps = res[0]
        temp_data = res[1:1 + num_temps * 3]
        for i in range(0, num_temps):
            connected = temp_data[i * 3] == 0x00
            if connected:
                temps.append(u16le_from(temp_data, offset=i * 3 + 1) / 10)
            else:
                temps.append(None)

        return temps

    def _read_data(self, mode, data_type):
        self._send_command(_CMD_OPEN_ENDPOINT, mode)
        raw_data = self._send_command(_CMD_READ_INITIAL)
        more_raw_data = self._send_command(_CMD_READ_MORE)
        final_raw_data = self._send_command(_CMD_READ_FINAL)
        self._send_command(_CMD_CLOSE_ENDPOINT)
        if tuple(raw_data[3:5]) != data_type:
            raise ExpectationNotMet('device returned incorrect data type')

        return raw_data[5:] + more_raw_data[3:] + final_raw_data[3:]

    def _send_command(self, command, data=()):
        # self.device.write expects buf[0] to be the report number or 0 if not used
        buf = bytearray(_REPORT_LENGTH + 1)

        # buf[1] when going out is always 08
        buf[1] = 0x08

        # Indexes for the buffer
        cmd_start = 2
        data_start = cmd_start + len(command)
        data_end = data_start + len(data)

        # Fill in the buffer
        buf[cmd_start:data_start] = command
        buf[data_start:data_end] = data

        self.device.clear_enqueued_reports()
        self.device.write(buf)

        res = self.device.read(_RESPONSE_LENGTH)
        while res[0] != 0x00:
            res = self.device.read(_RESPONSE_LENGTH)
        buf = bytes(res)
        # Device occasionally sends unsolicited reports between the drain and
        # write, arriving with the correct report number (res[0]==0x00) but a
        # stale command echo (buf[1]!=command[0]).  Retry a bounded number of
        # times rather than asserting immediately, which avoids the 502 error
        # that causes coolercontrold to apply the Default Profile (pump=0 RPM).
        _retries = 8
        while buf[1] != command[0] and _retries > 0:
            res = self.device.read(_RESPONSE_LENGTH)
            while res[0] != 0x00:
                res = self.device.read(_RESPONSE_LENGTH)
            buf = bytes(res)
            _retries -= 1
        assert buf[1] == command[0], 'response does not match command'
        return buf

    @contextmanager
    def _wake_device_context(self, commit_speed=False):
        # Load persisted LED state on first use so that fan speed writes
        # re-apply the correct color even after liqctld restarts or fresh
        # device connections where self._led_payload is None.
        if self._led_payload is None:
            self._led_payload = self._load_led_state()

        was_animating = (self._anim_thread is not None and self._anim_thread.is_alive())

        # Acquire _anim_lock to serialize HID access with the animation thread.
        # Allow up to 400ms for a running frame to complete (normal frame ≤45ms at 24fps).
        # If the timeout fires the frame is overrunning (e.g. heavy CPU load) — stop the
        # animation thread so the fan control op (safety-critical) can proceed immediately.
        # Animation resumes on the next set_color() call.  The 400ms budget leaves ~150ms
        # for the WAKE + fan write before liqctld's 550ms read deadline.
        if not self._anim_lock.acquire(timeout=0.4):
            _LOGGER.warning(
                'animation frame overran 400 ms; stopping animation to unblock fan control'
            )
            if self._anim_thread and self._anim_thread.is_alive():
                self._anim_stop.set()
            if not self._anim_lock.acquire(timeout=0.5):
                _LOGGER.warning('animation thread still unresponsive after 900 ms; aborting op')
                self._anim_stop.clear()  # undo stop signal — thread will self-heal after HID timeout
                raise RuntimeError('HID device unresponsive; animation thread holding lock')
        try:
            # Always WAKE: the device must be in software mode for fan ops and LED
            # writes.  Idempotent — safe even if animation already WAKEd it.
            self._send_command(_CMD_WAKE)
            try:
                yield
            finally:
                if commit_speed:
                    # SLEEP commits fan speed: the Commander ST only reads and
                    # applies speed endpoint values when transitioning from WAKE
                    # to SLEEP.  In WAKE mode all speed writes are silently ignored
                    # by the fan controller.  Only write-path callers (set_fixed_speed,
                    # set_speed_profile, initialize) pass commit_speed=True.
                    self._send_command(_CMD_SLEEP)
                    # SLEEP reverts LED display to NVRAM. Re-enter WAKE immediately
                    # and reapply the color payload to restore the software color.
                    # Doing WAKE unconditionally here means the animation thread can
                    # write its next frame without needing to re-check first_frame.
                    self._send_command(_CMD_WAKE)
                    if was_animating:
                        # Restart thread if it was stopped by the lock-timeout path above;
                        # no-op if thread is still alive (it resumes on its next frame).
                        self._ensure_animation_thread()
                    elif self._led_payload is not None:
                        self._write_led_data(_MODE_LED_COLORS, _DATA_TYPE_LED_COLORS,
                                             self._led_payload)
                # commit_speed=False (e.g. get_status): device stays in WAKE —
                # no SLEEP, no LED blink.  Read-only ops don't need a fan commit.
        finally:
            self._anim_lock.release()
            if was_animating:
                self._ensure_animation_thread()

    def _save_led_state(self):
        """Persist current LED payload to disk for cross-session continuity."""
        try:
            os.makedirs(_LED_STATE_DIR, exist_ok=True)
            with open(_LED_STATE_FILE, 'w') as f:
                json.dump({'payload': list(self._led_payload)}, f)
        except OSError as e:
            _LOGGER.warning('could not save LED state: %s', e)

    def _load_led_state(self):
        """Load persisted LED payload from disk, or return None if not found."""
        try:
            with open(_LED_STATE_FILE) as f:
                data = json.load(f)
            payload = bytes(data['payload'])
            if payload:
                return payload
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            pass
        return None

    def _write_data(self, mode, data_type, data):
        self._read_data(mode, data_type)  # Will ensure we are writing the correct data type to avoid breakage

        self._send_command(_CMD_OPEN_ENDPOINT, mode)

        # Write data
        data_len = len(data)
        data_start_index = 0
        while (data_start_index < data_len):
            if (data_start_index == 0):
                # First 9 bytes are in use
                packet_data_len = _REPORT_LENGTH - 9

                if (data_len < packet_data_len):
                    packet_data_len = data_len

                # Num Data Length bytes + 0x05 + 0x06 + Num Data Type bytes + Num Data bytes
                buf = bytearray(2 + 2 + len(data_type) + packet_data_len)

                # Data Length value (includes data type length) - 0x03 and 0x04
                buf[0: 2] = int.to_bytes(data_len + len(data_type), length=2, byteorder="little", signed=False)
                # Data Type value - 0x07 and 0x08
                buf[4: 4 + len(data_type)] = data_type
                # Data - 0x09 onwards
                buf[4 + len(data_type):] = data[0:packet_data_len]

                self._send_command(_CMD_WRITE, buf)
                data_start_index += packet_data_len
            else:
                # First 3 bytes are in use
                packet_data_len = _REPORT_LENGTH - 3
                if data_len - data_start_index < packet_data_len:
                    packet_data_len = data_len - data_start_index

                self._send_command(_CMD_WRITE_MORE, data[data_start_index:data_start_index + packet_data_len])
                data_start_index += packet_data_len

        self._send_command(_CMD_CLOSE_ENDPOINT)

    def _write_data_bootstrap(self, mode, data_type, data):
        """Write to an endpoint without the read-verify guard in _write_data.
        Only safe during initialize() when an endpoint is known to be uninitialized."""
        self._send_command(_CMD_OPEN_ENDPOINT, mode)
        data_len = len(data)
        data_start_index = 0
        while data_start_index < data_len:
            if data_start_index == 0:
                packet_data_len = min(data_len, _REPORT_LENGTH - 9)
                buf = bytearray(2 + 2 + len(data_type) + packet_data_len)
                buf[0:2] = int.to_bytes(data_len + len(data_type), 2, 'little')
                buf[4:4 + len(data_type)] = data_type
                buf[4 + len(data_type):] = data[0:packet_data_len]
                self._send_command(_CMD_WRITE, buf)
                data_start_index += packet_data_len
            else:
                packet_data_len = min(data_len - data_start_index, _REPORT_LENGTH - 3)
                self._send_command(_CMD_WRITE_MORE,
                                   data[data_start_index:data_start_index + packet_data_len])
                data_start_index += packet_data_len
        self._send_command(_CMD_CLOSE_ENDPOINT)

    def _write_fan_direct(self, duties):
        """Write fan duties to (0x18,0x00) using write-mode endpoint protocol.

        duties: dict {channel_index: duty_pct}

        Commits immediately on CLOSE_WRITE — no SLEEP required.  Device must be in
        WAKE mode (call inside _wake_device_context).

        Protocol per iCUE usbmon capture (2026-04-17):
          OPEN_WRITE(0x18,0x00) → CMD_PREP_WRITE → WRITE_DIRECT(payload) → CLOSE_WRITE
        Payload: count(1) + count × [ch_id_le(2) + duty_%(2)]
        """
        ch_list = sorted(duties.keys())
        fan_payload = bytearray([len(ch_list)])
        for ch in ch_list:
            fan_payload += int.to_bytes(ch, 2, 'little')
            fan_payload += int.to_bytes(clamp(duties[ch], 0, 100), 2, 'little')

        self._send_command(_CMD_OPEN_ENDPOINT_WRITE, _MODE_FAN_DIRECT)
        self._send_command(_CMD_PREP_WRITE)

        data_len = len(fan_payload) + len(_DATA_TYPE_FAN_DIRECT)
        buf = bytearray(2 + 2 + len(_DATA_TYPE_FAN_DIRECT) + len(fan_payload))
        buf[0:2] = int.to_bytes(data_len, 2, 'little')
        buf[4:4 + len(_DATA_TYPE_FAN_DIRECT)] = _DATA_TYPE_FAN_DIRECT
        buf[4 + len(_DATA_TYPE_FAN_DIRECT):] = fan_payload
        self._send_command(_CMD_WRITE_DIRECT, buf)

        self._send_command(_CMD_CLOSE_ENDPOINT_WRITE)

    def _write_led_data(self, mode, data_type, data):
        """Write to an LED endpoint using 64-byte HID packets.

        Differs from _write_data() in two ways:
        1. Uses _LED_REPORT_LENGTH=64 (matching the device's USB FS HID descriptor).
           Fan speed payloads fit in 64 bytes, masking this requirement. LED color
           payloads are 699 bytes across 12 packets; 96-byte buffers silently
           truncate to 64, corrupting every packet after the first 64 bytes.
        2. Skips the read-verify guard: (0x22, 0x00) returns data type (0x07, 0x00)
           when read, not (0x12, 0x00), so _write_data()'s guard would always refuse.
        """
        self._send_led_command(_CMD_OPEN_ENDPOINT, mode)

        data_len = len(data)
        data_start_index = 0
        while data_start_index < data_len:
            if data_start_index == 0:
                packet_data_len = min(data_len, _LED_REPORT_LENGTH - 9)
                buf = bytearray(2 + 2 + len(data_type) + packet_data_len)
                buf[0:2] = int.to_bytes(data_len + len(data_type), 2, 'little')
                buf[4:4 + len(data_type)] = data_type
                buf[4 + len(data_type):] = data[0:packet_data_len]
                self._send_led_command(_CMD_WRITE, buf)
                data_start_index += packet_data_len
            else:
                packet_data_len = min(data_len - data_start_index, _LED_REPORT_LENGTH - 3)
                self._send_led_command(
                    _CMD_WRITE_MORE,
                    data[data_start_index:data_start_index + packet_data_len])
                data_start_index += packet_data_len

        self._send_led_command(_CMD_CLOSE_ENDPOINT)

    def _send_led_command(self, command, data=()):
        """Like _send_command() but uses 64-byte HID reports for LED endpoints."""
        buf = bytearray(_LED_REPORT_LENGTH + 1)
        buf[1] = 0x08
        buf[2:2 + len(command)] = command
        buf[2 + len(command):2 + len(command) + len(data)] = data

        self.device.clear_enqueued_reports()
        self.device.write(buf)

        res = self.device.read(_RESPONSE_LENGTH)
        while res[0] != 0x00:
            res = self.device.read(_RESPONSE_LENGTH)
        buf = bytes(res)
        _retries = 8
        while buf[1] != command[0] and _retries > 0:
            res = self.device.read(_RESPONSE_LENGTH)
            while res[0] != 0x00:
                res = self.device.read(_RESPONSE_LENGTH)
            buf = bytes(res)
            _retries -= 1
        assert buf[1] == command[0], 'response does not match command'
        return buf

    def _fan_to_channel(self, fan):
        if self._has_pump:
            return fan
        else:
            # On devices without a pump, channel 0 is fan 1
            return fan - 1

    def _parse_channels(self, channel):
        if self._has_pump and channel == 'pump':
            return [0]
        elif channel == "fans":
            return [self._fan_to_channel(x) for x in range(1, _FAN_COUNT + 1)]
        elif channel.startswith("fan") and channel[3:].isnumeric() and 0 < int(channel[3:]) <= _FAN_COUNT:
            return [self._fan_to_channel(int(channel[3:]))]
        else:
            fan_names = ['fan' + str(i) for i in range(1, _FAN_COUNT + 1)]
            fan_names_part = '", "'.join(fan_names)
            if self._has_pump:
                fan_names.insert(0, "pump")
            raise ValueError(f'unknown channel, should be one of: "{fan_names_part}" or "fans"')

    def set_screen(self, channel, mode, value, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice
