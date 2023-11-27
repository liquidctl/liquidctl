from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice


_SYNC_ARGB_COMMAND_LENGTH = 7
_SYNC_CHANNEL_COMMAND_LENGTH = 4

_SYNC_ARGB_COMMANDS = {
    "SL": [224, 16, 48, 0, 0, 0],
    "AL": [224, 16, 65, 0, 0, 0],
    "SL-Infinity": [224, 16, 97, 0, 0, 0],
    "SL v2": [224, 16, 97, 0, 0, 0],
    "AL v2": [224, 16, 97, 0, 0, 0],
}
_SYNC_CHANNEL_COMMANDS = {
    "SL": [224, 16, 49],
    "AL": [224, 16, 66],
    "SL-Infinity": [224, 16, 98],
    "SL v2": [224, 16, 98],
    "AL v2": [224, 16, 98],
}

_PIDS = {
    "SL": [0x7750, 0xA100],
    "AL": [0xA101],
    "SL-Infinity": [0xA102],
    "SL v2": [0xA103, 0xA105],
    "AL v2": [0xA104],
}

_CHANNEL_BYTE_MASK = 0x10
_CHANNEL_PWM_MASK = 0x1

_CHANNEL_PARSING_ERROR = "unknown channel, should be one of fan1..6"


class LianLiUNI(UsbHidDriver):
    """Lian-Li Uni fans"""

    _MATCHES = [
        (0x0CF2, 0x7750, "LianLi-UNI SL", {"fan_count": 1, "temp_probs": 0, "led_channels": 2}),
        (0x0CF2, 0xA100, "LianLi-UNI SL", {"fan_count": 1, "temp_probs": 0, "led_channels": 2}),
        (0x0CF2, 0xA101, "LianLi-UNI AL", {"fan_count": 1, "temp_probs": 0, "led_channels": 2}),
        (
            0x0CF2,
            0xA102,
            "LianLi-UNI SL-Infinity",
            {"fan_count": 4, "temp_probs": 0, "led_channels": 2},
        ),
        (0x0CF2, 0xA103, "LianLi-UNI SL v2", {"fan_count": 1, "temp_probs": 0, "led_channels": 2}),
        (0x0CF2, 0xA105, "LianLi-UNI SL v2", {"fan_count": 1, "temp_probs": 0, "led_channels": 2}),
        (0x0CF2, 0xA104, "LianLi-UNI AL v2", {"fan_count": 1, "temp_probs": 0, "led_channels": 2}),
    ]

    def __init__(self, device, description, fan_count, temp_probs, led_channels, **kwargs):
        super().__init__(device, description, **kwargs)

        self.variant = next(key for key in _PIDS if self.product_id in _PIDS[key])

    def initialize(self, direct_access=False, fan_mode={}, **kwargs):
        if "rgb_sync" in kwargs and kwargs["rgb_sync"]:
            self._set_rgb_sync()

    def set_fixed_speed(self, channel, duty, **kwargs):
        channel = self._parse_channel(channel)

        channel_byte = _CHANNEL_BYTE_MASK << channel

        is_pwm = False
        if (
            kwargs["fan_mode"]
            and channel in kwargs["fan_mode"]
            and kwargs["fan_mode"][channel] == "pwm"
        ):
            channel_byte = self._set_pwm_sync(channel_byte, channel)
            is_pwm = True

        self.device.write(bytearray(_SYNC_CHANNEL_COMMANDS[self.variant] + [channel_byte]))

        if is_pwm:
            self._set_manual_rpm(channel, duty)

    def _parse_channel(self, channel):
        channel = channel.split("fan")
        error = False

        if len(channel) != 2:
            error = True
        else:
            try:
                channel = int(channel[1])
                if channel not in range(1, 7):
                    error = True
            except ValueError:
                error = True

        if error:
            raise ValueError(_CHANNEL_PARSING_ERROR)
        return channel

    def _set_rgb_sync(self, sync_rgb):
        buf = bytearray(_SYNC_ARGB_COMMAND_LENGTH)

        buf[0:3] = _SYNC_ARGB_COMMANDS[self.variant][0:3]
        buf[3] = 0x1 if sync_byte else 0x0
        buf[4:] = _SYNC_ARGB_COMMANDS[self.variant][3:]

        self.device.write(buf)

    def _set_pwm_sync(self, channel_byte, channel):
        return channel_byte | _CHANNEL_PWM_MASK << channel

    def _set_manual_rpm(self, channel, speed):
        speed = min(speed, 100.0)
        command = [224, channel + 32, 0]

        if self.variant in ["SL", "AL"]:
            command.append((800.0 + (11.0 * speed)) / 19)
        elif self.variant == "SL-Infinity":
            command.append((250.0 + (17.5 * speed)) / 20)
        elif self.variant in ["SL v2", "AL v2"]:
            command.append((200.0 + (19.0 * speed)) / 21)

        self.device.write(bytearray(command))

    def set_screen(self, channel, mode, value, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()
