from liquidctl.driver.usb import UsbHidDriver

_SYNC_ARGB_COMMANDS = {
    'SL': [224, 16, 48, 0, 0, 0],
    'AL': [224, 16, 65, 0, 0, 0],
    'SL-Infinity': [224, 16, 97, 0, 0, 0],
    'SL v2': [224, 16, 97, 0, 0, 0],
    'AL v2': [224, 16, 97, 0, 0, 0],
}
_SYNC_CHANNEL_COMMANDS = {
    'SL': [224, 16, 49],
    'AL': [224, 16, 66],
    'SL-Infinity': [224, 16, 98],
    'SL v2': [224, 16, 98],
    'AL v2': [224, 16, 98],
}

_PIDS = {
    'SL': [0x7750, 0xa100],
    'AL': [0xa101],
    'SL-Infinity': [0xa102],
    'SL v2': [0xa103, 0xa105],
    'AL v2': [0xa104],
}

_CHANNEL_BYTE_MASK = 0x10
_CHANNEL_PWM_MASK = 0x1

class LianLiUNI(UsbHidDriver):
    """Lian-Li Uni fans"""

    _MATCHES = [
        (0x0cf2, 0x7750, 'LianLi-UNI SL',
            {'fan_count': 6, 'temp_probs': 0, 'led_channels': 2}),
        (0x0cf2, 0xa100, 'LianLi-UNI SL',
            {'fan_count': 6, 'temp_probs': 0, 'led_channels': 2}),
        (0x0cf2, 0xa101, 'LianLi-UNI AL',
            {'fan_count': 6, 'temp_probs': 0, 'led_channels': 2}),
        (0x0cf2, 0xa102, 'LianLi-UNI SL-Infinity',
            {'fan_count': 6, 'temp_probs': 0, 'led_channels': 2}),
        (0x0cf2, 0xa103, 'LianLi-UNI SL v2',
            {'fan_count': 6, 'temp_probs': 0, 'led_channels': 2}),
        (0x0cf2, 0xa105, 'LianLi-UNI SL v2',
            {'fan_count': 6, 'temp_probs': 0, 'led_channels': 2}),
        (0x0cf2, 0xa104, 'LianLi-UNI AL v2',
            {'fan_count': 6, 'temp_probs': 0, 'led_channels': 2}),
    ]

    def __init__(self, device, description, fan_count, temp_probs, led_channels, **kwargs):
        super().__init__(device, description, **kwargs)

        self.variant = next(key for key in _PIDS if self.product_id in _PIDS[key])

    def sync_rgb_header(self, sync_rgb):
        self._write(
            _SYNC_ARGB_COMMANDS[self.variant][0:3],
            0x1 if sync_byte else 0x0,
            _SYNC_ARGB_COMMANDS[self.variant][3:]
        )

    def set_channel_pwm(self, channel):
        # TODO check channel at least 1
        channel_byte = _CHANNEL_BYTE_MASK << channel

        channel_byte = channel_byte | _CHANNEL_PWM_MASK << channel

        self.device.write(_SYNC_CHANNEL_COMMANDS[self.variant] + channel_byte)


    def set_channel_speed(self, channel, speed):
        speed = min(speed, 100.0)
        command = [224, channel + 32, 0]

        if self.variant in ['SL', 'AL']:
            command.append((800.0 + (11.0 * speed)) / 19)
        elif self.variant == 'SL-Infinity':
            command.append((250.0 + (17.5 * speed)) / 20)
        elif self.variant in ['SL v2', 'AL v2']:
            command.append((200.0 + (19.0 * speed)) / 21)

        self.device.write(command)

    def set_channel_profile(self, channel, speed, mode):
        if mode == 'pwm':
            self.set_channel_pwm(channel)
        else:
            self.set_channel_speed(channel, speed)
