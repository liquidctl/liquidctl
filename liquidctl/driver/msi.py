"""liquidctl drivers for MSI liquid coolers.

Supported devices:

- MPG Coreliquid K360

Copyright (C) 2021  Andrew Udvare and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections import namedtuple
from copy import copy
from enum import Enum, unique
from time import sleep
import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.util import RelaxedNamesEnum, clamp

_LOGGER = logging.getLogger(__name__)

_MAX_DATA_LENGTH = 185
_PER_LED_LENGTH = 720
_REPORT_LENGTH = 64
_CYCLE_NUMBER_STRIPE_TYPE_MAPPING = {0: 41, 1: 52, 2: 63, 3: 20, 4: 30}
_DEFAULT_FEATURE_DATA = (
    82, 1, 255, 0, 0, 40, 0, 255, 0, 128, 0, 1, 255, 0, 0, 40, 0, 255, 0,
    128, 0, 1, 255, 0, 0, 40, 0, 255, 0, 128, 0, 1, 255, 0, 0, 40, 0, 255, 0,
    128, 0, 20, 1, 255, 0, 0, 40, 0, 255, 0, 128, 0, 20, 1, 255, 0, 0, 40,
    0, 255, 0, 130, 76, 10, 1, 255, 0, 0, 40, 0, 255, 0, 128, 0, 26, 255, 0,
    0, 168, 0, 255, 0, 191, 0, 32, 255, 0, 0, 40, 0, 255, 0, 128, 0, 32,
    255, 0, 0, 40, 0, 255, 0, 128, 0, 32, 255, 0, 0, 40, 0, 255, 0, 128, 0, 32,
    255, 0, 0, 40, 0, 255, 0, 128, 0, 32, 255, 0, 0, 40, 0, 255, 0, 128, 0, 32,
    255, 0, 0, 40, 0, 255, 0, 128, 0, 32, 255, 0, 0, 40, 0, 255, 0, 128, 0, 32,
    255, 0, 0, 40, 0, 255, 0, 128, 0, 32, 255, 0, 0, 40, 0, 255, 0, 128, 0, 32,
    255, 0, 0, 40, 0, 255, 0, 128, 0, 0)

_DeviceSettings = namedtuple('DeviceSettings', [
    'stripe_or_fan', 'fan_type', 'corsair_device_quantity',
    'll120_outer_individual', 'led_num_jrainbow1', 'led_num_jrainbow2',
    'led_num_jcorsair'
])
_BoardSyncSettings = namedtuple('BoardSyncSettings', [
    'onboard_sync', 'combine_jrgb', 'combine_jpipe1', 'combine_jpipe2',
    'combine_jrainbow1', 'combine_jrainbow2', 'combine_jcorsair'
])
_StyleSettings = namedtuple(
    'StyleSettings',
    ['lighting_mode', 'speed', 'brightness', 'color_selection'])
_ColorSettings = namedtuple('ColorSettings', ['color1', 'color2'])
_FanConfig = namedtuple(
    'FanConfig',
    ['mode', 'duty0', 'duty1', 'duty2', 'duty3', 'duty4', 'duty5', 'duty6'])
_FanTempConfig = namedtuple(
    'FanTempConfig',
    ['mode', 'temp0', 'temp1', 'temp2', 'temp3', 'temp4', 'temp5', 'temp6'])


@unique
class _OLEDHardwareMonitorOffset(Enum):
    CPU_FREQ = 0
    CPU_TEMP = 1
    GPU_MEMORY_FREQ = 2
    GPU_USAGE = 3
    FAN_PUMP = 4
    FAN_RADIATOR = 5
    FAN_CPUMOS = 6
    MAXIMUM = 7


@unique
class _FanMode(RelaxedNamesEnum):
    SILENT = 0
    BALANCE = 1
    GAME = 2
    CUSTOMIZE = 3
    DEFAULT = 4
    SMART = 5

    @classmethod
    def _missing_(cls, value):
        _LOGGER.debug('falling back to BALANCE for _FanMode(%s)', value)
        return _FanMode.BALANCE


@unique
class _StripeOrFan(Enum):
    STRIPE = 0
    FAN = 1


@unique
class _FanType(Enum):
    SP = 0
    HD = 1
    LL = 2


class _LEDArea(Enum):
    JCORSAIR = 53
    JCORSAIR_OUTER_LL120 = 0x40
    JPIPE1 = 11
    JPIPE2 = 21
    JRAINBOW1 = 0x1F
    JRAINBOW2 = 42
    JRGB1 = 1
    JRGB2 = 174
    ONBOARD_LED_0 = 74
    ONBOARD_LED_1 = 84
    ONBOARD_LED_10 = 174
    ONBOARD_LED_2 = 94
    ONBOARD_LED_3 = 104
    ONBOARD_LED_4 = 114
    ONBOARD_LED_5 = 124
    ONBOARD_LED_6 = 134
    ONBOARD_LED_7 = 144
    ONBOARD_LED_8 = 154
    ONBOARD_LED_9 = 164


_CYCLE_NUMBER_LED_AREA_MAPPING = {
    _LEDArea.JPIPE1.value: 20,
    _LEDArea.JPIPE2.value: 30,
    _LEDArea.JRAINBOW1.value: 41,
    _LEDArea.JRAINBOW2.value: 52,
    _LEDArea.JCORSAIR.value: 63
}


@unique
class _LightingMode(RelaxedNamesEnum):
    BLINK = 19
    BREATHING = 2
    CLOCK = 20
    COLOR_PULSE = 21
    COLOR_RING = 15
    COLOR_RING_DOUBLE_FLASHING = 35
    COLOR_RING_FLASHING = 34
    COLOR_SHIFT = 22
    COLOR_WAVE = 23
    CORSAIR_IQUE = 37
    DISABLE = 0
    DISABLE2 = 33
    DOUBLE_FLASHING = 4
    DOUBLE_METEOR = 17
    ENERGY = 18
    FAN_CONTROL = 32
    FIRE = 38
    FLASHING = 3
    JAZZ = 12
    JRAINBOW = 28
    LAVA = 39
    LIGHTING = 5
    MARQUEE = 24
    METEOR = 7
    MOVIE = 14
    MSI_MARQUEE = 6
    MSI_RAINBOW = 9
    NO_ANIMATION = 1
    PLANETARY = 16
    PLAY = 13
    POP = 10
    RAINBOW = 25
    RAINBOW_DOUBLE_FLASHING = 30
    RAINBOW_FLAHING = 29
    RAINBOW_WAVE = 26
    RANDOM = 31
    RAP = 11
    STACK = 36
    VISOR = 27
    WATER_DROP = 8
    END = 40


@unique
class _Speed(RelaxedNamesEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


@unique
class _ColorSelection(Enum):
    RAINBOW_COLOR = 0
    USER_DEFINED = 1


@unique
class _JType(Enum):
    JRAINBOW = 3
    JCORSAIR = 4
    JONBOARD = 5


@unique
class _UploadType(Enum):
    BANNER = 0
    GIF = 1


class MpgCooler(UsbHidDriver):
    _MATCHES = [
        (0x0db0, 0xb130, 'MSI MPG Coreliquid K360', {
            'fan_count': 5
        }),
        (0x0db0, 0xca00, 'Unknown', {}),
        (0x0db0, 0xca02, 'Unknown', {}),
    ]

    def __init__(self, device, description, **kwargs):
        super().__init__(device, description, **kwargs)
        self._feature_data_per_led = bytearray(_PER_LED_LENGTH + 5)
        self._bytearray_oled_hardware_monitor_data = bytearray(_REPORT_LENGTH)
        self._per_led_rgb_jonboard = bytearray(_PER_LED_LENGTH)
        self._per_led_rgb_jrainbow1 = bytearray(_PER_LED_LENGTH)
        self._per_led_rgb_jrainbow2 = bytearray(_PER_LED_LENGTH)
        self._per_led_rgb_jcorsair = bytearray(_PER_LED_LENGTH)
        self._fan_count = kwargs.pop('fan_count', 0)
        # the following fields are only initialized in connect()
        self._data = None
        self._feature_data = None

    @classmethod
    def probe(cls, handle, vendor=None, product=None, release=None,
              serial=None, match=None, **kwargs):
        for vid, pid, desc, devargs in cls._MATCHES:
            if (vendor and vendor != vid) or handle.vendor_id != vid:
                continue
            if (product and product != pid) or handle.product_id != pid:
                continue
            if release and handle.release_number != release:
                continue
            if serial and handle.serial_number != serial:
                continue
            if match and match.lower() not in desc.lower():
                continuei
            if handle.hidinfo['usage_page'] != 0xff00:
                continue
            consargs = devargs.copy()
            consargs.update(kwargs)
            dev = cls(handle, desc, **consargs)
            _LOGGER.debug('%s identified: %s', cls.__name__, desc)
            yield dev

    def connect(self, **kwargs):
        ret = super().connect(**kwargs)
        self._data = kwargs.pop(
            'runtime_storage',
            RuntimeStorage(key_prefixes=[
                f'vid{self.vendor_id:04x}_pid{self.product_id:04x}',
                f'serial{self.serial_number}'
            ]))
        self._feature_data = self.device.get_feature_report(
            0x52, _MAX_DATA_LENGTH)
        return ret

    def initialize(self, **kwargs):
        pump_mode = kwargs.pop('pump_mode', 'balanced')
        direction = kwargs.pop('direction', 'default')
        if pump_mode == 'balanced':
            pump_mode = 'balance'
        pump_mode_int = _FanMode[pump_mode].value
        self._data.store('pump_mode', pump_mode_int)
        dir_int = 0
        if (direction not in ('default', 'top', 'bottom', 'left', 'right', '0',
                              '1', '2', '3')):
            _LOGGER.warning(
                'Unknown direction value. Correct values are 0-3 or top, '
                'bottom, left, right, default.')
        if direction in ('1', 'top'):
            dir_int = 1
        elif direction in ('2', 'left'):
            dir_int = 2
        elif direction in ('3', 'bottom'):
            dir_int = 3
        self._data.store('direction', dir_int)
        self.set_oled_brightness_and_direction(100, dir_int)
        if pump_mode_int == _FanMode.GAME.value:
            self.switch_to_game_mode()
        elif pump_mode_int == _FanMode.BALANCE.value:
            self.switch_to_balance_mode()
        elif pump_mode_int == _FanMode.DEFAULT.value:
            self.switch_to_default_mode()
        elif pump_mode_int == _FanMode.SILENT.value:
            self.switch_to_silent_mode()
        elif pump_mode_int == _FanMode.SMART.value:
            self.switch_to_smart_mode()

    def get_status(self, **kwargs):
        self._write((0x31, ))
        array = self._read()
        assert array[1] == 0x31, 'Unexpected value in response buffer'
        return [
            ('Fan 1 speed', array[2] + (array[3] << 8), 'rpm'),
            ('Fan 1 duty', array[0x16] + (array[0x17] << 8), '%'),
            ('Fan 2 speed', array[4] + (array[5] << 8), 'rpm'),
            ('Fan 2 duty', array[0x18] + (array[0x19] << 8), '%'),
            ('Fan 3 speed', array[6] + (array[7] << 8), 'rpm'),
            ('Fan 3 duty', array[0x1A] + (array[0x1B] << 8), '%'),
            ('Water block speed', array[8] + (array[9] << 8), 'rpm'),
            ('Water block duty', array[0x1C] + (array[0x1D] << 8), '%'),
            ('Pump speed', array[0xA] + (array[0xB] << 8), 'rpm'),
            ('Pump duty', array[0x1E] + (array[0x1F] << 8), '%'),
            ('Temperature inlet', array[12] + (array[13] << 8), '°C'),
            ('Temperature outlet', array[14] + (array[15] << 8), '°C'),
            ('Temperature sensor 1', array[16] + (array[17] << 8), '°C'),
            ('Temperature sensor 2', array[18] + (array[19] << 8), '°C'),
        ]

    def get_fan_config(self):
        self._write((0x32, ))
        buf = self._read()
        assert buf[1] == 0x32, 'Unexpected value in returned list'
        ret = []
        for mode_index in (2, 10, 18, 26, 34):
            ret.append(_FanConfig(*buf[mode_index:mode_index + 8]))
        return ret

    def set_fan_config(self, configs):
        buf = bytearray(_REPORT_LENGTH - 1)
        buf[0] = 0x40
        for config, offset in zip(configs, (1, 9, 17, 25, 33)):
            buf[offset] = config.mode
            buf[offset + 1] = config.duty0
            buf[offset + 2] = config.duty1
            buf[offset + 3] = config.duty2
            buf[offset + 4] = config.duty3
            buf[offset + 5] = config.duty4
            buf[offset + 6] = config.duty5
            buf[offset + 7] = config.duty6
        return self._write(buf)

    def get_fan_temp_config(self):
        self._write((0x33, ))
        buf = self._read()
        assert buf[1] == 0x32, 'Unexpected value in returned list'
        ret = []
        for mode_index in (2, 10, 18, 26, 34):
            ret.append(_FanTempConfig(*buf[mode_index:mode_index + 8]))
        return ret

    def set_fan_temp_config(self, configs):
        buf = bytearray(_REPORT_LENGTH)
        buf[0] = 0x41
        for config, offset in zip(configs, (1, 9, 17, 25, 33)):
            buf[offset] = config.mode
            buf[offset + 1] = config.temp0
            buf[offset + 2] = config.temp1
            buf[offset + 3] = config.temp2
            buf[offset + 4] = config.temp3
            buf[offset + 5] = config.temp4
            buf[offset + 6] = config.temp5
            buf[offset + 7] = config.temp6
        return self._write(buf)

    def get_current_model_index(self):
        self._write((0xb1, ), 0xcc, prefix=1)
        return self._read()[2]

    def get_firmware_version_aprom(self):
        self._write((0xb0, ), 0xcc, prefix=1)
        ret = self._read()
        return (
            ret[2] >> 4,  # high
            ret[2] & 0xF,  # low
        )

    def get_firmware_version_ldrom(self):
        self._write((0xb6, ), 0xcc, prefix=1)
        ret = self._read()
        return (
            ret[2] >> 4,  # high
            ret[2] & 0xF,  # low
        )

    def get_firmware_checksum_aprom(self):
        self._write((0xb0, ), 0xcc, prefix=1)
        ret = self._read()
        return (
            ret[8],  # high
            ret[9],  # low
        )

    def get_firmware_checksum_ldrom(self):
        self._write((0xb4, ), 0xcc, prefix=1)
        ret = self._read()
        return (
            ret[8],  # high
            ret[9],  # low
        )

    def get_all_hardware_monitor(self):
        self.device.clear_enqueued_reports()
        return self.device.get_feature_report(0xd0, _REPORT_LENGTH)

    def set_buzzer(self, type, frequency=650):
        return self._write((0xc2, 0, 0, 0, 0, 0, type, frequency & 0xFF,
                            (frequency >> 8) & 0xFF),
                           prefix=1)

    def set_led_global(self, on_off):
        return self._write((0xbb, 0, 0, 0, 0, int(on_off)), prefix=1)

    def get_led_global(self):
        self._write((0xba, ), 0xcc, prefix=1)
        ret = self._read()
        ok = len(ret) == _REPORT_LENGTH
        for j, _ in enumerate(ret):
            if ((j == 0 and ret[j] != 1) or (j == 1 and ret[j] != 90)
                    or (j == 6 and ret[j] not in (0, 1))):
                ok = False
            elif ret[j] != 0xcc:
                ok = False
        return ok and ret[6] == 1

    def get_led_pe0(self):
        self._write((0xa0, 0xcc, 0xcc, 0xcc, 0xcc, 0xcc, 0xcc, 0xcc, 1, 0xf2),
                    0xcc,
                    prefix=0xfa)
        ret = self._read()
        ok = True
        if (ret[0] != 250 or ret[1] != 160 or ret[2] != 205 or ret[9] != 1
                or ret[10] != 242 or ret[11] not in (0, 1)):
            ok = 0
        for j, n in enumerate(ret, start=23):
            if j > 29:
                break
            if n != 0:
                ok = False
        for j, n in enumerate(ret, start=30):
            if n != 0xcc:
                ok = False
        return ok and ret[11] == 1

    def get_device_settings(self):
        return _DeviceSettings(self._feature_data[61] & 1,
                               (self._feature_data[61] & 0xE) >> 1,
                               (self._feature_data[62] & 0xFC) >> 2,
                               self._feature_data[72] & 1,
                               self._feature_data[41], self._feature_data[52],
                               self._feature_data[63])

    def get_board_sync_settings(self):
        return _BoardSyncSettings((self._feature_data[82] & 1) == 1,
                                  (self._feature_data[78] & 0x80) >> 7 == 1,
                                  ((self._feature_data[82] >> 4) & 1) == 1,
                                  ((self._feature_data[82] >> 5) & 1) == 1,
                                  ((self._feature_data[82] >> 1) & 1) == 1,
                                  ((self._feature_data[82] >> 2) & 1) == 1,
                                  ((self._feature_data[82] >> 3) & 1) == 1)

    def get_style_settings(self, led_area):
        return _StyleSettings(self._feature_data[led_area],
                              (self._feature_data[led_area + 4] & 3),
                              (self._feature_data[led_area + 4] >> 2) & 0x1f,
                              ((self._feature_data[led_area + 8] & 0x80) >> 7))

    def get_color_settings(self, led_area):
        return _ColorSettings(self._feature_data[led_area + 1:led_area + 4],
                              self._feature_data[led_area + 5:led_area + 8])

    def get_current_led_setting(self):
        self._feature_data = self.device.get_feature_report(
            self._feature_data[0], _MAX_DATA_LENGTH)
        self._feature_data[62] = clamp(self._feature_data[62] - 4, 0, 255)
        return self._feature_data

    def get_all_board(self):
        return self.device.get_feature_report(0x52, _MAX_DATA_LENGTH)

    def get_oled_firmware_version(self):
        self._write((0xf1, ))
        return self._read()[2]

    def get_oled_gif_checksum(self):
        self._write((0xc2, ))
        ret = self._read()
        return (
            ret[3],  # high
            ret[2],  # low
        )

    def get_oled_banner_checksum(self):
        self._write((0xd2, ))
        buf = self._read()
        return (
            buf[3],  # high
            buf[2],  # low
        )

    def get_oled_m481checksum(self):
        self._write((0xf1, ))
        ret = self._read()
        return (
            ret[3],  # high
            ret[2],  # low
        )

    def set_volume(self, main, left, right):
        return self._write((0xc0, clamp(main, 0, 100), clamp(
            left, 0, 100), clamp(right, 0, 100)),
                           0xcc,
                           prefix=1)

    def set_oled_cpu_message(self, message):
        return self._write([0x90] +
                           list(message[:60].encode('ascii', 'ignore')))

    def set_oled_show_hardware_monitor(self,
                                       show_area,
                                       radiator_fan_smart_mode_on_off=True):
        if len(show_area) < 7:
            return False
        buf = bytearray(_REPORT_LENGTH)
        buf[0] = 0xd0
        buf[1] = 0x71
        for item in iter(_OLEDHardwareMonitorOffset):
            if item.value != _OLEDHardwareMonitorOffset.MAXIMUM and show_area[
                    item.value]:
                buf[item.value + 2] = 1
            if show_area[5]:
                buf[9] = 3 if radiator_fan_smart_mode_on_off else 1
        return self._write(buf[1:])

    def set_return_to_default(self):
        """--reset-all"""
        self._feature_data = copy(_DEFAULT_FEATURE_DATA)
        self._feature_data[184] = 1
        return self._set_all_board(self._feature_data)

    def _set_all_board(self, data):
        if data[41] > 200:
            data[41] = 100
        if data[52] > 240:
            data[52] = 100
        b = (data[62] & 0xFC) >> 2
        if ((b + 1) * data[63]) > 240:
            b = 5
            data[62] = b << 2
            data[63] = 12
        if len(data) < 185 or data[0] != 82:
            return False
        return bool(self.device.send_feature_report(data))

    def set_cycle_number(self, stripe_type, cycle_num):
        """Cycle number should NOT be clamped."""
        if stripe_type in _CYCLE_NUMBER_STRIPE_TYPE_MAPPING:
            self._feature_data[
                _CYCLE_NUMBER_STRIPE_TYPE_MAPPING[stripe_type]] = cycle_num

    def set_cycle_number_by_led_area(self, led_area, cycle_num):
        if led_area in _CYCLE_NUMBER_LED_AREA_MAPPING:
            self._feature_data[
                _CYCLE_NUMBER_LED_AREA_MAPPING[led_area]] = cycle_num

    def set_device_setting(self, stripe_or_fan, fan_type, corsair_device_qty,
                           ll120_outer_individual):
        corsair_device_qty = clamp(corsair_device_qty, 0, 63)
        ll120_outer_individual = clamp(int(ll120_outer_individual), 0, 1)
        self._feature_data[61] = ((self._feature_data[61]
                                   & 0x80) | (fan_type << 1) | stripe_or_fan)
        self._feature_data[62] = corsair_device_qty << 2
        self._feature_data[72] = (self._feature_data[72]
                                  | ll120_outer_individual)

    def set_board_sync_setting(self, onboard_sync, combine_jrgb,
                               combine_jpipe1, combine_jpipe2,
                               combine_jrainbow1, combine_jrainbow2,
                               combine_jcorsair):
        self._feature_data[82] |= clamp(int(onboard_sync), 0, 1)
        self._feature_data[78] |= 0b10000000 if combine_jrgb else 0
        self._feature_data[82] |= 0b00010000 if combine_jpipe1 else 0
        self._feature_data[82] |= 0b00100000 if combine_jpipe2 else 0
        self._feature_data[82] |= 0b00000010 if combine_jrainbow1 else 0
        self._feature_data[82] |= 0b00000100 if combine_jrainbow2 else 0
        self._feature_data[82] |= 0b00001000 if combine_jcorsair else 0

    def set_style_setting(self, led_area, lighting_mode, speed, brightness,
                          color_selection):
        """
        --led-area
        --lighting-mode
        --speed
        --brightness
        --color-selection
        """
        lighting_mode = clamp(lighting_mode, 0, 40)
        speed = clamp(speed, 0, 2)
        brightness = clamp(brightness, 0, 10)
        color_selection = clamp(color_selection, 0, 1)
        self._feature_data[led_area] = lighting_mode
        self._feature_data[led_area +
                           4] = ((self._feature_data[led_area + 4] & 0x80) |
                                 (brightness << 2) | speed)
        self._feature_data[led_area +
                           8] |= 0b10000000 if color_selection else 0

    def set_color_setting(self, led_area, color1_r, color1_g, color1_b,
                          color2_r, color2_g, color2_b):
        """
        --led-area
        --color1
        --color2
        """
        self._feature_data[led_area + 1] = clamp(led_area, 0, 174)
        self._feature_data[led_area + 2] = clamp(color1_r, 0, 255)
        self._feature_data[led_area + 3] = clamp(color1_g, 0, 255)
        self._feature_data[led_area + 4] = clamp(color1_b, 0, 255)
        self._feature_data[led_area + 5] = clamp(color2_r, 0, 255)
        self._feature_data[led_area + 6] = clamp(color2_g, 0, 255)
        self._feature_data[led_area + 7] = clamp(color2_b, 0, 255)

    def set_send_led_setting(self, save):
        """--persist-to-device ?"""
        self._feature_data[184] = int(bool(save))
        return self._set_all_board(self._feature_data)

    def set_direction_setting_b931_only(self, board_sync, jrainbow1, jrainbow2,
                                        jrainbow3, jrainbow4, jrainbow5):
        """--b931-direction ?"""
        self._feature_data[83] |= int(bool(board_sync))
        self._feature_data[39] |= int(bool(jrainbow1))
        self._feature_data[61] |= int(bool(jrainbow2))
        self._feature_data[50] |= int(bool(jrainbow3))
        self._feature_data[19] |= int(bool(jrainbow4))
        self._feature_data[29] |= int(bool(jrainbow5))

    def set_oled_user_message(self, message):
        """--message"""
        return self._write([0x93] + list((message[:61] +
                                          ' ').encode('ascii', 'ignore')))

    def set_oled_show_gameboot(self, selection, message):
        """
        --selection
        --message
        """
        return self._write([0x73, selection] +
                           list(message[:60].encode('ascii', 'ignore')))

    def set_oled_show_profile(self, profile_type=0, gif_no=0):
        """
        --profile-type
        --gif-number
        """
        data = [0x70, 0, gif_no]
        ret = self._write(data)
        data[1] = clamp(profile_type, 0, 1)
        return ret + self._write(data)

    def set_oled_show_banner(self, banner_type=0, bmp_no=0):
        """
        --banner-type
        --bmp-number
        """
        data = [0x79, 0, bmp_no]
        ret = self._write(data)
        data[1] = banner_type
        return ret + self._write(data)

    def set_oled_show_disable(self):
        """--disable-oled"""
        return self._write((0x7f, ))

    def _set_oled_upload(self, type, filename, type_num=0):
        start_cmd = 0xc0 if type == _UploadType.GIF else 0xd0
        with open(filename, 'rb') as f:
            content = f.read()
            l = len(content)
            if l > (2**20):
                raise ValueError('Too big')
        self._write(
            (start_cmd, l & 0xFF, (l >> 8) & 0xFF, (l >> 16) & 0xFF, (l >> 24)
             & 0xFF, type_num))
        sleep(((l / 4096 + 3) * 100) / 1000)
        sleep(1)
        n = 0
        while n < l:
            array = [start_cmd + 1]
            o = clamp(l - n, 0, 60)
            for k in range(1, o):
                array[k] = content[n + k - 2]
            n += o
            self._write(array)
            sleep(0.15)
        sleep(1)
        high, low = self.get_oled_gif_checksum()
        if low != (l & 0xFF) or high != ((l >> 8) & 0xFF):
            raise RuntimeError('Upload probably failed')

    def set_oled_upload_gif(self, filename, gif_no=6):
        """Default is 6 to not overwrite the default images.

        --upload-gif-file
        --upload-gif-number
        """
        self._set_oled_upload(_UploadType.GIF, filename, gif_no)

    def set_oled_upload_banner(self, filename, banner_no=4):
        """Default is 4 to not overwrite the default banners.

        --upload-banner-file
        --upload-banner-number
        """
        self._set_oled_upload(_UploadType.BANNER, filename, banner_no)

    def set_oled_clock(self, time):
        """
        --set-oled-clock now
        --set-old-clock ISOTIME
        """
        return self._write((
            0x83,
            time.year % 100,
            time.month,
            time.day,
            time.weekday(),
            time.hour,
            time.minute,
            time.second,
        ))

    def set_oled_show_clock(self, style):
        """--set-oled-mode clock"""
        return self._write((0x7a, clamp(style, 0, 2)))

    def set_oled_show_cpu_status(self, freq, temp):
        """--update-cpu-status"""
        freq = clamp(int(freq), 0, 65536)
        temp = clamp(int(temp), 0, 65536)
        return self._write((
            0x85,
            freq & 0xFF,
            (freq >> 8) & 0xFF,
            temp & 0xFF,
            (temp >> 8) & 0xFF,
        ))

    @staticmethod
    def _make_buffer(array, fill=0, total_size=_REPORT_LENGTH, prefix=0xd0):
        return bytearray([prefix] + list(array) +
                         ((total_size - (len(array) + 1)) * [fill]))

    def _write(self, array, fill=0, total_size=_REPORT_LENGTH, prefix=0xd0):
        self.device.clear_enqueued_reports()
        return self.device.write(
            self._make_buffer(array, fill, total_size, prefix))

    def _read(self, size=_REPORT_LENGTH):
        return bytearray(self.device.read(size))

    def set_oled_gpu_status(self, mem_freq, usage):
        """
        --set-gpu-memory-frequency
        --set-gpu-usage
        """
        mem_freq = clamp(int(mem_freq), 0, 65536)
        usage = clamp(int(usage), 0, 65536)
        return self._write((
            0x86,
            mem_freq & 0xFF,
            (mem_freq >> 8) & 0xFF,
            usage & 0xFF,
            (usage >> 8) & 0xFF,
        ))

    def set_oled_brightness_and_direction(self, brightness=100, direction=0):
        """
        --set-oled-brightness
        --direction
        """
        return self._write((0x7e, clamp(brightness, 0,
                                        100), clamp(direction, 0, 3)))

    def set_per_led_720byte(self, jtype, area, rgb_data):
        b = jtype
        if self.product_id != 0x7b10 and self.product_id != 0x7c34:
            b += 1
        if len(rgb_data) < 3:
            rgb_data = bytearray(3)
        rgb_data = rgb_data[:_PER_LED_LENGTH]
        self._feature_data_per_led = self._make_buffer(
            [0x37, b, area] + list(rgb_data),
            total_size=_PER_LED_LENGTH + 5,
            prefix=0x53)
        return self.device.send_feature_report(self._feature_data_per_led)

    def set_per_led_index(self,
                          jtype,
                          area,
                          index_and_rgb,
                          show=True,
                          led_count=0):
        """
        --set-per-led-index
        --jtype INT
        --area INT
        --index-and-rgb hex string?
        --show (or not passed)
        --maximum-leds INT
        """
        array = bytearray(1)
        if (len(index_and_rgb[1]) < 4 or len(index_and_rgb[0]) < 1
                or len(index_and_rgb) != 2):
            raise ValueError('index_and_rgb should be a 2-dimensional list')
        if jtype == _JType.JONBOARD.value:
            array = self._per_led_rgb_jonboard
        elif jtype == _JType.JRAINBOW.value:
            area = clamp(area, 0, 1)
            array = (self._per_led_rgb_jrainbow2
                     if area == 1 else self._per_led_rgb_jrainbow1)
        elif jtype == _JType.JCORSAIR.value:
            array = self._per_led_rgb_jcorsair
        end_index = led_count if led_count > 0 else len(index_and_rgb[0])
        for i in range(end_index):
            if index_and_rgb[i][0] * 3 + 2 < len(array):
                array[index_and_rgb[i][0] * 3] = index_and_rgb[i][1]
                array[index_and_rgb[i][0] * 3 + 1] = index_and_rgb[i][2]
                array[index_and_rgb[i][0] * 3 + 2] = index_and_rgb[i][3]
        if show:
            self.set_per_led_720byte(jtype, area, array)

    def set_switch_to_per_led_mode(self, jtype, area, show=False):
        """
        --switch-to-per-led-mode
        --jtype INT
        --area INT
        --show (or not passed)
        """
        if jtype == _JType.JONBOARD.value:
            self.set_style_setting(_LEDArea.ONBOARD_LED_0.value,
                                   _LightingMode.CORSAIR_IQUE.value,
                                   _Speed.MEDIUM.value, 10,
                                   _ColorSelection.USER_DEFINED.value)
            self._per_led_rgb_jonboard = bytearray(_PER_LED_LENGTH)
        elif jtype == _JType.JRAINBOW.value:
            if area == 0:
                self._per_led_rgb_jrainbow1 = bytearray(_PER_LED_LENGTH)
                self.set_cycle_number(0, 200)
                self.set_style_setting(_LEDArea.JRAINBOW1.value,
                                       _LightingMode.CORSAIR_IQUE.value,
                                       _Speed.MEDIUM.value, 10,
                                       _ColorSelection.USER_DEFINED.value)
            elif area == 1:
                self._per_led_rgb_jrainbow2 = bytearray(_PER_LED_LENGTH)
                self.set_cycle_number(1, 240)
                self.set_style_setting(_LEDArea.JRAINBOW2.value,
                                       _LightingMode.CORSAIR_IQUE.value,
                                       _Speed.MEDIUM.value, 10,
                                       _ColorSelection.USER_DEFINED.value)
        elif jtype == _JType.JCORSAIR.value:
            self._per_led_rgb_jcorsair = bytearray(_PER_LED_LENGTH)
            self.set_style_setting(_LEDArea.JCORSAIR.value,
                                   _LightingMode.CORSAIR_IQUE.value,
                                   _Speed.MEDIUM.value, 10,
                                   _ColorSelection.USER_DEFINED.value)
            if (((self._feature_data[61] & 0xE) >> 1) == 0
                    and (self._feature_data[61] & 1) == 1):
                self.set_device_setting(_StripeOrFan.FAN.value,
                                        _FanType.SP.value, 5, 0)
            else:
                self.set_cycle_number(2, 240)
                self.set_device_setting(_StripeOrFan.STRIPE.value,
                                        _FanType.HD.value, 0, 0)
        self.set_board_sync_setting(True, True, True, True, False, False,
                                    False)
        if show:
            self.set_send_led_setting(False)
            self.set_clear_per_led(jtype, area)

    def set_clear_per_led(self, jtype, area):
        """
        --clear-per-led
        --jtype
        --area
        """
        return self.set_per_led_720byte(jtype, area, bytearray(3))

    def _set_all(self, which, r=0, g=0, b=0):
        self.set_board_sync_setting(True, True, True, True, True, True, True)
        self.set_style_setting(_LEDArea.ONBOARD_LED_0, which, 1, 10, 1)
        self.set_color_setting(_LEDArea.ONBOARD_LED_0, r, g, b, r, g, b)
        self.set_send_led_setting(False)

    def set_all_disable(self):
        """--led-disable"""
        self._set_all(_LightingMode.DISABLE.value)

    def set_all_static(self, r, g, b):
        """--led-all-static"""
        self._set_all(_LightingMode.NO_ANIMATION.value, r, g, b)

    def set_all_flashing(self, r, g, b):
        """--led-all-flashing"""
        self._set_all(_LightingMode.FLASHING.value, r, g, b)

    def set_all_breathing(self, r, g, b):
        """--led-all-breathing"""
        self._set_all(_LightingMode.BREATHING.value, r, g, b)

    def set_all_rainbow_wave(self):
        """--led-all-rainbow-wave"""
        self._set_all(_LightingMode.RAINBOW_WAVE.value)

    def switch_to_balance_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.BALANCE.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.BALANCE.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)

    def switch_to_game_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.GAME.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.GAME.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)

    def switch_to_silent_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.SILENT.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.SILENT.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)

    def switch_to_smart_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.SMART.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.SMART.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)

    def switch_to_default_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.DEFAULT.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.DEFAULT.value, 0, 0, 0, 0, 0, 0, 0)] *
            self._fan_count)

    # def set_oled_cpu_message(self, message):
    #     return self._write([0x90] +
    #                        list(message[:60].encode('ascii', 'ignore')))

    # def set_oled_memory_message(self, message):
    #     return self._write([0x91] +
    #                        list(message[:60].encode('ascii', 'ignore')))

    # def set_oled_vga_message(self, message):
    #     return self._write([0x92] +
    #                        list(message[:60].encode('ascii', 'ignore')))

    # def set_oled_show_system_message(self):
    #     return self._write((0x72, ))

    # def set_oled_show_user_message(self):
    #     return self._write((0x74, ))

    # def set_oled_start_isp_process(self):
    #     return self._write((0xfa, ))

    # def set_oled_show_demo_mode(self):
    #     return self._write((0x77, 0xff))

    # def set_reset_mcu(self):
    #     return self._write((0xd0, ), 0xcc, prefix=1)
