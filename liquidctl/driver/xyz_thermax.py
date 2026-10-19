"""liquidctl driver for the XYZ Thermax air cooler temperature display.

Supported devices:

- XYZ Thermax 6 Pro Duo temperature display (USB HID 5131:2007)

Copyright liquidctl contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import logging

from liquidctl.driver.usb import UsbHidDriver

_LOGGER = logging.getLogger(__name__)

# Output report: ID 0 followed by 64 data bytes.  The layout comes from the vendor application
# (XYZ-WC-AQUA), which sends one report about every second; see docs/xyz-thermax-display-guide.md.
_REPORT_LENGTH = 64
_COMMAND = 0x40
_OFFSET_CPU_TEMPERATURE = 1
_OFFSET_GPU_TEMPERATURE = 9
_OFFSET_CHECKSUM = 29
_FLAG_FAHRENHEIT = 0x80
_TEMPERATURE_MAX = 127

_UNITS = {"celsius": 0x00, "fahrenheit": _FLAG_FAHRENHEIT}


def _temperature(text, name):
    try:
        value = int(text)
    except ValueError:
        raise ValueError(f"{name} temperature must be a whole number: {text!r}") from None
    if not 0 <= value <= _TEMPERATURE_MAX:
        raise ValueError(f"{name} temperature must be between 0 and {_TEMPERATURE_MAX}")
    return value


class XyzThermax(UsbHidDriver):
    """Driver for the temperature display of the XYZ Thermax 6 Pro Duo.

    The display measures nothing: it shows the CPU temperature that the host sends to it.  The
    device has no readable state, and the USB IDs are generic (the same pair is used by some
    magnetic stripe readers), so the driver never reads from it or writes during `initialize`.
    """

    _MATCHES = [
        (0x5131, 0x2007, "XYZ Thermax 6 Pro Duo display", {}),
    ]

    def initialize(self, **kwargs):
        """Nothing to initialize."""

        return []

    def get_status(self, **kwargs):
        """Not supported: the device does not report anything."""

        _LOGGER.info("No status available")
        return []

    def set_screen(self, channel, mode, value, **kwargs):
        """Show a temperature on the display.

        The `channel` must be `lcd`, the `mode` is the unit that the display should use,
        `celsius` or `fahrenheit`, and the `value` is the CPU temperature in °C, optionally
        followed by the GPU temperature (e.g. `54` or `54,49`).  The display converts to °F
        itself, so values are always given in °C.
        """

        if channel != "lcd":
            raise ValueError("Only the 'lcd' channel is supported")
        if mode not in _UNITS:
            raise ValueError(f"Mode must be one of: {', '.join(_UNITS)}")

        parts = str(value).split(",")
        if len(parts) > 2:
            raise ValueError("Value must be 'CPU' or 'CPU,GPU' temperatures in °C")
        cpu = _temperature(parts[0], "CPU")
        gpu = _temperature(parts[1], "GPU") if len(parts) == 2 else 0

        _LOGGER.info("showing CPU %d °C, GPU %d °C in %s", cpu, gpu, mode)
        self.device.write(self._report(cpu, gpu, _UNITS[mode]))

    @staticmethod
    def _report(cpu, gpu, unit_flag):
        data = [0] * _REPORT_LENGTH
        data[0] = _COMMAND
        data[_OFFSET_CPU_TEMPERATURE] = cpu | unit_flag
        data[_OFFSET_GPU_TEMPERATURE] = gpu | unit_flag
        data[_OFFSET_CHECKSUM] = sum(data[:_OFFSET_CHECKSUM]) & 0xFF
        return [0x00] + data
