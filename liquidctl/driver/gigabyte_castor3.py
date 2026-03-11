"""liquidctl driver for Gigabyte Aorus Waterforce X II 360 AIO coolers.

Supported devices:

- Gigabyte Aorus Waterforce X II 360 (Castor3 controller)

The Castor3 controller uses a HID interface with report ID 0x99. OUT packets
are 6143 bytes (zero-padded after the payload); IN packets are 255 bytes. The
command byte is always byte[0] after stripping the report ID.

Protocol reference and test results are available in castor3_protocol.md and
test_results.md in the project repository.

Copyright liquidctl contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import glob
import logging
import os
import signal
import struct
import subprocess
import sys
import time

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_SENSOR_PID_FILE = "/tmp/castor3_sensor_push.pid"

# ── Transport constants ──────────────────────────────────────────────────────

REPORT_ID = 0x99
OUT_SIZE = 6143  # HID OUT payload size (after report ID)
IN_SIZE = 255  # HID IN report size
CHUNK_SIZE = 6141  # file bytes per f2 chunk (OUT_SIZE - 2 for cmd+len byte)

# ── Init blob ────────────────────────────────────────────────────────────────

_C9_INIT_BLOB = bytes([0xC9, 0x08, 0x64, 0x09, 0xCC, 0xCC])

# ── Fan presets ──────────────────────────────────────────────────────────────

_FAN_PRESETS = {
    "default": 0x02,
    "zero-rpm": 0x07,
    "quiet": 0x06,
    "balanced": 0x00,
    "performance": 0x05,
    "turbo": 0x04,
}

_FAN_PRESET_NAMES = {v: k for k, v in _FAN_PRESETS.items()}

# dd response byte meanings (different from e5 preset IDs)
_FAN_DD_MODE_NAMES = {
    0x01: "customized",
    0x05: "preset",
}

# ── Pump modes ───────────────────────────────────────────────────────────────

_PUMP_MODES = {
    "balanced": 0x00,
    "turbo": 0x04,
}

_PUMP_MODE_NAMES = {v: k for k, v in _PUMP_MODES.items()}

# ── LED effects ──────────────────────────────────────────────────────────────

_LED_EFFECTS = {
    "static": {"style": 0x01, "b4": 0x02, "b5": 0x01, "colors": "single"},
    "pulse": {"style": 0x02, "b4": 0x02, "b5": 0x01, "colors": "single"},
    "flash": {"style": 0x04, "b4": 0x02, "b5": 0x01, "colors": "single"},
    "double-flash": {"style": 0x05, "b4": 0x02, "b5": 0x01, "colors": "single"},
    "cycle": {"style": 0x03, "b4": 0x02, "b5": 0x01, "colors": "none"},
    "gradient": {"style": 0x06, "b4": "brightness", "b5": 0x01, "colors": "single"},
    "color-shift": {"style": 0x07, "b4": 0x08, "b5": 0x02, "colors": "palette8"},
    "wave": {"style": 0x08, "b4": 0x02, "b5": 0x01, "colors": "none"},
    "rainbow": {"style": 0x0A, "b4": 0x02, "b5": 0x01, "colors": "none"},
    "tri-color": {"style": 0x0B, "b4": 0x02, "b5": 0x01, "colors": "palette3"},
    "spin": {"style": 0x0C, "b4": 0x02, "b5": 0x01, "colors": "palette3"},
    "switch": {"style": 0x0D, "b4": 0x02, "b5": 0x01, "colors": "palette2"},
    "off": {"style": 0x01, "b4": 0x02, "b5": 0x01, "colors": "single"},
}

_PALETTE_MAX = {"palette2": 2, "palette3": 3, "palette8": 8}

_LED_DEFAULT_PALETTES = {
    "color-shift": [
        (0xFF, 0x00, 0x00), (0xFF, 0x72, 0x00), (0xFF, 0xFF, 0x00), (0x00, 0xFF, 0x00),
        (0x00, 0xFF, 0xFF), (0x00, 0x00, 0xFF), (0xFF, 0x00, 0xFF), (0xFF, 0x80, 0x80),
    ],
    "tri-color": [(0x00, 0x00, 0xFF), (0x7D, 0x00, 0xFF), (0xFF, 0x00, 0xFF)],
    "spin": [(0xFF, 0x00, 0xFE), (0x00, 0xFF, 0xFB), (0xFF, 0xFF, 0x00)],
    "switch": [(0xFF, 0x00, 0xFE), (0x00, 0xFF, 0xFB)],
}

_LED_SPEED_MIN = 1
_LED_SPEED_MAX = 5
_LED_BRIGHTNESS_MIN = 1
_LED_BRIGHTNESS_MAX = 10

# ── Fan curve constants ──────────────────────────────────────────────────────

_MAX_FAN_CURVE_POINTS = 5
_MIN_FAN_CURVE_POINTS = 2
_MAX_FAN_RPM = 3000
_MAX_FAN_CURVE_TEMP = 100

# ── Metric one-hot offsets (Enthusiast 04/05) ────────────────────────────────

_METRIC_OFFSET = {
    "fan": 0,
    "pump": 1,
    "cpu-clock": 2,
    "cpu-temp": 3,
    "cpu-usage": 4,
    "cpu-power": 5,
}

# ── Overlay metric offsets (image/gif/video System Info overlay) ─────────────

_OVERLAY_METRIC_OFFSET = {
    "cpu-clock": 0,
    "cpu-temp": 1,
    "cpu-usage": 2,
    "cpu-power": 3,
}

# ── Display mode IDs ─────────────────────────────────────────────────────────

_DISPLAY_MODE_ID = {
    "enthusiast1": 0x01,
    "enthusiast2": 0x02,
    "enthusiast3": 0x03,
    "enthusiast4": 0x04,
    "enthusiast5": 0x05,
    "image": 0x06,
    "gif": 0x07,
    "video": 0x08,
}

_DISPLAY_MODE_NAMES = {v: k for k, v in _DISPLAY_MODE_ID.items()}

# ── Session numbers ──────────────────────────────────────────────────────────

_SESSION_N = {
    "enthusiast1": 0x01,
    "enthusiast2": 0x02,
    "enthusiast3": 0x03,
    "enthusiast4": 0x04,
    "enthusiast5": 0x05,
    "image": 0x06,
    "gif": 0x07,
    "video": 0x08,
    "carousel": 0x09,
}


def _quoted(*names):
    return ", ".join(map(repr, names))


def _one_hot(metric):
    """Build a 6-byte one-hot metric selector."""
    metric = metric.lower()
    off = _METRIC_OFFSET.get(metric)
    if off is None:
        raise ValueError(
            f"unknown metric {metric!r}, should be one of: {_quoted(*_METRIC_OFFSET)}"
        )
    buf = [0] * 6
    buf[off] = 1
    return buf


def _parse_color(color):
    """Validate and return a 3-element color tuple."""
    if len(color) != 3:
        raise ValueError(f"expected 3-element color, got {len(color)} elements")
    return tuple(clamp(c, 0, 255) for c in color)


def _read_cpu_temp():
    """Read CPU package/die temperature from kernel hwmon.

    Scans hwmon devices for known CPU temperature drivers:
      - k10temp / zenpower  (AMD: prefer temp2=Tdie over temp1=Tctl)
      - coretemp            (Intel: temp1 is package temp)
      - cpu_thermal         (ARM / generic DT thermal)
      - acpitz              (ACPI thermal zone, fallback)

    Returns temperature in C as int, or None if unavailable.
    """
    # Priority order: prefer specific CPU drivers over generic thermal zones
    _DRIVER_PRIORITY = {
        "k10temp": 1,
        "zenpower": 1,
        "coretemp": 2,
        "cpu_thermal": 3,
        "acpitz": 4,
    }

    best = None
    best_prio = 999

    for hwmon_dir in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        try:
            with open(f"{hwmon_dir}/name") as f:
                name = f.read().strip()
        except Exception:
            continue

        prio = _DRIVER_PRIORITY.get(name)
        if prio is None or prio >= best_prio:
            continue

        # AMD k10temp/zenpower: prefer temp2 (Tdie) over temp1 (Tctl spikes)
        # Intel coretemp: temp1 is package temp
        # Others: try temp1
        if name in ("k10temp", "zenpower"):
            sensors = ["temp2_input", "temp1_input"]
        else:
            sensors = ["temp1_input"]

        for sensor in sensors:
            try:
                with open(f"{hwmon_dir}/{sensor}") as f:
                    val = int(f.read().strip()) // 1000
                if 0 < val < 150:  # sanity check
                    best = val
                    best_prio = prio
                    break
            except (FileNotFoundError, ValueError):
                continue

    return best


class GigabyteCastor3(UsbHidDriver):
    """liquidctl driver for Gigabyte Aorus Waterforce X II 360 (Castor3).

    This device has a 320x320 LCD screen, a pump, and a fan header, all
    controlled through HID report 0x99. The device requires a continuous
    sensor push (e0 packets) to update its Enthusiast mode displays.

    Supported features:

    - Fan presets and custom fan curves
    - Pump mode (balanced / turbo)
    - LED ring effects (12 modes, single-color and palette)
    - Display rotation (30 degree steps)
    - 5 Enthusiast display modes with configurable metrics and colors
    - Custom image/gif/video display with ROM upload
    - System info overlay on image modes
    - Text overlay rendering (requires Pango/Cairo or Pillow)
    - Carousel mode (cycle through display modes)
    - ROM slot management (list, free space, delete)
    - Sensor readout (CPU temp, fan RPM, pump RPM)
    """

    _MATCHES = [
        (
            0x0414,  # Gigabyte
            0x7A5E,  # Aorus Waterforce X II 360 (Castor3)
            "Gigabyte Aorus Waterforce X II 360",
            {},
        ),
    ]

    def __init__(self, device, description, **kwargs):
        super().__init__(device, description, **kwargs)
        self._pump_mode = _PUMP_MODES["balanced"]

    # ── Low-level transport ──────────────────────────────────────────────

    def _write(self, payload):
        """Write OUT packet: prepend report ID, zero-pad to OUT_SIZE."""
        buf = bytearray(OUT_SIZE + 1)
        buf[0] = REPORT_ID
        buf[1 : 1 + len(payload)] = payload
        self.device.write(bytes(buf))

    def _read(self, timeout_ms=2000):
        """Read one IN packet, stripping report ID if present."""
        try:
            data = self.device.read(IN_SIZE, timeout=timeout_ms)
        except Exception:
            return b""
        if not data:
            return b""
        b = bytes(data)
        if b and b[0] == REPORT_ID:
            b = b[1:]
        return b

    def _cmd(self, payload, expected_cmd=None, timeout_s=2.0):
        """Write payload, poll for response matching expected command byte."""
        expected = expected_cmd if expected_cmd is not None else payload[0]
        self._write(payload)
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            b = self._read(timeout_ms=100)
            if b and b[0] == expected:
                return b
            if not b:
                time.sleep(0.005)
        _LOGGER.debug("timed out waiting for response 0x%02x", expected)
        return b""

    def _drain(self, max_packets=30):
        """Drain queued IN packets."""
        for _ in range(max_packets):
            try:
                data = self.device.read(IN_SIZE, timeout=50)
                if not data:
                    break
            except Exception:
                break

    def _wait_idle(self, timeout_s=10.0):
        """Poll c1 until device is idle (busy byte = 0)."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            resp = self._cmd(b"\xc1\x00")
            if resp and resp[1] == 0x00:
                return True
            time.sleep(0.1)
        _LOGGER.warning("device did not become idle within timeout")
        return False

    def _wait_upload_done(self, timeout_s=60.0):
        """Poll c2 until upload progress = 100% (0x64)."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            resp = self._cmd(b"\xc2\x00")
            if resp and resp[1] == 0x64:
                return True
            time.sleep(0.2)
        _LOGGER.warning("upload did not complete within timeout")
        return False

    def _session_open(self, n):
        """Send e7 session open."""
        self._write(bytes([0xE7, n]))
        time.sleep(0.05)

    def _ac_begin(self):
        """Begin ac edit bracket."""
        self._write(b"\xac\x01")
        time.sleep(0.05)

    def _ac_end(self):
        """End ac edit bracket (commit)."""
        self._write(b"\xac\x00")
        time.sleep(0.05)

    def _e2_send(self, payload):
        """Send e2 metric configuration payload (without report ID)."""
        self._write(bytes(payload))
        time.sleep(0.05)

    def _e4_send(self, mode, colors):
        """Send e4 panel color command. colors: list of (R, G, B) tuples."""
        buf = bytearray([0xE4, mode])
        for r, g, b in colors:
            buf += bytes([r & 0xFF, g & 0xFF, b & 0xFF])
        self._write(bytes(buf))
        time.sleep(0.05)

    # ── liquidctl driver API ─────────────────────────────────────────────

    def initialize(self, pump_mode="balanced", **kwargs):
        """Initialize the device and return firmware version.

        Replicates the GCC startup sequence: d6/de handshake, c9 init blob,
        CPU model push, fan state query, initial sensor push, and device
        state queries.

        pump_mode: 'balanced' or 'turbo' (default: 'balanced').

        Returns a list of (key, value, unit) tuples.
        """
        pump_mode = pump_mode.lower()
        if pump_mode not in _PUMP_MODES:
            raise ValueError(
                f"unknown pump mode, should be one of: {_quoted(*_PUMP_MODES)}"
            )
        self._pump_mode = _PUMP_MODES[pump_mode]

        self.device.clear_enqueued_reports()

        # Phase 1 — d6/de handshake
        self._cmd(b"\xd6\x00", expected_cmd=0xD6, timeout_s=0.5)
        self._cmd(b"\xd6\x00", expected_cmd=0xD6, timeout_s=0.5)
        resp_de = self._cmd(b"\xde\x00", expected_cmd=0xDE, timeout_s=0.5)
        self._cmd(b"\xd6\x00", expected_cmd=0xD6, timeout_s=0.5)

        fw_version = resp_de[1] if resp_de and len(resp_de) >= 2 else 0
        _LOGGER.debug("firmware/protocol version: %d", fw_version)

        # Phase 2 — c9 init blob x9
        for _ in range(9):
            self._write(_C9_INIT_BLOB)
            time.sleep(0.02)
        self._drain()

        # Phase 3 — push CPU model string
        self._push_cpu_model()

        # Phase 4 — fan state query
        resp_dd = self._cmd(b"\xdd\x00")
        fan_mode_byte = resp_dd[1] if resp_dd and len(resp_dd) >= 2 else 0xFF
        _LOGGER.debug("fan controller mode byte: 0x%02x", fan_mode_byte)
        self._cmd(b"\xd9\x01")

        # Phase 5 — initial sensor push + pump/fan poll
        self._push_sensors_once()
        self._cmd(b"\xda\x00")

        # Phase 6 — query device state
        self._cmd(b"\xe8\x00")
        self._cmd(b"\xff\x00", expected_cmd=0xFF, timeout_s=0.5)
        self._cmd(b"\xad\x00", expected_cmd=0xAD, timeout_s=0.5)
        self._cmd(b"\xdf\x00")
        self._cmd(bytes([0xEA, 0x01]))
        self._cmd(b"\xab\x00")

        status = [("Firmware version", fw_version, "")]

        pump_name = _PUMP_MODE_NAMES.get(self._pump_mode, "unknown")
        _LOGGER.info("pump mode set to %s during initialization", pump_name)

        # Start the background sensor push daemon so Enthusiast mode
        # displays stay live without requiring continuous CLI polling.
        self._start_sensor_daemon()

        return status

    def get_status(self, direct_access=False, **kwargs):
        """Get a status report.

        Returns a list of (key, value, unit) tuples with CPU temperature,
        CPU usage, CPU clock, fan RPM, pump RPM, fan controller mode, and
        pump mode.
        """
        status = []

        # CPU temp from system hwmon (k10temp or zenpower)
        cpu_temp = _read_cpu_temp()
        if cpu_temp is not None:
            status.append(("CPU temperature", cpu_temp, "\u00b0C"))

        # CPU usage from /proc/stat
        cpu_usage = self._read_cpu_usage()
        status.append(("CPU usage", cpu_usage, "%"))

        # CPU clock from sysfs
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq") as f:
                cpu_clk = int(f.read().strip()) // 1000
            status.append(("CPU clock", cpu_clk, "MHz"))
        except Exception:
            pass

        # Push one sensor sample so device has fresh data
        self._push_sensors_once()

        # Fan + pump RPM from da query
        resp = self._cmd(b"\xda\x00")
        if resp and len(resp) >= 6:
            fan_rpm = struct.unpack_from("<H", resp, 1)[0]
            pump_rpm = struct.unpack_from("<H", resp, 4)[0]
            status.append(("Fan speed", fan_rpm, "rpm"))
            status.append(("Pump speed", pump_rpm, "rpm"))

        # Fan controller mode from dd
        # dd returns: 0x01=customized, or the preset ID directly (0x00=balanced, etc.)
        resp_dd = self._cmd(b"\xdd\x00")
        if resp_dd and len(resp_dd) >= 2:
            dd_byte = resp_dd[1]
            fan_mode_name = _FAN_DD_MODE_NAMES.get(
                dd_byte, _FAN_PRESET_NAMES.get(dd_byte, f"0x{dd_byte:02x}")
            )
            status.append(("Fan mode", fan_mode_name, ""))

        # Pump mode (software-tracked)
        pump_name = _PUMP_MODE_NAMES.get(self._pump_mode, "unknown")
        status.append(("Pump mode", pump_name, ""))

        # Display mode from e8
        resp_e8 = self._cmd(b"\xe8\x00")
        if resp_e8 and len(resp_e8) >= 2:
            disp_name = _DISPLAY_MODE_NAMES.get(resp_e8[1], f"0x{resp_e8[1]:02x}")
            status.append(("Display mode", disp_name, ""))

        return status

    # ── Fan control ──────────────────────────────────────────────────────

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set fan to a fixed speed.

        channel: 'fan' — the fan header connected to the AIO.

        duty: 0-100 percentage. Converted to RPM (linear scale, 3000 RPM max)
              and written as a flat two-point custom curve spanning 0-100C.

        The e6 curve format is: [temp_C] [rpm_hi] [rpm_lo] per point,
        where RPM is big-endian uint16.
        """
        channel = channel.lower()
        if channel != "fan":
            raise ValueError(f"unknown channel {channel!r}, should be 'fan'")

        duty = clamp(duty, 0, 100)
        rpm = round(duty * _MAX_FAN_RPM / 100)

        _LOGGER.info("setting fan to fixed %d%% (%d rpm)", duty, rpm)

        # Read current curve (matches GCC behavior)
        self._cmd(b"\xd9\x01")
        time.sleep(0.05)

        # Select Customized preset (ID 0x01)
        self._write(b"\xe5\x01\x01")
        time.sleep(0.05)
        self._write(b"\xe5\x02" + bytes([self._pump_mode]))
        time.sleep(0.05)

        # Write flat curve: two points at same RPM across full temp range
        payload = bytearray([0x00, 0x01])
        payload += bytes([0x00, (rpm >> 8) & 0xFF, rpm & 0xFF])
        payload += bytes([0x64, (rpm >> 8) & 0xFF, rpm & 0xFF])
        payload += b"\x00" * (17 - 6)
        self._write(b"\xe6" + bytes(payload))
        time.sleep(0.1)

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set fan to follow a temperature-RPM speed profile.

        channel: 'fan'

        profile: list of (temperature C, duty %) pairs, sorted by
                 temperature. 2-5 points supported. Duty is converted to RPM
                 linearly (0% = 0 RPM, 100% = 3000 RPM).
        """
        channel = channel.lower()
        if channel != "fan":
            raise ValueError(f"unknown channel {channel!r}, should be 'fan'")

        profile = list(profile)
        if not (_MIN_FAN_CURVE_POINTS <= len(profile) <= _MAX_FAN_CURVE_POINTS):
            raise ValueError(
                f"need {_MIN_FAN_CURVE_POINTS}-{_MAX_FAN_CURVE_POINTS} points, "
                f"got {len(profile)}"
            )

        profile = sorted(profile, key=lambda p: p[0])
        for temp, duty in profile:
            rpm = clamp(round(int(duty) * _MAX_FAN_RPM / 100), 0, _MAX_FAN_RPM)
            _LOGGER.info(
                "setting fan curve point: %dC -> %d%% (%d rpm)",
                int(temp), int(duty), rpm,
            )

        # Read current curve (GCC behavior)
        self._cmd(b"\xd9\x01")
        time.sleep(0.05)

        # Select Customized preset
        self._write(b"\xe5\x01\x01")
        time.sleep(0.05)
        self._write(b"\xe5\x02" + bytes([self._pump_mode]))
        time.sleep(0.05)

        # Write curve: e6 [zone=0x00] [sub=0x01] [temp rpm_hi rpm_lo] x N
        payload = bytearray([0x00, 0x01])
        for temp, duty in profile:
            temp = clamp(int(temp), 0, _MAX_FAN_CURVE_TEMP)
            rpm = clamp(round(int(duty) * _MAX_FAN_RPM / 100), 0, _MAX_FAN_RPM)
            payload += bytes([temp, (rpm >> 8) & 0xFF, rpm & 0xFF])
        payload += b"\x00" * (17 - len(profile) * 3)
        self._write(b"\xe6" + bytes(payload))
        time.sleep(0.1)

    def fan_set_preset(self, preset, pump=None):
        """Set fan to a named preset.

        preset: 'default', 'zero-rpm', 'quiet', 'balanced', 'performance', 'turbo'
        pump: optionally set pump mode simultaneously ('balanced' or 'turbo')

        Protocol: e5 01 [fan_preset_id] -> e5 02 [pump_mode_id]
        Both are always sent together; cannot change one without the other.
        """
        preset = preset.lower()
        if preset not in _FAN_PRESETS:
            raise ValueError(
                f"unknown fan preset {preset!r}, should be one of: "
                f"{_quoted(*_FAN_PRESETS)}"
            )
        if pump is not None:
            pump = pump.lower()
            if pump not in _PUMP_MODES:
                raise ValueError(
                    f"unknown pump mode {pump!r}, should be one of: "
                    f"{_quoted(*_PUMP_MODES)}"
                )
            self._pump_mode = _PUMP_MODES[pump]

        pid = _FAN_PRESETS[preset]
        self._drain()
        self._write(b"\xe5\x01" + bytes([pid]))
        time.sleep(0.05)
        self._write(b"\xe5\x02" + bytes([self._pump_mode]))
        _LOGGER.info("fan preset -> %s, pump -> %s", preset,
                      _PUMP_MODE_NAMES.get(self._pump_mode, "unknown"))

    def fan_read_curve(self):
        """Read the current custom fan curve from device.

        Returns list of (temp_C, rpm) tuples.

        NOTE: Only returns meaningful data when Customized mode is active.
        Named presets use firmware-internal curves; d9 returns stale data.
        """
        resp = self._cmd(b"\xd9\x01")
        if not resp or len(resp) < 4:
            return []
        pts = []
        off = 3
        while off + 2 < len(resp):
            temp = resp[off]
            rpm = (resp[off + 1] << 8) | resp[off + 2]
            if temp == 0 and rpm == 0 and off > 3:
                break
            pts.append((temp, rpm))
            off += 3
        return pts

    # ── Pump control ─────────────────────────────────────────────────────

    def pump_set(self, mode, fan="default"):
        """Set pump mode. Fan preset must be re-sent simultaneously.

        mode: 'balanced' or 'turbo'
        fan: fan preset to apply simultaneously (default: 'default')
        """
        mode = mode.lower()
        if mode not in _PUMP_MODES:
            raise ValueError(
                f"unknown pump mode {mode!r}, should be one of: "
                f"{_quoted(*_PUMP_MODES)}"
            )
        self._pump_mode = _PUMP_MODES[mode]
        self.fan_set_preset(fan, pump=mode)

    # ── LED control ──────────────────────────────────────────────────────

    def set_color(self, channel, mode, colors, speed="normal", **kwargs):
        """Set the LED ring color mode.

        channel: 'led' — the LED ring on the pump head.

        mode: one of 'static', 'pulse', 'flash', 'double-flash', 'cycle',
              'gradient', 'color-shift', 'wave', 'rainbow', 'tri-color',
              'spin', 'switch', 'off'.

        colors: list of [R, G, B] color tuples.

        speed: 'slowest'|'slower'|'normal'|'faster'|'fastest' (default: 'normal')

        Additional kwargs:
            brightness: 1-10 (default: 10)
        """
        mode = mode.lower()
        if mode not in _LED_EFFECTS:
            raise ValueError(
                f"unknown LED mode {mode!r}, should be one of: "
                f"{_quoted(*_LED_EFFECTS)}"
            )

        speed_names = {"slowest": 1, "slower": 2, "normal": 3, "faster": 4, "fastest": 5}
        speed_val = speed_names.get(speed.lower(), 3) if isinstance(speed, str) else clamp(speed, 1, 5)
        brightness = clamp(
            kwargs.get("brightness", _LED_BRIGHTNESS_MAX),
            _LED_BRIGHTNESS_MIN, _LED_BRIGHTNESS_MAX,
        )

        cfg = _LED_EFFECTS[mode]
        style = cfg["style"]
        b4 = cfg["b4"]
        b5 = cfg["b5"]
        ctype = cfg["colors"]
        speed_wire = 0 if mode == "off" else speed_val * 20

        if b4 == "brightness":
            b4 = brightness

        colors = list(colors)

        # c9 — effect select + params
        self._write(bytes([0xC9, style, speed_wire, brightness, b4, b5]))

        # cd — primary color (single-color effects)
        if ctype == "single":
            if not colors:
                color = (0xFF, 0x66, 0x00)
            else:
                color = _parse_color(colors[0])
            self._write(bytes([0xCD, color[0], color[1], color[2]]))

        # b0..b3 — palette (2 colors per register, padded to 8)
        elif ctype in _PALETTE_MAX:
            n = _PALETTE_MAX[ctype]
            defaults = _LED_DEFAULT_PALETTES.get(mode, [(0xFF, 0x00, 0x00)] * n)
            palette = [_parse_color(c) for c in colors[:n]] if colors else list(defaults)
            while len(palette) < 8:
                palette.append(palette[-1])
            for i, reg in enumerate([0xB0, 0xB1, 0xB2, 0xB3]):
                c1, c2 = palette[i * 2], palette[i * 2 + 1]
                self._write(bytes([reg, style, c1[0], c1[1], c1[2],
                                   c2[0], c2[1], c2[2], 0x00]))

        # b6 — commit
        self._write(bytes([0xB6]))
        _LOGGER.info("LED -> %s, speed=%d, brightness=%d", mode, speed_val, brightness)

    def led_get(self, slot=1):
        """Get LED color for slot (1=inner, 2=outer).

        Returns (R, G, B) tuple from ea hardware register.
        Note: may return stale color if effect was set since last ea write.
        """
        resp = self._cmd(bytes([0xEA, slot]))
        if not resp or len(resp) < 5:
            return (0, 0, 0)
        return (resp[2], resp[3], resp[4])

    def led_effect_get(self):
        """Get LED effect state from ab hardware register.

        Returns dict with 'speed' and 'brightness' values.
        """
        resp = self._cmd(b"\xab\x00")
        if not resp or len(resp) < 3:
            return {"speed": 0xFF, "brightness": 0xFF}
        return {"speed": resp[1], "brightness": resp[2]}

    # ── Display rotation ─────────────────────────────────────────────────

    def set_rotation(self, degrees):
        """Set LCD rotation. 0-330 degrees in 30 degree steps.

        Persists across power cycles. No session or commit needed.
        """
        degrees = int(degrees) % 360
        if degrees % 30 != 0:
            raise ValueError(f"rotation must be a multiple of 30 (got {degrees})")
        step = degrees // 30
        self._write(bytes([0xCE, step]))
        _LOGGER.info("rotation -> %d degrees (step 0x%02x)", degrees, step)

    # ── Display mode query ───────────────────────────────────────────────

    def display_query(self):
        """Query current display mode via e8.

        Returns dict with 'id' (int) and 'mode' (str).
        """
        resp = self._cmd(b"\xe8\x00")
        mid = resp[1] if resp else 0xFF
        return {"id": mid, "mode": _DISPLAY_MODE_NAMES.get(mid, f"unknown(0x{mid:02x})")}

    # ── Device info queries ──────────────────────────────────────────────

    def device_state(self):
        """Query low-level device state via d6.

        Returns dict with 'active' (bool), 'session' (int), 'slot' (int).
        """
        resp = self._cmd(b"\xd6\x00", expected_cmd=0xD6)
        if not resp or len(resp) < 4:
            return {}
        return {"active": resp[1] == 0x01, "session": resp[2], "slot": resp[3]}

    def firmware_version(self):
        """Query firmware/protocol version via de.

        Returns version int (observed: 2).
        """
        resp = self._cmd(b"\xde\x00", expected_cmd=0xDE)
        return resp[1] if resp and len(resp) >= 2 else 0xFF

    # ── set_screen — LCD display modes ───────────────────────────────────

    def set_screen(self, channel, mode, value, **kwargs):
        """Set the LCD screen mode.

        channel: 'lcd'

        mode: one of 'enthusiast1'-'enthusiast5', 'rotation', 'carousel',
              'image', 'gif', 'video'.

        See individual _set_* methods for value format documentation.
        """
        mode = mode.lower()

        if mode == "rotation":
            self.set_rotation(value)
        elif mode == "carousel":
            self._set_carousel(value if isinstance(value, dict) else {})
        elif mode in ("image", "gif", "video"):
            self._set_image_mode(mode)
        elif mode.startswith("enthusiast"):
            n = int(mode[-1])
            self._set_enthusiast(n, value if isinstance(value, dict) else {})
        else:
            raise ValueError(
                f"unknown screen mode {mode!r}, should be one of: "
                "'enthusiast1'-'enthusiast5', 'rotation', 'carousel', "
                "'image', 'gif', 'video'"
            )

    # ── Enthusiast display modes ─────────────────────────────────────────

    def _set_enthusiast(self, n, value):
        """Configure one of the 5 Enthusiast display modes."""
        self._drain()
        self._session_open(n)
        self._ac_begin()

        if n == 1:
            self._enthusiast1(value)
        elif n == 2:
            self._enthusiast2(value)
        elif n == 3:
            self._enthusiast3(value)
        elif n == 4:
            self._enthusiast4(value)
        elif n == 5:
            self._enthusiast5(value)
        else:
            raise ValueError(f"unknown enthusiast mode {n}")

        self._ac_end()
        _LOGGER.info("set enthusiast mode %d", n)

    def _enthusiast1(self, v):
        """Enthusiast 01 — single gauge.

        e2 bytes: [3]=clock, [4]=temp, [5]=usage, [6]=power
        """
        e2 = bytearray(OUT_SIZE)
        e2[0] = 0xE2
        e2[3] = int(v.get("clock", True))
        e2[4] = int(v.get("temp", True))
        e2[5] = int(v.get("usage", True))
        e2[6] = int(v.get("power", True))
        self._e2_send(e2)
        color = v.get("color", (0x00, 0xFF, 0xFF))
        self._e4_send(0x01, [_parse_color(color)])

    def _enthusiast2(self, v):
        """Enthusiast 02 — arc gauge with model name.

        e2 bytes: [3]=clock, [4]=temp, [5]=usage
        ae: 0x00=no model name, 0x01=show model name
        """
        e2 = bytearray(OUT_SIZE)
        e2[0] = 0xE2
        e2[3] = int(v.get("clock", True))
        e2[4] = int(v.get("temp", True))
        e2[5] = int(v.get("usage", True))
        self._e2_send(e2)

        model_name = v.get("model_name", True)
        self._write(bytes([0xAE, 0x01 if model_name else 0x00]))
        time.sleep(0.05)

        colors = v.get("colors", [(0x00, 0xFF, 0xFF), (0xFF, 0x80, 0x00)])
        self._e4_send(0x02, [_parse_color(c) for c in colors[:2]])

    def _enthusiast3(self, v):
        """Enthusiast 03 — three-panel layout.

        e2 bytes: [3]=A_temp, [4]=A_clock, [7]=B_fan, [8]=B_pump,
                  [15]=0x01 marker, [16]=C_temp, [17]=C_clock,
                  [18]=C_usage, [19]=C_power
        """
        e2 = bytearray(OUT_SIZE)
        e2[0] = 0xE2

        pa = v.get("panel_a", (True, True))
        e2[3] = int(pa[0])
        e2[4] = int(pa[1])

        pb = v.get("panel_b", (True, True))
        e2[7] = int(pb[0])
        e2[8] = int(pb[1])

        e2[15] = 0x01  # constant marker

        pc = v.get("panel_c", (True, True, False, False))
        e2[16] = int(pc[0])
        e2[17] = int(pc[1])
        e2[18] = int(pc[2]) if len(pc) > 2 else 0
        e2[19] = int(pc[3]) if len(pc) > 3 else 0

        self._e2_send(e2)

        colors = v.get(
            "colors",
            [(0x00, 0xFF, 0xFF), (0xFF, 0x00, 0x80), (0x00, 0x80, 0xFF)],
        )
        self._e4_send(0x03, [_parse_color(c) for c in colors[:3]])

    def _enthusiast4(self, v):
        """Enthusiast 04 — four quadrants, each one-hot metric.

        e2 bytes: [1:7]=Q1, [7:13]=Q2, [13:19]=Q3, [19:25]=Q4
        """
        e2 = bytearray(OUT_SIZE)
        e2[0] = 0xE2
        e2[1:7] = _one_hot(v.get("q1", "cpu-temp"))
        e2[7:13] = _one_hot(v.get("q2", "cpu-usage"))
        e2[13:19] = _one_hot(v.get("q3", "fan"))
        e2[19:25] = _one_hot(v.get("q4", "pump"))
        self._e2_send(e2)

        colors = v.get("colors", [(0x00, 0xFF, 0xFF)] * 4)
        self._e4_send(0x04, [_parse_color(c) for c in colors[:4]])

    def _enthusiast5(self, v):
        """Enthusiast 05 — ring gauge + center value.

        e2 bytes: [1:7]=center metric, [7:13]=ring metric
        e4 colors: [0]=center, [1]=ring
        """
        e2 = bytearray(OUT_SIZE)
        e2[0] = 0xE2
        e2[1:7] = _one_hot(v.get("center", "cpu-temp"))
        e2[7:13] = _one_hot(v.get("ring", "fan"))
        self._e2_send(e2)

        colors = v.get("colors", [(0x00, 0xFF, 0xFF), (0xFF, 0xFF, 0x00)])
        self._e4_send(0x05, [_parse_color(c) for c in colors[:2]])

    # ── Image / Gif / Video modes ────────────────────────────────────────

    def _set_image_mode(self, mode="image"):
        """Switch to Custom Image / Gif / Video display mode."""
        session = _SESSION_N.get(mode, _SESSION_N["image"])
        mode_id = _DISPLAY_MODE_ID.get(mode, 0x06)
        self._drain()
        self._session_open(session)
        self._write(bytes([0xE8, mode_id]))
        time.sleep(0.1)
        _LOGGER.info("display mode -> %s", mode)

    # ── ROM operations ───────────────────────────────────────────────────

    def rom_free(self):
        """Returns free ROM bytes."""
        resp = self._cmd(b"\xfa\x42")
        if not resp or len(resp) < 4:
            return 0
        kb_blocks = struct.unpack_from("<H", bytes(resp), 2)[0]
        return kb_blocks * 1024

    def rom_list(self):
        """Enumerate ROM slots and their files.

        Returns list of dicts: [{'slot': int, 'type': str, 'files': [str]}]
        """
        slots = []
        for slot in range(1, 13):
            resp = self._cmd(bytes([0xF4, slot, 0x00]))
            file_count = resp[2] if resp and len(resp) >= 3 else 0
            if file_count == 0:
                continue
            filenames = []
            for page in range(32):
                r = self._cmd(bytes([0xF5, slot, page, 0x00]))
                if not r or len(r) < 5 or r[4] == 0:
                    break
                name_len = r[4]
                name = r[5 : 5 + name_len].decode("latin1", errors="replace").rstrip("\x00")
                if name and name not in filenames and all(c >= " " and c != "\xff" for c in name):
                    filenames.append(name)
            type_str = {1: "image", 2: "gif", 3: "video"}.get(slot, f"slot{slot}")
            slots.append({"slot": slot, "type": type_str, "files": filenames})
        return slots

    def rom_delete(self, filename):
        """Delete a file from ROM by name.

        WARNING: Untested. Use with caution.

        Args:
            filename: Bare filename as stored in ROM (e.g. 'city.jpg').
        """
        self._write(bytes([0xF6, 0x06, 0x05, 0x01, 0x00, 0x00, 0x00]))
        time.sleep(0.05)
        path = f"B:/{filename}"
        path_bytes = path.encode("ascii")
        self._write(bytes([0xFE, len(path_bytes)]) + path_bytes)
        time.sleep(0.1)
        free = self.rom_free()
        _LOGGER.info("ROM delete: '%s' (free: %.2f MB)", filename, free / (1024 * 1024))
        return True

    # ── File upload ──────────────────────────────────────────────────────

    def upload_file(self, filepath, name=None, crop=None):
        """Upload a file to ROM slot 1 (image carousel).

        Args:
            filepath: Path to image file (JPEG or PNG).
            name: Override filename stored on device.
            crop: (x, y, w, h) region to crop before resizing to 320x320.

        Returns True on success.
        """
        from pathlib import Path

        path = Path(filepath)
        data = path.read_bytes()
        size = len(data)
        fname = ((name or path.name).encode("ascii") + b"\x00")

        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg", ".png"):
            try:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(data)).convert("RGB")
                if img.size != (320, 320) or crop:
                    if crop:
                        cx, cy, cw, ch = crop
                        img = img.crop((cx, cy, cx + cw, cy + ch))
                        img = img.resize((320, 320), Image.LANCZOS)
                    else:
                        ratio = max(320 / img.width, 320 / img.height)
                        new_w = int(img.width * ratio + 0.5)
                        new_h = int(img.height * ratio + 0.5)
                        img = img.resize((new_w, new_h), Image.LANCZOS)
                        left = (new_w - 320) // 2
                        top = (new_h - 320) // 2
                        img = img.crop((left, top, left + 320, top + 320))
                    buf = io.BytesIO()
                    fmt = "JPEG" if suffix in (".jpg", ".jpeg") else "PNG"
                    img.save(buf, format=fmt, quality=92)
                    data = buf.getvalue()
                    size = len(data)
            except ImportError:
                _LOGGER.warning("Pillow not installed; upload may fail if image is not 320x320")
            except Exception as e:
                _LOGGER.warning("resize failed (%s); uploading original", e)

        _LOGGER.info("uploading '%s' (%d bytes)", path.name, size)

        f1_start = bytes([
            0xF1, 0x01,
            (size >> 24) & 0xFF, (size >> 16) & 0xFF,
            (size >> 8) & 0xFF, size & 0xFF,
            len(fname),
        ]) + fname
        self._write(f1_start)
        time.sleep(0.05)

        offset = 0
        while offset < size:
            chunk_data = data[offset : offset + CHUNK_SIZE]
            valid = len(chunk_data)
            chunk = chunk_data.ljust(CHUNK_SIZE, b"\x00")
            self._write(bytes([0xF2, valid & 0xFF]) + chunk)
            offset += valid

        f1_end = bytes([
            0xF1, 0x02,
            (size >> 24) & 0xFF, (size >> 16) & 0xFF,
            (size >> 8) & 0xFF, size & 0xFF,
            0x00,
        ])
        self._write(f1_end)

        if not self._wait_upload_done():
            _LOGGER.error("upload failed")
            return False

        self._write(b"\xc0\x01\x00\x00")
        time.sleep(0.5)
        _LOGGER.info("upload complete (%d bytes)", size)
        return True

    # ── Text overlay ─────────────────────────────────────────────────────

    def upload_text_overlay(self, text, font_name="DejaVu Sans", font_size=26,
                            bold=False, italic=False, underline=False,
                            strikethrough=False, outline=False,
                            outline_color=(0, 0, 0), shadow=False,
                            shadow_color=(0, 0, 0), glow=False,
                            glow_color=None, letter_spacing=0,
                            circular=False, circular_radius=130,
                            markup=False, color=(0xFF, 0xFF, 0xFF)):
        """Render text to a 320x320 RGBA PNG and upload as '_txt_.png'.

        The device composites this over the current image slot display.
        Uses Pango/Cairo for rendering, falls back to Pillow.

        Returns True on success.
        """
        r, g, b = color
        data = None

        try:
            import gi
            import cairo
            import io

            gi.require_version("Pango", "1.0")
            gi.require_version("PangoCairo", "1.0")
            from gi.repository import Pango, PangoCairo

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 320, 320)
            ctx = cairo.Context(surface)
            ctx.set_source_rgba(0, 0, 0, 0)
            ctx.paint()

            layout = PangoCairo.create_layout(ctx)
            layout.set_width(320 * Pango.SCALE)
            layout.set_alignment(Pango.Alignment.CENTER)

            font_desc = Pango.FontDescription()
            font_desc.set_family(font_name)
            font_desc.set_size(font_size * Pango.SCALE)
            if bold:
                font_desc.set_weight(Pango.Weight.BOLD)
            if italic:
                font_desc.set_style(Pango.Style.ITALIC)
            layout.set_font_description(font_desc)

            if markup:
                layout.set_markup(text, -1)
                text_len = 0
            else:
                layout.set_text(text, -1)
                text_len = len(text.encode("utf-8"))

            if text_len > 0:
                attrs = Pango.AttrList()
                if underline:
                    attr = Pango.attr_underline_new(Pango.Underline.SINGLE)
                    attr.start_index = 0
                    attr.end_index = text_len
                    attrs.insert(attr)
                if strikethrough:
                    attr = Pango.attr_strikethrough_new(True)
                    attr.start_index = 0
                    attr.end_index = text_len
                    attrs.insert(attr)
                if letter_spacing != 0:
                    attr_ls = Pango.attr_letter_spacing_new(letter_spacing)
                    attr_ls.start_index = 0
                    attr_ls.end_index = text_len
                    attrs.insert(attr_ls)
                layout.set_attributes(attrs)

            _ink, logical = layout.get_pixel_extents()
            y_offset = (320 - logical.height) // 2

            if circular:
                import math
                cx, cy = 160, 160
                radius = circular_radius
                plain_text = layout.get_text()
                char_widths = []
                for ch in plain_text:
                    ch_layout = PangoCairo.create_layout(ctx)
                    ch_layout.set_font_description(font_desc)
                    ch_layout.set_text(ch, -1)
                    _ink_ch, log_ch = ch_layout.get_pixel_extents()
                    char_widths.append(log_ch.width)
                total_width = sum(char_widths)
                total_angle = total_width / radius if radius > 0 else 2 * math.pi
                start_angle = -math.pi / 2 - total_angle / 2
                current_angle = start_angle
                ctx.set_source_rgba(r / 255.0, g / 255.0, b / 255.0, 1.0)
                for i, ch in enumerate(plain_text):
                    char_angle = char_widths[i] / radius if radius > 0 else 0
                    angle = current_angle + char_angle / 2
                    px = cx + radius * math.cos(angle)
                    py = cy + radius * math.sin(angle)
                    ctx.save()
                    ctx.translate(px, py)
                    ctx.rotate(angle + math.pi / 2)
                    ch_layout = PangoCairo.create_layout(ctx)
                    ch_layout.set_font_description(font_desc)
                    ch_layout.set_text(ch, -1)
                    _ink_ch, log_ch = ch_layout.get_pixel_extents()
                    ctx.move_to(-log_ch.width / 2, -log_ch.height / 2)
                    PangoCairo.show_layout(ctx, ch_layout)
                    ctx.restore()
                    current_angle += char_angle
            else:
                def _draw_layout(lx, ly, lr, lg, lb, la=1.0):
                    ctx.move_to(lx, ly)
                    ctx.set_source_rgba(lr / 255.0, lg / 255.0, lb / 255.0, la)
                    PangoCairo.show_layout(ctx, layout)

                if glow:
                    gc = glow_color or color
                    for off in [3, 2, 1]:
                        for dx in range(-off, off + 1):
                            for dy in range(-off, off + 1):
                                if dx * dx + dy * dy <= off * off + 1:
                                    alpha = 0.15 / (off * 0.7)
                                    _draw_layout(dx, y_offset + dy, gc[0], gc[1], gc[2], alpha)
                if shadow:
                    _draw_layout(2, y_offset + 2, shadow_color[0], shadow_color[1],
                                 shadow_color[2], 0.7)
                if outline:
                    ctx.move_to(0, y_offset)
                    PangoCairo.layout_path(ctx, layout)
                    ctx.set_source_rgba(outline_color[0] / 255.0, outline_color[1] / 255.0,
                                        outline_color[2] / 255.0, 1.0)
                    ctx.set_line_width(2.0)
                    ctx.stroke()
                _draw_layout(0, y_offset, r, g, b)

            buf = io.BytesIO()
            surface.write_to_png(buf)
            data = buf.getvalue()

        except Exception as e:
            _LOGGER.debug("Pango/Cairo failed (%s), trying Pillow", e)
            try:
                from PIL import Image, ImageDraw, ImageFont
                import io
                img = Image.new("RGBA", (320, 320), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype(font_name, font_size)
                except Exception:
                    try:
                        font = ImageFont.load_default(font_size)
                    except Exception:
                        font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), text, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x = (320 - tw) // 2
                y = (320 - th) // 2
                draw.text((x, y), text, fill=(r, g, b, 255), font=font)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                data = buf.getvalue()
            except ImportError:
                raise NotSupportedByDevice(
                    "text overlay requires pango (python-gobject) or Pillow"
                )

        if not data:
            _LOGGER.error("text rendering failed")
            return False

        return self._upload_text_png(data)

    def upload_text_layout(self, elements):
        """Render multiple text elements onto a single 320x320 PNG overlay.

        Each element is a string: 'position:text:size:color[:radius][:font]'
        Positions: center, top, bottom, arc-top, arc-bottom
        """
        import math

        try:
            import gi
            import cairo
            import io
            gi.require_version("Pango", "1.0")
            gi.require_version("PangoCairo", "1.0")
            from gi.repository import Pango, PangoCairo
        except ImportError:
            raise NotSupportedByDevice("text-layout requires pango (python-gobject)")

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 320, 320)
        ctx = cairo.Context(surface)
        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.paint()

        for elem in elements:
            parts = elem.split(":")
            if len(parts) < 4:
                raise ValueError(f"element '{elem}' needs at least position:text:size:color")
            pos = parts[0].strip().lower()
            txt = parts[1]
            size = int(parts[2])
            color_str = parts[3].strip().lstrip("#")
            cr = int(color_str[0:2], 16)
            cg = int(color_str[2:4], 16)
            cb = int(color_str[4:6], 16)
            radius = int(parts[4]) if len(parts) > 4 and parts[4].strip() else 130
            font = parts[5].strip() if len(parts) > 5 and parts[5].strip() else "DejaVu Sans"

            font_desc = Pango.FontDescription()
            font_desc.set_family(font)
            font_desc.set_size(size * Pango.SCALE)
            font_desc.set_weight(Pango.Weight.BOLD)

            if pos in ("arc-top", "arc-bottom"):
                ccx, ccy = 160, 160
                char_widths = []
                for ch in txt:
                    ch_layout = PangoCairo.create_layout(ctx)
                    ch_layout.set_font_description(font_desc)
                    ch_layout.set_text(ch, -1)
                    _ink, log = ch_layout.get_pixel_extents()
                    char_widths.append(log.width)
                total_width = sum(char_widths)
                total_angle = total_width / radius if radius > 0 else 2 * math.pi
                if pos == "arc-top":
                    start_angle = -math.pi / 2 - total_angle / 2
                    direction = 1
                else:
                    start_angle = math.pi / 2 + total_angle / 2
                    direction = -1
                ctx.set_source_rgba(cr / 255.0, cg / 255.0, cb / 255.0, 1.0)
                current_angle = start_angle
                for i, ch in enumerate(txt):
                    char_angle = char_widths[i] / radius if radius > 0 else 0
                    angle = current_angle + direction * char_angle / 2
                    px = ccx + radius * math.cos(angle)
                    py = ccy + radius * math.sin(angle)
                    ctx.save()
                    ctx.translate(px, py)
                    if pos == "arc-top":
                        ctx.rotate(angle + math.pi / 2)
                    else:
                        ctx.rotate(angle - math.pi / 2)
                    ch_layout = PangoCairo.create_layout(ctx)
                    ch_layout.set_font_description(font_desc)
                    ch_layout.set_text(ch, -1)
                    _ink, log = ch_layout.get_pixel_extents()
                    ctx.move_to(-log.width / 2, -log.height / 2)
                    PangoCairo.show_layout(ctx, ch_layout)
                    ctx.restore()
                    current_angle += direction * char_angle
            else:
                layout = PangoCairo.create_layout(ctx)
                layout.set_width(320 * Pango.SCALE)
                layout.set_alignment(Pango.Alignment.CENTER)
                layout.set_font_description(font_desc)
                layout.set_text(txt, -1)
                _ink, logical = layout.get_pixel_extents()
                if pos == "top":
                    y = 20
                elif pos == "bottom":
                    y = 320 - logical.height - 20
                else:
                    y = (320 - logical.height) // 2
                ctx.move_to(0, y)
                ctx.set_source_rgba(cr / 255.0, cg / 255.0, cb / 255.0, 1.0)
                PangoCairo.show_layout(ctx, layout)

        buf = io.BytesIO()
        surface.write_to_png(buf)
        data = buf.getvalue()
        return self._upload_text_png(data)

    def _upload_text_png(self, data):
        """Upload pre-rendered PNG data as _txt_.png text overlay."""
        fname = b"_txt_.png\x00"
        size = len(data)

        f1_start = bytes([
            0xF1, 0x01,
            (size >> 24) & 0xFF, (size >> 16) & 0xFF,
            (size >> 8) & 0xFF, size & 0xFF,
            len(fname),
        ]) + fname
        self._write(f1_start)
        time.sleep(0.05)

        offset = 0
        while offset < size:
            chunk_data = data[offset : offset + CHUNK_SIZE]
            valid = len(chunk_data)
            chunk = chunk_data.ljust(CHUNK_SIZE, b"\x00")
            self._write(bytes([0xF2, valid & 0xFF]) + chunk)
            offset += valid

        # Text overlay uses f1 03 (not 02 which is for image uploads)
        f1_end = bytes([
            0xF1, 0x03,
            (size >> 24) & 0xFF, (size >> 16) & 0xFF,
            (size >> 8) & 0xFF, size & 0xFF,
            0x00,
        ])
        self._write(f1_end)

        if not self._wait_upload_done():
            _LOGGER.error("text overlay upload failed")
            return False

        self._write(b"\xc0\x01\x00\x00")
        time.sleep(0.3)
        _LOGGER.info("text overlay uploaded (%d bytes)", size)
        return True

    # ── Image overlay (System Info) ──────────────────────────────────────

    def overlay_set(self, items, hide_logo=False):
        """Set system info overlay on the current image display.

        items: list of 1-2 metric names from: cpu-clock, cpu-temp, cpu-usage, cpu-power

        Protocol:
          c0 00 [logo_byte] 01 — enables System Info overlay mode
          bare e2 — selects which metrics to show (immediate effect)
        """
        metrics = []
        for item in items[:3]:
            item = item.lower().strip()
            if item in ("none", "0"):
                continue
            if item == "no-logo":
                hide_logo = True
                continue
            if item not in _OVERLAY_METRIC_OFFSET:
                raise ValueError(
                    f"unknown overlay metric {item!r}, should be one of: "
                    f"{_quoted(*_OVERLAY_METRIC_OFFSET)}, 'no-logo'"
                )
            metrics.append(item)

        logo_byte = 0x00 if hide_logo else 0x01
        self._write(bytes([0xC0, 0x00, logo_byte, 0x01]))
        time.sleep(0.1)

        e2 = bytearray(OUT_SIZE)
        e2[0] = 0xE2
        if len(metrics) >= 1:
            e2[3 + _OVERLAY_METRIC_OFFSET[metrics[0]]] = 0x01
        if len(metrics) >= 2:
            e2[9 + _OVERLAY_METRIC_OFFSET[metrics[1]]] = 0x01
        self._write(bytes(e2))
        time.sleep(0.1)
        _LOGGER.info("overlay -> %s%s", metrics, " (no logo)" if hide_logo else "")

    def overlay_clear(self):
        """Clear / disable overlay — switch to None mode."""
        self._write(b"\xc0\x00\x00\x00")
        time.sleep(0.1)
        _LOGGER.info("overlay cleared")

    def overlay_set_colors(self, colors):
        """Set overlay text colors for system info items.

        colors: list of up to 4 (R, G, B) tuples.
        Slots: [CPU title] [metric 1] [metric 2] [logo]
        """
        while len(colors) < 4:
            colors.append(colors[-1] if colors else (0x00, 0xFF, 0xFF))
        self._e4_send(0x06, [_parse_color(c) for c in colors[:4]])
        time.sleep(0.05)
        self._write(b"\xc0\x00\x01\x01")
        time.sleep(0.1)
        _LOGGER.info("overlay colors set")

    # ── Slot management ──────────────────────────────────────────────────

    def slot_query(self, slot):
        """Query active file list and duration for a ROM slot.

        Returns {'session': int, 'duration_s': int, 'active_files': [int]}
        """
        session = slot + 5
        resp = self._cmd(bytes([0xFD, session, 0x00]))
        if not resp or len(resp) < 3:
            return {}
        duration = resp[2]
        nfiles = resp[3] if len(resp) > 3 else 0
        active = [resp[4 + i] for i in range(nfiles) if 4 + i < len(resp) and resp[4 + i] != 0]
        return {"session": session, "duration_s": duration, "active_files": active}

    def slot_files_set(self, slot, file_indices, duration_s=5):
        """Set the active file list for a ROM slot.

        file_indices: 1-based indices, up to 4.
        duration_s: 5-60 in 5s steps.
        """
        valid_dur = list(range(5, 65, 5))
        if duration_s not in valid_dur:
            raise ValueError(f"duration must be one of {valid_dur}")
        if not file_indices or len(file_indices) > 4:
            raise ValueError("provide 1-4 file indices (1-based)")
        session = slot + 5
        padded = (list(file_indices) + [0, 0, 0, 0])[:4]
        self._write(bytes([0xF6, session, duration_s] + padded))
        time.sleep(0.05)
        _LOGGER.info("slot %d active files -> %s @ %ds", slot, file_indices, duration_s)

    def display_image_duration(self, slots, seconds):
        """Set display duration for one or more image slots."""
        valid_dur = list(range(5, 65, 5))
        if seconds not in valid_dur:
            raise ValueError(f"duration must be one of {valid_dur}")
        for slot in slots:
            info = self.slot_query(slot)
            active = info.get("active_files", [1])
            if not active:
                active = [1]
            self.slot_files_set(slot, active, seconds)

    # ── Carousel mode ────────────────────────────────────────────────────

    def _set_carousel(self, value):
        """Set Carousel mode: cycle through display modes.

        value = {'modes': ['enthusiast1', 'image', ...], 'interval': 10}
        """
        modes = value.get("modes", [])
        interval = value.get("interval", 10)

        valid_intervals = list(range(5, 65, 5))
        if interval not in valid_intervals:
            raise ValueError(
                f"interval must be one of {valid_intervals}, got {interval}"
            )

        ids = []
        for m in modes:
            m = m.lower().replace(" ", "").replace("_", "")
            mid = _DISPLAY_MODE_ID.get(m)
            if mid is None:
                raise ValueError(
                    f"unknown carousel mode {m!r}, should be one of: "
                    f"{_quoted(*_DISPLAY_MODE_ID)}"
                )
            ids.append(mid)

        if not ids:
            raise ValueError("carousel requires at least one mode")

        self._drain()
        self._session_open(0x09)
        self._ac_begin()

        payload = [interval] + ids
        while len(payload) < 10:
            payload.append(0x00)
        self._write(bytes([0xFB] + payload))
        time.sleep(0.05)

        self._ac_end()
        _LOGGER.info("carousel -> modes=%s interval=%ds", modes, interval)

    # ── Sensor push daemon ──────────────────────────────────────────────

    @staticmethod
    def _sensor_daemon_running():
        """Check if a sensor push daemon is already running."""
        try:
            pid = int(open(_SENSOR_PID_FILE).read().strip())
            os.kill(pid, 0)  # signal 0 = check if process exists
            return True
        except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
            return False

    def _start_sensor_daemon(self):
        """Spawn a detached background process that pushes e0 every second.

        The daemon opens its own HID handle to the device and runs
        independently of the liquidctl CLI process. It writes its PID
        to /tmp/castor3_sensor_push.pid so subsequent invocations can
        detect it's already running.

        The daemon is killed by stop_sensor_daemon() or when the system
        shuts down (it's just a regular process, no systemd needed).
        """
        if self._sensor_daemon_running():
            _LOGGER.debug("sensor daemon already running")
            return

        # Build a self-contained Python script that opens the HID device
        # and loops e0 pushes. This runs as a fully detached process.
        script = f'''
import glob, os, signal, struct, sys, time

REPORT_ID = 0x99
OUT_SIZE = 6143
VID = 0x0414
PID = 0x7a5e

def read_cpu_temp():
    prio_map = {{"k10temp": 1, "zenpower": 1, "coretemp": 2, "cpu_thermal": 3, "acpitz": 4}}
    best, best_p = 0, 999
    for d in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        try:
            name = open(f"{{d}}/name").read().strip()
        except Exception:
            continue
        p = prio_map.get(name)
        if p is None or p >= best_p:
            continue
        sensors = ["temp2_input", "temp1_input"] if name in ("k10temp", "zenpower") else ["temp1_input"]
        for s in sensors:
            try:
                v = int(open(f"{{d}}/{{s}}").read().strip()) // 1000
                if 0 < v < 150:
                    best, best_p = v, p
                    break
            except Exception:
                continue
    return best

def read_cpu_usage():
    def stat():
        try:
            line = open("/proc/stat").readline().split()
            idle = int(line[4]) + int(line[5])
            total = sum(int(p) for p in line[1:])
            return idle, total
        except Exception:
            return 0, 0
    i1, t1 = stat()
    time.sleep(0.2)
    i2, t2 = stat()
    dt = t2 - t1
    return round(100 * (dt - (i2 - i1)) / dt) if dt > 0 else 0

def write_pkt(dev, payload):
    buf = bytearray(OUT_SIZE + 1)
    buf[0] = REPORT_ID
    buf[1:1+len(payload)] = payload
    dev.write(bytes(buf))

# Write PID file
open("{_SENSOR_PID_FILE}", "w").write(str(os.getpid()))

def cleanup(*_):
    try:
        os.unlink("{_SENSOR_PID_FILE}")
    except Exception:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

try:
    import hid
    dev = hid.device()
    dev.open(VID, PID)
except Exception:
    cleanup()

try:
    while True:
        cpu_temp = min(255, max(0, read_cpu_temp()))
        cpu_usage = min(100, max(0, read_cpu_usage()))
        try:
            cpu_clk = int(open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq").read().strip()) // 1000
        except Exception:
            cpu_clk = 0
        cpu_clk = min(0xFFFF, max(0, cpu_clk))

        pkt = bytearray(19)
        pkt[0] = 0xE0
        pkt[2] = cpu_temp
        pkt[3] = 0x20
        pkt[4] = 0x04
        pkt[5] = cpu_usage
        pkt[6] = 0x10
        pkt[7] = 45
        pkt[9] = (cpu_clk >> 8) & 0xFF
        pkt[10] = cpu_clk & 0xFF
        write_pkt(dev, bytes(pkt))

        # Drain any incoming packets to prevent queue buildup
        dev.set_nonblocking(1)
        for _ in range(4):
            if not dev.read(255):
                break
        dev.set_nonblocking(0)

        time.sleep(0.8)  # ~1 push/sec accounting for cpu_usage 0.2s sample
except Exception:
    pass
finally:
    cleanup()
'''
        # Launch as a fully detached subprocess
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # detach from parent process group
        )
        _LOGGER.info("sensor daemon started (pid %d)", proc.pid)

    @staticmethod
    def stop_sensor_daemon():
        """Stop the sensor push daemon if running."""
        try:
            pid = int(open(_SENSOR_PID_FILE).read().strip())
            os.kill(pid, signal.SIGTERM)
            _LOGGER.info("sensor daemon stopped (pid %d)", pid)
        except (FileNotFoundError, ValueError, ProcessLookupError):
            pass
        try:
            os.unlink(_SENSOR_PID_FILE)
        except FileNotFoundError:
            pass

    # ── Sensor push internals ────────────────────────────────────────────

    def _push_cpu_model(self):
        """Send CPU model string to device (used in Enthusiast 02 display)."""
        try:
            model = ""
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        model = line.split(":", 1)[1].strip()
                        break
            if not model:
                model = "Unknown CPU"
            for suffix in [" Processor", " processor", " CPU"]:
                model = model.replace(suffix, "")
            model = model.strip()
            if len(model) % 2 != 0:
                model += " "
        except Exception:
            model = "Unknown CPU "

        encoded = model.encode("ascii", errors="replace")[:64]
        self._write(bytes([0xE1, len(encoded)]) + encoded)
        time.sleep(0.02)
        _LOGGER.debug("pushed CPU model: %s", model)

    def _push_sensors_once(self):
        """Build and send one e0 sensor push packet (host -> device).

        Coolant is hardcoded to 45C (no USB-accessible thermistor).
        CPU usage is read from /proc/stat (two samples, 200ms apart).
        """
        cpu_temp = _read_cpu_temp() or 0
        cpu_usage = self._read_cpu_usage()
        cpu_clk = 0

        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq") as f:
                cpu_clk = int(f.read().strip()) // 1000
        except Exception:
            pass

        cpu_clk = clamp(cpu_clk, 0, 0xFFFF)
        cpu_temp = clamp(cpu_temp, 0, 255)
        cpu_usage = clamp(cpu_usage, 0, 100)

        pkt = bytearray(19)
        pkt[0] = 0xE0
        pkt[1] = 0x00
        pkt[2] = cpu_temp
        pkt[3] = 0x20
        pkt[4] = 0x04
        pkt[5] = cpu_usage
        pkt[6] = 0x10
        pkt[7] = 45  # coolant — hardcoded, no sensor
        pkt[8] = 0x00
        pkt[9] = (cpu_clk >> 8) & 0xFF
        pkt[10] = cpu_clk & 0xFF
        self._write(bytes(pkt))

    @staticmethod
    def _read_cpu_usage():
        """Read CPU usage % from /proc/stat (two samples, 200ms apart).

        Returns integer 0-100. Returns 0 on failure.
        """
        def _read_stat():
            try:
                with open("/proc/stat") as f:
                    line = f.readline()  # first line: cpu aggregate
                parts = line.split()
                # user nice system idle iowait irq softirq steal
                idle = int(parts[4]) + int(parts[5])  # idle + iowait
                total = sum(int(p) for p in parts[1:])
                return idle, total
            except Exception:
                return 0, 0

        idle1, total1 = _read_stat()
        time.sleep(0.2)
        idle2, total2 = _read_stat()

        d_total = total2 - total1
        d_idle = idle2 - idle1
        if d_total <= 0:
            return 0
        return round(100 * (d_total - d_idle) / d_total)
