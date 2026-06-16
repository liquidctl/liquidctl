# Copyright 2024  liquidctl contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""liquidctl driver for Enermax Liqtech XTR series liquid coolers.

Protocol reverse-engineered from the USB traffic on Linux; no vendor
documentation was available.  The device is a USB HID peripheral that
controls the LCD display on the pump head of the Liqtech XTR AIO cooler.
It does not expose any readable sensor data over USB.

Copyright 2024  liquidctl contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDriver

LOGGER = logging.getLogger(__name__)

# Every outbound report starts with this ID followed by 64 bytes of data.
_REPORT_ID = 0x20
_REPORT_LEN = 65  # report-ID byte + 64 data bytes

# (command_byte, hi-byte offset within the 65-byte report buffer)
# Values are 16-bit big-endian, displayed verbatim (no unit conversion).
_CMD_CPU  = (0x01, 5)   # primary CPU field
_CMD_CPU2 = (0x02, 6)   # secondary CPU field — mirrors primary; hardware shows ≤2 digits
_CMD_GPU  = (0x04, 8)   # GPU field, 4-digit capable
_CMD_PUMP = (0x10, 11)  # pump-RPM field

_CHANNELS = {
    'cpu':  _CMD_CPU,
    'gpu':  _CMD_GPU,
    'pump': _CMD_PUMP,
}

_MODES = ('temperature', 'rpm')


class EnermaxLiqtechXtr(UsbHidDriver):
    """liquidctl driver for Enermax Liqtech XTR AIO liquid coolers.

    The Liqtech XTR exposes the pump-head LCD over USB HID.  It is a
    write-only display: no temperatures or pump speeds can be read back
    from the device — those values must come from host sensors.

    Three display fields are available via ``set_screen``:

    ``cpu``
        Primary CPU temperature field (°C).  Also written to the secondary
        CPU field (cmd 0x02); note that field's hardware only renders the
        two lowest digits.

    ``gpu``
        4-digit GPU field.  Use ``id * 1000 + temp_c`` to show which GPU
        is currently displayed (e.g. ``2065`` = GPU #2 at 65 °C) and cycle
        through multiple GPUs by calling ``set_screen`` in a loop.

    ``pump``
        Pump RPM.  Read from the host Super-I/O chip (e.g. via hwmon) and
        pushed to the display; the USB device itself has no tachometer.

    **Screen refresh:** Each field blanks after roughly 2 seconds without
    a write.  Call ``set_screen`` from a loop or systemd service to keep
    the display live.

    Protocol (reverse-engineered; Enermax VID 0x2e3c PID 0x0a12):

    - HID report ID ``0x20``, 64 data bytes (65 total including report ID).
    - buf[1] = command byte; value big-endian at buf[off:off+2].
    - Field offsets (in the 65-byte buffer): cpu cmd=0x01 @5, cpu2 cmd=0x02
      @6, gpu cmd=0x04 @8, pump cmd=0x10 @11.
    - Status command (0x10/0x01) returns only static device info; no live
      sensor data is readable from the device.
    """

    _MATCHES = [
        (0x2e3c, 0x0a12, 'Enermax Liqtech XTR', {}),
    ]

    def initialize(self, **kwargs):
        """Initialize the device.

        Writes zeros to all display fields to confirm USB connectivity, then
        returns a single-entry status list identifying the device.
        """
        for cmd, off in (_CMD_CPU, _CMD_CPU2, _CMD_GPU, _CMD_PUMP):
            self._write_field(cmd, off, 0)
        return [('Device', 'Enermax Liqtech XTR', '')]

    def get_status(self, **kwargs):
        """Return device status.

        The Enermax Liqtech XTR is a write-only display over USB; no sensor
        values can be read back from the device.  Returns an empty list.
        """
        return []

    def set_screen(self, channel, mode, value, **kwargs):
        """Set a numeric field on the pump-head LCD.

        channel  one of: cpu, gpu, pump
        mode     one of: temperature, rpm  (informational; value displayed as-is)
        value    integer in [0, 9999]

        For ``channel='cpu'`` the value is additionally written to the
        secondary CPU field so both fields stay consistent.

        The screen requires periodic refresh (blanks after ~2 s); call this
        method in a loop for a live display.
        """
        channel = channel.lower()
        mode = mode.lower()
        if channel not in _CHANNELS:
            raise ValueError(
                f'unknown channel {channel!r}, must be one of: {", ".join(_CHANNELS)}'
            )
        if mode not in _MODES:
            raise ValueError(
                f'unknown mode {mode!r}, must be one of: {", ".join(_MODES)}'
            )
        val = int(value)
        if not 0 <= val <= 9999:
            raise ValueError(f'value {val} out of range [0, 9999]')

        cmd, off = _CHANNELS[channel]
        self._write_field(cmd, off, val)
        if channel == 'cpu':
            self._write_field(*_CMD_CPU2, val)
        LOGGER.debug('set_screen channel=%s mode=%s value=%d', channel, mode, val)

    def set_color(self, channel, mode, colors, **kwargs):
        """Not supported — device has no USB-controlled LEDs."""
        raise NotSupportedByDriver

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported — pump speed is controlled via motherboard PWM header."""
        raise NotSupportedByDriver

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported — pump speed is controlled via motherboard PWM header."""
        raise NotSupportedByDriver

    def _write_field(self, cmd, off, val):
        val = max(0, min(int(val), 9999))
        buf = [_REPORT_ID, cmd] + [0x00] * (_REPORT_LEN - 2)
        buf[off]     = (val >> 8) & 0xff
        buf[off + 1] = val & 0xff
        self.device.write(buf)
