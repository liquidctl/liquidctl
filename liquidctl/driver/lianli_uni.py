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
import re
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


class LianLiUni(UsbHidDriver):
    """Driver for Lian Li Uni fan controllers."""

    _MATCHES = [
        (0x0CF2, 0x7750, "Lian Li Uni SL", {"device_type": "SL"}),
        (0x0CF2, 0xA100,"Lian Li Uni SL", {"device_type": "SL"}),
        (0x0CF2,0xA101,"Lian Li Uni AL",{"device_type": "AL"}),
        (0x0CF2,0xA102,"Lian Li Uni SL-Infinity",{"device_type": "SLI"}),
        (0x0CF2,0xA103,"Lian Li Uni SL V2",{"device_type": "SLV2"}),
        (0x0CF2, 0xA104, "Lian Li Uni AL V2", {"device_type": "ALV2"}),
        (0x0CF2, 0xA105, "Lian Li Uni SL V2", {"device_type": "SLV2"}),
    ]

    def __init__(self, device, description, **kwargs):
        """Initialize the Lian Li Uni driver."""
        super().__init__(device, description, **kwargs)
        self.device_type = kwargs.get("device_type")
        if not self.device_type:
            raise NotSupportedByDevice(
                f"Unknown device with PID: {hex(self.device.product_id)}"
            )
        # Variables for CoolerControl support
        self.speed_channels = ["channel1", "channel2", "channel3", "channel4"]
        self.channel_speeds = {}
        self.pwm_channels = {
            channel: False for channel in range(_MIN_CHANNEL, _MAX_CHANNEL + 1)
        }
        self.supports_cooling = True
        _LOGGER.info(
            "Initialized LianLiUni driver for device type: %s", self.device_type
        )

    def initialize(self, **kwargs):
        """Initialize the device and disable PWM synchronization on all channels."""
        _LOGGER.info("Initializing Lian Li Uni controller")

        # Disable PWM synchronization on all channels
        for channel in range(_MIN_CHANNEL, _MAX_CHANNEL + 1):
            self.toggle_pwm_sync(channel, desired_state=False)
            time.sleep(0.2)  # Delay to prevent race conditions

        return [
            ("Device", self.description, ""),
            ("Firmware version", "N/A", ""),
        ]

    def get_status(self, **kwargs):
        """Returns last set fan speed, resets if disconnected"""
        status = []

        for channel in range(_MIN_CHANNEL, _MAX_CHANNEL + 1):
            speed = self.channel_speeds.get(channel, 0.0)
            duty_name = f"Channel {channel + 1}"
            status.append((duty_name, float(speed), "%"))

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
            raise NotSupportedByDevice(
                f"Unsupported device type for PWM sync: {self.device_type}"
            )

        command = command_prefix + [channel_byte]
        _LOGGER.debug(
            "%s PWM sync for channel %d: command %s", debug_string, channel, command
        )

        try:
            self.device.write(command)
            self.pwm_channels[channel] = desired_state  # Update state
        except Exception as e:
            _LOGGER.warning("Error writing to device: %s", e)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set a fixed speed for the specified channel.

        Parameters:
            channel: str or int - The name of the channel (e.g., 'channel1') or the zero-based index of the channel
            duty: int or float - The desired speed percentage (0-100)
        """
        if isinstance(channel, str):
            channel_index = self._extract_channel_index(channel)
        else:
            channel_index = channel

        if not _MIN_CHANNEL <= channel_index <= _MAX_CHANNEL:
            raise ValueError(
                f"channel must be between {_MIN_CHANNEL} and {_MAX_CHANNEL} (zero-based index)"
            )

        # Check if PWM is on for the channel
        if self.pwm_channels[channel_index]:
            _LOGGER.warning(
                f"Cannot set fixed speed for Channel {channel_index + 1}: PWM is enabled. "
                "Please disable PWM first to set a fixed speed."
            )
            return

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

        _LOGGER.info(f"Fan speed for Channel {channel_index + 1} set to {duty}%")

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
            raise NotSupportedByDevice(
                f"Unsupported device type: {self.device_type}"
            )
        return speed_byte

    def _extract_channel_index(self, channel):
        """Extract the channel index from the channel name.

        Parameters:
            channel: str - The name of the channel (e.g., 'channel1')

        Returns:
            int - The zero-based index of the channel
        """
        match = re.search(r"(\d+)$", channel)
        if match:
            channel_number = int(match.group(1))
            if 1 <= channel_number <= (_MAX_CHANNEL + 1):
                return channel_number - 1
        raise ValueError(
            f"Invalid channel '{channel}'. Must be 'channel1' to 'channel{_MAX_CHANNEL + 1}'"
        )

    def disconnect(self, **kwargs):
        """Disconnect from the device."""
        _LOGGER.info("Disconnecting from device")
        self.device.close()
