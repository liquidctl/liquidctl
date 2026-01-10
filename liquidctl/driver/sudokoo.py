"""liquidctl driver for the Sudokoo SK700V CPU cooler LCD display.

Protocol reverse-engineered by Fernando Pelliccioni.

Copyright Fernando Pelliccioni and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import logging

from liquidctl.driver.usb import UsbHidDriver

_LOGGER = logging.getLogger(__name__)

VENDOR_ID = 0x381c
PRODUCT_ID = 0x0003
_REPORT_LENGTH = 64

# Packet headers
_HEARTBEAT_HEADER = bytes([0x10, 0x68, 0x01, 0x09, 0x02, 0x03, 0x01, 0x78, 0x16])
_DATA_HEADER = bytes([0x10, 0x68, 0x01, 0x09, 0x0d, 0x01, 0x02, 0x00])
_DATA_HEADER_SCREEN_OFF = bytes([0x10, 0x68, 0x01, 0x09, 0x0d, 0x01, 0x00, 0x00])

# Constants
_CHECKSUM_CONSTANT = 0x82
_TEMP_CONSTANT = 0x42
_FOOTER_CONSTANT = 0x16


class SudokooSk700v(UsbHidDriver):
    """Driver for Sudokoo SK700V CPU cooler LCD display."""

    _MATCHES = [
        (VENDOR_ID, PRODUCT_ID, "Sudokoo SK700V", {}),
    ]

    def initialize(self, **kwargs):
        """Initialize the device and return device info."""
        msg = [
            ("Device", "Sudokoo SK700V", ""),
            ("Status", "Connected", ""),
        ]
        _LOGGER.info("Sudokoo SK700V initialized")
        return msg

    def get_status(self, **kwargs):
        """Get device status (not supported - device is write-only)."""
        _LOGGER.info("SK700V is a write-only display device")
        return []

    def disconnect(self, **kwargs):
        """Disconnect from the device."""
        super().disconnect(**kwargs)

    def set_screen(self, mode, **kwargs):
        """Turn the screen on or off.

        Args:
            mode: 'on' or 'off'
        """
        if mode.lower() == 'off':
            # Send screen off packet
            packet = self._create_screen_off_packet()
            self.device.write(packet)
            _LOGGER.info("Screen turned off")
        else:
            # Screen on is implicit when sending data
            _LOGGER.info("Screen will turn on when data is sent")

    def set_status_display(self, temp, load, freq, power, temp_scale='C', **kwargs):
        """Send CPU metrics to the display.

        Args:
            temp: Temperature in degrees (Celsius or Fahrenheit based on temp_scale)
            load: CPU load percentage (0-100)
            freq: CPU frequency in MHz
            power: CPU power in Watts
            temp_scale: 'C' for Celsius, 'F' for Fahrenheit
        """
        # Send heartbeat first
        heartbeat = self._create_heartbeat_packet()
        self.device.write(heartbeat)

        # Send data packet
        data = self._create_data_packet(
            power_w=int(power),
            load_pct=int(load),
            freq_mhz=int(freq),
            temp=int(temp),
            temp_scale=temp_scale
        )
        self.device.write(data)

        _LOGGER.debug(
            "sent: temp=%d%s, load=%d%%, freq=%dMHz, power=%dW",
            temp,
            "°F" if temp_scale == "F" else "°C",
            load,
            freq,
            power,
        )

    def _create_heartbeat_packet(self):
        """Create a heartbeat packet."""
        packet = bytearray(_REPORT_LENGTH)
        packet[:len(_HEARTBEAT_HEADER)] = _HEARTBEAT_HEADER
        return bytes(packet)

    def _create_screen_off_packet(self):
        """Create a screen off packet."""
        packet = bytearray(_REPORT_LENGTH)
        packet[:len(_DATA_HEADER_SCREEN_OFF)] = _DATA_HEADER_SCREEN_OFF
        # Add dummy values
        packet[8] = 0x64   # power
        packet[9] = 0x32   # power correlated
        packet[10] = 0x00  # Celsius
        packet[11] = _TEMP_CONSTANT
        packet[12] = 0x70  # temp encoded
        packet[15] = 0x28  # load
        packet[16] = 0x0e  # freq high
        packet[17] = 0x10  # freq low
        packet[18] = self._calc_checksum(packet)
        packet[19] = _FOOTER_CONSTANT
        return bytes(packet)

    def _create_data_packet(self, power_w, load_pct, freq_mhz, temp, temp_scale='C'):
        """Create a data packet with the given metrics.

        Args:
            power_w: Power in Watts (0-255)
            load_pct: Load percentage (0-100)
            freq_mhz: Frequency in MHz
            temp: Temperature value
            temp_scale: 'C' for Celsius, 'F' for Fahrenheit
        """
        # Convert frequency to valid value (480 + n*510)
        freq_valid = self._freq_to_valid(freq_mhz)
        freq_high = (freq_valid >> 8) & 0xFF
        freq_low = freq_valid & 0xFF

        # Calculate power correlated value
        b9 = int(round(power_w * 10 / 23))

        # Temperature encoding depends on scale
        if temp_scale.upper() == 'F':
            b10 = 0x01  # Fahrenheit
            b12 = (temp * 2) & 0xFF
        else:
            b10 = 0x00  # Celsius
            if temp <= 64:
                b12 = ((temp - 32) * 4) & 0xFF
            else:
                b12 = ((temp - 64) * 2 + 128) & 0xFF

        # Build packet
        packet = bytearray(_REPORT_LENGTH)
        packet[:len(_DATA_HEADER)] = _DATA_HEADER

        packet[8] = power_w & 0xFF       # b8: Power
        packet[9] = b9 & 0xFF            # b9: Power correlated
        packet[10] = b10                 # b10: Scale (0=C, 1=F)
        packet[11] = _TEMP_CONSTANT      # b11: Constant 0x42
        packet[12] = b12                 # b12: Temp encoded
        packet[13] = 0x00                # b13: Unknown
        packet[14] = 0x00                # b14: Unknown
        packet[15] = load_pct & 0xFF     # b15: Load %
        packet[16] = freq_high           # b16: Freq high byte
        packet[17] = freq_low            # b17: Freq low byte
        packet[18] = self._calc_checksum(packet)  # b18: Checksum
        packet[19] = _FOOTER_CONSTANT    # b19: Constant 0x16

        return bytes(packet)

    def _calc_checksum(self, packet):
        """Calculate the checksum for a data packet.

        Formula: (b8 + b9 + b10 + b11 + b12 + b13 + b14 + b15 + b16 + b17 + 0x82) & 0xFF
        """
        checksum = (
            packet[8] + packet[9] + packet[10] + packet[11] +
            packet[12] + packet[13] + packet[14] + packet[15] +
            packet[16] + packet[17] + _CHECKSUM_CONSTANT
        )
        return checksum & 0xFF

    def _freq_to_valid(self, freq_mhz):
        """Convert frequency to the nearest valid value.

        Valid frequencies follow the pattern: 480 + n * 510
        Values: 480, 990, 1500, 2010, 2520, 3030, 3540, 4050, 4560, 5070, 5580, 6090...
        """
        n = round((freq_mhz - 480) / 510)
        n = max(0, n)  # Ensure non-negative
        return 480 + n * 510
