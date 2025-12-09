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

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import time

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

# Minimum and maximum channel, corresponds to channels 1-4
_MIN_CHANNEL = 0
_MAX_CHANNEL = 3

# PWM commands mapped by device type
_PWM_COMMANDS = {
    "SL": [224, 16, 49],
    "AL": [224, 16, 66],
    "SLI": [224, 16, 98],
    "SLV2": [224, 16, 98],
    "ALV2": [224, 16, 98],
}

_REPORT_LENGTH = 65


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
        if not self.device_type:
            raise NotSupportedByDevice(f"Unknown device with PID: {hex(self.device.product_id)}")
        # Variables for CoolerControl support
        self.channel_speeds = {}
        self.pwm_channels = {channel: False for channel in range(_MIN_CHANNEL, _MAX_CHANNEL + 1)}
        self.supports_cooling = True

    def initialize(self, **kwargs):
        """Initialize the device and enable PWM synchronization on all channels."""

        # Enable PWM synchronization on all channels
        for channel in range(_MIN_CHANNEL, _MAX_CHANNEL + 1):
            self.toggle_pwm_sync(channel, desired_state=True)
            time.sleep(0.2)  # Delay to prevent race conditions

        return None

    def get_status(self, **kwargs):
        """Returns queried speed from controller,
        if nothing is returned, returns 0"""
        status = []

        for channel in range(_MIN_CHANNEL, _MAX_CHANNEL + 1):
            current_speed = self.query_current_speed(channel)
            duty_name = f"Channel {channel + 1}"
            if current_speed is None:
                current_speed = 0
            status.append((duty_name, int(current_speed), "rpm"))

        return status

    def toggle_pwm_sync(self, channel, desired_state=None):
        """Toggles or explicitly sets PWM synchronization for manual speed control.

        Parameters:
            channel: int - The zero-based index of the channel
            desired_state: bool, optional - Set True to enable PWM, False to disable PWM.
                                            If None, toggle the current state.
        """
        if not _MIN_CHANNEL <= channel <= _MAX_CHANNEL:
            raise ValueError(
                f"channel must be between {_MIN_CHANNEL} and {_MAX_CHANNEL} (zero-based index)"
            )

        # Determine the desired action
        if desired_state is None:
            # Toggle the current state
            desired_state = not self.pwm_channels[channel]

        if desired_state:
            debug_string = "Enabling"
            channel_byte = 0x11 << channel  # enables PWM
        else:
            debug_string = "Disabling"
            channel_byte = 0x10 << channel  # disables PWM

        # Construct the command to toggle PWM synchronization
        command_prefix = _PWM_COMMANDS.get(self.device_type)
        if not command_prefix:
            raise NotSupportedByDevice(f"Unsupported device type for PWM sync: {self.device_type}")

        command = command_prefix + [channel_byte]
        _LOGGER.debug("%s PWM sync for channel %d: command %s", debug_string, channel, command)

        try:
            self.device.write(command)
            self.pwm_channels[channel] = desired_state  # Update state
        except Exception as e:
            _LOGGER.warning("Error writing to device: %s", e)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set a fixed speed for the specified channel.

        Parameters:
            channel: str or int - The name of the channel (e.g., '0') or the zero-based index of the channel
            duty: int or float - The desired speed percentage (0-100)
        """
        if isinstance(channel, str):
            channel_index = int(channel)
        else:
            channel_index = channel

        if not _MIN_CHANNEL <= channel_index <= _MAX_CHANNEL:
            raise ValueError(
                f"channel must be between {_MIN_CHANNEL} and {_MAX_CHANNEL} (zero-based index)"
            )

        # Check if PWM is on for the channel
        if self.pwm_channels[channel_index]:
            _LOGGER.debug(
                "Channel %d: PWM is enabled. "
                "Disabling PWM synchronization.",
                {channel_index + 1},
            )
            self.toggle_pwm_sync(channel_index, desired_state=False)

        duty = clamp(duty, 0, 100)
        speed_byte = self._calculate_speed_byte(duty)
        command = [224, channel_index + 32, 0, speed_byte]
        _LOGGER.debug(
            "Setting fixed speed for channel %d: duty %.1f%%, command %s",
            channel_index,
            duty,
            command,
        )
        try:
            self.device.write(command)
        except Exception as e:
            _LOGGER.error("Error writing to device: %s", e)
        time.sleep(0.1)  # Delay to prevent race conditions

        self.channel_speeds[channel_index] = duty

        _LOGGER.info("setting %s PWM duty to %d%%", channel_index + 1, duty)

    def query_current_speed(self, channel):
        """
        Query the actual fan speed from the device for a given channel by reading the
        controller's input report.

        For device types:
          - 'SL', 'AL', 'SLI': speed data begins at offset 1.
          - 'SLV2', 'ALV2': speed data begins at offset 2.

        Each channel's speed occupies 2 bytes and is the current RPM

        Parameters:
            channel (int): Zero-based index of the channel (0 to 3).

        Returns:
            int: The fan speed value as reported by the device, or raises an Assert if the read fails.
        """
        # Validate channel index
        if not _MIN_CHANNEL <= channel <= _MAX_CHANNEL:
            raise ValueError(
                f"Channel must be between {_MIN_CHANNEL} and {_MAX_CHANNEL} (zero-based index)"
            )

        # Determine offset based on the device type.
        if self.device_type in ["SL", "AL", "SLI"]:
            offset = 1
        elif self.device_type in ["SLV2", "ALV2"]:
            offset = 2
        else:
            raise NotSupportedByDevice(
                f"Unsupported device type for reading speed: {self.device_type}"
            )

        try:
            report = self.device.get_input_report(224, 65)
            _LOGGER.debug("Received speed report: %s", report)
        except Exception as e:
            raise AssertionError(f"Error reading speed report {e}")

        # # Calculate the starting index for this channel's speed value.
        start_index = offset + channel * 2
        _LOGGER.debug("start_index: %s", start_index)
        # Extract the 2 bytes corresponding to this channel.
        speed_bytes = report[start_index : start_index + 2]
        if len(speed_bytes) < 2:
            raise AssertionError(f"Report is too short for channel {channel}: {report}")

        speed_value = int.from_bytes(speed_bytes, byteorder="big")
        _LOGGER.debug(
            "Channel %d: extracted bytes %s -> speed value %d",
            channel,
            speed_bytes,
            speed_value,
        )

        return int(speed_value)

    def _calculate_speed_byte(self, speed):
        """Calculate the speed byte based on the device type and desired speed.

        Parameters:
            speed: int or float - The desired speed percentage (0-100)

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
