"""liquidctl drivers for Lian Li Uni hubs.

Supported devices:

- Lian Li Uni SL
- Lian Li Uni SL v2
- Lian Li Uni AL
- Lian Li Uni AL v2
- Lian Li Uni SL-Infinity

Acknowledgements:

- EightB1ts for finding IDs, PWM Commands and speed byte calculation
  https://github.com/EightB1ts/uni-sync

Copyright BlafKing and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import time

from enum import Enum
from liquidctl.driver.usb import UsbHidDriver
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

# Minimum and maximum channel, corresponds to channels 1-4
_MIN_CHANNEL = 1
_MAX_CHANNEL = 4

# PWM commands mapped by device type
_PWM_COMMANDS = {
    "SL": [224, 16, 49],
    "AL": [224, 16, 66],
    "SLI": [224, 16, 98],
    "SLV2": [224, 16, 98],
    "ALV2": [224, 16, 98],
}

_REPORT_LENGTH = 65


class ChannelMode(Enum):
    AUTO = "auto"
    FIXED = "fixed"


class LianLiUni(UsbHidDriver):
    """Driver for Lian Li Uni fan controllers."""

    _MATCHES = [
        (0x0CF2, 0x7750, "Lian Li Uni SL", {"device_type": "SL"}),
        (0x0CF2, 0xA100, "Lian Li Uni SL", {"device_type": "SL"}),
        (0x0CF2, 0xA101, "Lian Li Uni AL", {"device_type": "AL"}),
        (0x0CF2, 0xA102, "Lian Li Uni SL-Infinity", {"device_type": "SLI"}),
        (0x0CF2, 0xA103, "Lian Li Uni SL V2", {"device_type": "SLV2"}),
        (0x0CF2, 0xA104, "Lian Li Uni AL V2", {"device_type": "ALV2"}),
        (0x0CF2, 0xA105, "Lian Li Uni SL V2", {"device_type": "SLV2"}),
    ]

    def __init__(self, device, description, **kwargs):
        """Initialize the Lian Li Uni driver."""
        super().__init__(device, description, **kwargs)
        self.device_type = kwargs.get("device_type")
        assert self.device_type, f"unexpected device with PID {hex(self.device.product_id)}"
        self.supports_cooling = True

    def initialize(self, **kwargs):
        """Initialize the device and enable PWM synchronization on all channels."""

        # Enable PWM synchronization on all channels
        for channel in range(_MIN_CHANNEL, _MAX_CHANNEL + 1):
            self.set_fan_control_mode(channel, ChannelMode.AUTO)
            time.sleep(0.2)  # Delay to prevent race conditions

        return None

    def get_status(self, **kwargs):
        """Returns queried speed from controller,
        if nothing is returned, returns 0"""
        status = []

        for channel in range(_MIN_CHANNEL, _MAX_CHANNEL + 1):
            current_speed = self._query_current_speed(channel)
            if current_speed is None:
                current_speed = 0
            status.append((f"Fan {channel} speed", int(current_speed), "rpm"))

        return status

    def set_fan_control_mode(self, channel, desired_state):
        """Toggles or explicitly sets PWM synchronization for manual speed control.

        Unstable

        Parameters:
            channel: str or (unstable) int - channel name or number ([fan]1–4);
            desired_state: ChannelMode - set AUTO to enable Auto PWM mode, FIXED to set be able to set fixed/manual speed.
        """
        channel = _parse_channel(channel)

        if desired_state is ChannelMode.AUTO:
            debug_string = "enabling"
            channel_byte = 0x11 << (channel - 1)  # enables auto mode
        else:
            debug_string = "disabling"
            channel_byte = 0x10 << (channel - 1)  # disables auto mode

        # Construct the command to toggle PWM synchronization
        command_prefix = _PWM_COMMANDS.get(self.device_type)
        assert command_prefix

        command = command_prefix + [channel_byte]
        _LOGGER.debug("%s PWM sync for channel %d: command %s", debug_string, channel, command)

        self.device.write(command)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set a fixed speed for the specified channel.

        Parameters:
            channel: str or (unstable) int - channel name or number ([fan]1–4);
            duty: int - the desired speed percentage (0-100).
        """
        channel = _parse_channel(channel)
        duty = clamp(duty, 0, 100)

        self.set_fan_control_mode(channel, ChannelMode.FIXED)

        speed_byte = self._calculate_speed_byte(duty)
        command = [224, channel + 31, 0, speed_byte]
        _LOGGER.info("setting fan%d PWM duty to %d%%", channel, duty)
        self.device.write(command)
        time.sleep(0.1)  # Delay to prevent race conditions

    def _query_current_speed(self, channel):
        """
        Query the actual fan speed from the device for a given channel by reading the
        controller's input report.

        For device types:
          - 'SL', 'AL', 'SLI': speed data begins at offset 1.
          - 'SLV2', 'ALV2': speed data begins at offset 2.

        Each channel's speed occupies 2 bytes and is the current RPM

        Parameters:
            channel (int): channel number (1–4).

        Returns:
            int: The fan speed value as reported by the device, or raises an Assert if the read fails.
        """
        assert _MIN_CHANNEL <= channel <= _MAX_CHANNEL

        # Determine offset based on the device type.
        if self.device_type in ["SL", "AL", "SLI"]:
            offset = 1
        elif self.device_type in ["SLV2", "ALV2"]:
            offset = 2
        else:
            raise AssertionError(f"unsupported device type for reading speed: {self.device_type}")

        report = self.device.get_input_report(224, 65)

        # # Calculate the starting index for this channel's speed value.
        start_index = offset + (channel - 1) * 2
        _LOGGER.debug("start_index: %s", start_index)
        # Extract the 2 bytes corresponding to this channel.
        speed_bytes = report[start_index : start_index + 2]
        if len(speed_bytes) < 2:
            raise AssertionError(f"report is too short for channel {channel}: {report}")

        speed_value = int.from_bytes(speed_bytes, byteorder="big")
        _LOGGER.debug(
            "channel %d: extracted bytes %s -> speed value %d",
            channel,
            speed_bytes,
            speed_value,
        )

        return speed_value

    def _calculate_speed_byte(self, speed):
        """Calculate the speed byte based on the device type and desired speed.

        Parameters:
            speed: int - The desired speed percentage (0-100)

        Returns:
            int - The calculated speed byte to send to the device
        """
        if self.device_type in ["SL", "AL"]:
            if speed == 0:
                return 40
            else:
                speed_byte = int((800 + (11 * speed)) / 19) & 0xFF
        elif self.device_type == "SLI":
            if speed == 0:
                return 10
            else:
                speed_byte = int((250 + (17.5 * speed)) / 20) & 0xFF
        elif self.device_type in ["SLV2", "ALV2"]:
            if speed == 0:
                return 7
            else:
                speed_byte = int((200 + (19 * speed)) / 21) & 0xFF
        else:
            raise AssertionError(f"unsupported device type: {self.device_type}")
        return speed_byte


def _parse_channel(name_or_number):
    """Parse a channel name-or-number spec into a channel number.

    Note that passing channel numbers to the public driver APIs is an unstable feature, that may
    very well be removed.

    >>> _parse_channel("fan1")
    1

    >>> _parse_channel(1)
    1

    >>> _parse_channel("1")
    Traceback (most recent call last):
        ...
    ValueError: invalid channel '1', available channels are 'fan1'...'fan4'

    >>> _parse_channel("fan5")
    Traceback (most recent call last):
        ...
    ValueError: invalid channel 'fan5', available channels are 'fan1'...'fan4'

    >>> _parse_channel(5)
    Traceback (most recent call last):
        ...
    ValueError: invalid channel 5, available channels are 'fan1'...'fan4'
    """
    channel = None

    if isinstance(name_or_number, str) and name_or_number.startswith("fan"):
        channel = int(name_or_number.removeprefix("fan"))
    elif isinstance(name_or_number, int):
        channel = name_or_number

    if channel is None or not (_MIN_CHANNEL <= channel <= _MAX_CHANNEL):
        raise ValueError(
            f"invalid channel {name_or_number!r}, "
            f"available channels are 'fan{_MIN_CHANNEL}'...'fan{_MAX_CHANNEL}'"
        )

    return channel
