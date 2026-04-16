"""liquidctl drivers for Corsair Commander Core.

Supported devices:

- Corsair Commander Core

Copyright ParkerMc and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
from contextlib import contextmanager

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet, NotSupportedByDriver, NotSupportedByDevice
from liquidctl.util import clamp, u16le_from

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 96
_RESPONSE_LENGTH = 96

_INTERFACE_NUMBER = 0

_FAN_COUNT = 6

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

_FAN_MODE_FIXED_PERCENT = 0x00
_FAN_MODE_CURVE_PERCENT = 0x02

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

    def initialize(self, **kwargs):
        """Initialize the device and get the fan modes."""

        with self._wake_device_context():
            # Get Firmware
            res = self._send_command(_CMD_GET_FIRMWARE)
            fw_version = (res[3], res[4], res[5])
            self._fw_major = fw_version[0]

            status = [('Firmware version', '{}.{}.{}'.format(*fw_version), '')]

            # Get LEDs per fan
            res = self._read_data(_MODE_LED_COUNT, _DATA_TYPE_LED_COUNT)
            num_devices = res[0]
            led_data = res[1:1 + num_devices * 4]
            for i in range(0, num_devices):
                connected = u16le_from(led_data, offset=i * 4) == 2
                num_leds = u16le_from(led_data, offset=i * 4 + 2)
                if self._has_pump:
                    label = 'AIO LED count' if i == 0 else f'RGB port {i} LED count'
                else:
                    label = f'RGB port {i+1} LED count'

                status += [(label, num_leds if connected else None, '')]

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

        return status

    def get_status(self, **kwargs):
        """Get all the fan speeds and temps"""
        status = []

        with self._wake_device_context():
            for i, speed in enumerate(self._get_speeds()):
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
        raise NotSupportedByDriver

    def _ensure_fw_version(self):
        """Fetch and cache firmware major version. Must be called inside a wake context."""
        if self._fw_major is None:
            res = self._send_command(_CMD_GET_FIRMWARE)
            self._fw_major = res[3]

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
            ValueError('a minimum of 2 speed curve points must be configured.')
        if len(curve_points) > 7:
            ValueError('a maximum of 7 speed curve points may be configured.')

        with self._wake_device_context():
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

        with self._wake_device_context():
            self._ensure_fw_version()
            if self._fw_major >= 2:
                # fw2.x: use fixed-percent mode (0x00) on the speed-mode endpoint,
                # then write duties to the fixed-percent endpoint.  This mirrors the
                # fw1.x path exactly, using the shifted fw2.x endpoint IDs.
                # Writing a flat curve to _MODE_HW_CURVE_PERCENT_V2 does NOT work
                # because 1-pt / flat 2-pt entries are ignored by the device at
                # temperatures above the reference point (confirmed empirically).
                mode_ep = _MODE_HW_SPEED_MODE_V2
                res = self._read_data(mode_ep, _DATA_TYPE_HW_SPEED_MODE)
                device_count = res[0]
                data = bytearray(res[0:device_count + 1])
                for chan in channels:
                    data[chan + 1] = _FAN_MODE_FIXED_PERCENT
                self._write_data(mode_ep, _DATA_TYPE_HW_SPEED_MODE, data)

                fixed_ep = _MODE_HW_FIXED_PERCENT_V2
                res = self._read_data(fixed_ep, _DATA_TYPE_HW_FIXED_PERCENT)
                device_count = res[0]
                data = bytearray(res[0:device_count * 2 + 1])
                duty_le = int.to_bytes(clamp(duty, 0, 100), length=2, byteorder="little", signed=False)
                for chan in channels:
                    i = chan * 2 + 1
                    data[i: i + 2] = duty_le
                self._write_data(fixed_ep, _DATA_TYPE_HW_FIXED_PERCENT, data)
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
                duty_le = int.to_bytes(clamp(duty, 0, 100), length=2, byteorder="little", signed=False)
                for chan in channels:
                    i = chan * 2 + 1
                    data[i: i + 2] = duty_le
                self._write_data(fixed_ep, _DATA_TYPE_HW_FIXED_PERCENT, data)

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
    def _wake_device_context(self):
        try:
            self._send_command(_CMD_WAKE)
            yield
        finally:
            self._send_command(_CMD_SLEEP)

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
