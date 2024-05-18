"""liquidctl drivers for MSI liquid coolers.

Supported devices:

- MPG Coreliquid K360

Copyright (C) 2021  Andrew Udvare, Aapo Kössi and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

from collections import namedtuple
from collections.abc import Sequence
from copy import copy
from enum import Enum, unique
from time import sleep
import logging
import io
from PIL import Image

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.util import RelaxedNamesEnum, check_unsafe, clamp, u16le_from

_LOGGER = logging.getLogger(__name__)

EXTRA_USAGE_PAGE = 0x0001
_MAX_DATA_LENGTH = 185
_PER_LED_LENGTH = 720
_REPORT_LENGTH = 64
_MAX_DUTIES = 7
_RAD_FAN_COUNT = 3
_CYCLE_NUMBER_STRIPE_TYPE_MAPPING = {0: 41, 1: 52, 2: 63, 3: 20, 4: 30}
# fmt: off
_DEFAULT_FEATURE_DATA = [
     82,   1, 255,   0,   0,  40,   0, 255,
      0, 128,   0,   1, 255,   0,   0,  40,
      0, 255,   0, 128,   0,   1, 255,   0,
      0,  40,   0, 255,   0, 128,   0,   1,
    255,   0,   0,  40,   0, 255,   0, 128,
      0,  20,   1, 255,   0,   0,  40,   0,
    255,   0, 128,   0,  20,   1, 255,   0,
      0,  40,   0, 255,   0, 130,  76,  10,
      1, 255,   0,   0,  40,   0, 255,   0,
    128,   0,  26, 255,   0,   0, 168,   0,
    255,   0, 191,   0,  32, 255,   0,   0,
     40,   0, 255,   0, 128,   0,  32, 255,
      0,   0,  40,   0, 255,   0, 128,   0,
     32, 255,   0,   0,  40,   0, 255,   0,
    128,   0,  32, 255,   0,   0,  40,   0,
    255,   0, 128,   0,  32, 255,   0,   0,
     40,   0, 255,   0, 128,   0,  32, 255,
      0,   0,  40,   0, 255,   0, 128,   0,
     32, 255,   0,   0,  40,   0, 255,   0,
    128,   0,  32, 255,   0,   0,  40,   0,
    255,   0, 128,   0,  32, 255,   0,   0,
     40,   0, 255,   0, 128,   0,  32, 255,
      0,   0,  40,   0, 255,   0, 128,   0,
      0
]
# fmt: on
_DeviceSettings = namedtuple(
    "DeviceSettings",
    [
        "stripe_or_fan",
        "fan_type",
        "corsair_device_quantity",
        "ll120_outer_individual",
        "led_num_jrainbow1",
        "led_num_jrainbow2",
        "led_num_jcorsair",
    ],
)
_BoardSyncSettings = namedtuple(
    "BoardSyncSettings",
    [
        "onboard_sync",
        "combine_jrgb",
        "combine_jpipe1",
        "combine_jpipe2",
        "combine_jrainbow1",
        "combine_jrainbow2",
        "combine_jcorsair",
    ],
)
_StyleSettings = namedtuple(
    "StyleSettings", ["lighting_mode", "speed", "brightness", "color_selection"]
)
_ColorSettings = namedtuple("ColorSettings", ["color1", "color2"])
_FanConfig = namedtuple(
    "FanConfig", ["mode", "duty0", "duty1", "duty2", "duty3", "duty4", "duty5", "duty6"]
)
_FanTempConfig = namedtuple(
    "FanTempConfig", ["mode", "temp0", "temp1", "temp2", "temp3", "temp4", "temp5", "temp6"]
)


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
        _LOGGER.debug("falling back to BALANCE for _FanMode(%s)", value)
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
    _LEDArea.JCORSAIR.value: 63,
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
    LIGHTNING = 5
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
    RAINBOW_FLASHING = 29
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


@unique
class _ScreenMode(Enum):
    HARDWARE = 0
    IMAGE = 1
    BANNER = 3
    CLOCK = 4
    SETTINGS = 5
    DISABLED = 6


class MpgCooler(UsbHidDriver):
    _COLOR_MODES = {
        "blink": _LightingMode.BLINK,
        "breathing": _LightingMode.BREATHING,
        "clock": _LightingMode.CLOCK,
        "color pulse": _LightingMode.COLOR_PULSE,
        "color ring": _LightingMode.COLOR_RING,
        "color ring double flashing": _LightingMode.COLOR_RING_DOUBLE_FLASHING,
        "color ring flashing": _LightingMode.COLOR_RING_FLASHING,
        "color shift": _LightingMode.COLOR_SHIFT,
        "color wave": _LightingMode.COLOR_WAVE,
        "corsair ique": _LightingMode.CORSAIR_IQUE,
        "disable": _LightingMode.DISABLE,
        "disable2": _LightingMode.DISABLE2,
        "double flashing": _LightingMode.DOUBLE_FLASHING,
        "double meteor": _LightingMode.DOUBLE_METEOR,
        "energy": _LightingMode.ENERGY,
        "fan control": _LightingMode.FAN_CONTROL,
        "fire": _LightingMode.FIRE,
        "flashing": _LightingMode.FLASHING,
        "jazz": _LightingMode.JAZZ,
        "jrainbow": _LightingMode.JRAINBOW,
        "lava": _LightingMode.LAVA,
        "lightning": _LightingMode.LIGHTNING,
        "marquee": _LightingMode.MARQUEE,
        "meteor": _LightingMode.METEOR,
        "movie": _LightingMode.MOVIE,
        "msi marquee": _LightingMode.MSI_MARQUEE,
        "msi rainbow": _LightingMode.MSI_RAINBOW,
        "steady": _LightingMode.NO_ANIMATION,
        "planetary": _LightingMode.PLANETARY,
        "play": _LightingMode.PLAY,
        "pop": _LightingMode.POP,
        "rainbow": _LightingMode.RAINBOW,
        "rainbow double flashing": _LightingMode.RAINBOW_DOUBLE_FLASHING,
        "rainbow flashing": _LightingMode.RAINBOW_FLASHING,
        "rainbow wave": _LightingMode.RAINBOW_WAVE,
        "random": _LightingMode.RANDOM,
        "rap": _LightingMode.RAP,
        "stack": _LightingMode.STACK,
        "visor": _LightingMode.VISOR,
        "water drop": _LightingMode.WATER_DROP,
        "end": _LightingMode.END,
    }
    BUILTIN_MODES = {
        "silent": _FanMode.SILENT.value,
        "balanced": _FanMode.BALANCE.value,
        "game": _FanMode.GAME.value,
        "default": _FanMode.DEFAULT.value,
        "smart": _FanMode.SMART.value,
    }
    SCREEN_MODES = {
        "hardware": _ScreenMode.HARDWARE,
        "image": _ScreenMode.IMAGE,
        "banner": _ScreenMode.BANNER,
        "clock": _ScreenMode.CLOCK,
        "settings": _ScreenMode.SETTINGS,
        "disable": _ScreenMode.DISABLED,
    }
    HWMONITORDISPLAY = {
        "cpu_freq": _OLEDHardwareMonitorOffset.CPU_FREQ,
        "cpu_temp": _OLEDHardwareMonitorOffset.CPU_TEMP,
        "gpu_freq": _OLEDHardwareMonitorOffset.GPU_MEMORY_FREQ,
        "gpu_usage": _OLEDHardwareMonitorOffset.GPU_USAGE,
        "fan_pump": _OLEDHardwareMonitorOffset.FAN_PUMP,
        "fan_radiator": _OLEDHardwareMonitorOffset.FAN_RADIATOR,
        "fan_cpumos": _OLEDHardwareMonitorOffset.FAN_CPUMOS,
    }
    _MATCHES = [
        (
            0x0DB0,
            0xB130,
            "MSI MPG Coreliquid K360",
            {"fan_count": 5},
        ),
        (
            0x0DB0,
            0xCA00,
            "Suspected MSI MPG Coreliquid",
            {"_unsafe": ["experimental_coreliquid_cooler"]},
        ),
        (
            0x0DB0,
            0xCA02,
            "Suspected MSI MPG Coreliquid",
            {"_unsafe": ["experimental_coreliquid_cooler"]},
        ),
    ]
    HAS_AUTOCONTROL = True

    def __init__(self, device, description, _unsafe=[], **kwargs):
        super().__init__(device, description, **kwargs)
        self._UNSAFE = _unsafe
        self._feature_data_per_led = bytearray(_PER_LED_LENGTH + 5)
        self._bytearray_oled_hardware_monitor_data = bytearray(_REPORT_LENGTH)
        self._per_led_rgb_jonboard = bytearray(_PER_LED_LENGTH)
        self._per_led_rgb_jrainbow1 = bytearray(_PER_LED_LENGTH)
        self._per_led_rgb_jrainbow2 = bytearray(_PER_LED_LENGTH)
        self._per_led_rgb_jcorsair = bytearray(_PER_LED_LENGTH)
        self._fan_count = kwargs.pop("fan_count", 5)
        # the following fields are only initialized in connect()
        self._data = None
        self._feature_data = None

    @classmethod
    def probe(cls, handle, **kwargs):
        """Probe `handle` and yield corresponding driver instances.

        These devices have multiple top-level HID usages, and HidapiDevice
        handles matching other usages have to be ignored.
        """

        # if usage_page/usage are not available due to hidapi limitations
        # (version, platform or backend), they are unfortunately left
        # uninitialized; because of this, we explicitly exclude the undesired
        # usage_page, and assume in all other cases that we either
        # have the desired usage page, or that on that system a
        # single handle is returned for that device interface (see: #259)

        if handle.hidinfo["usage_page"] == EXTRA_USAGE_PAGE:
            return
        yield from super().probe(handle, **kwargs)

    def connect(self, **kwargs):
        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        ret = super().connect(**kwargs)
        self._data = kwargs.pop(
            "runtime_storage",
            RuntimeStorage(
                key_prefixes=[
                    f"vid{self.vendor_id:04x}_pid{self.product_id:04x}",
                    f"serial{self.serial_number}",
                ]
            ),
        )
        self._feature_data = self.device.get_feature_report(0x52, _MAX_DATA_LENGTH)
        self._fan_cfg = self.get_fan_config()
        self._fan_temp_cfg = self.get_fan_temp_config()
        aprom_hi, aprom_lo = self.get_firmware_version_aprom()
        self._aprom_firmware_version = aprom_hi << 4 + aprom_lo
        ldrom_hi, ldrom_lo = self.get_firmware_version_ldrom()
        self._ldrom_firmware_version = ldrom_hi << 4 + ldrom_lo
        self._oled_firmware_version = self.get_oled_firmware_version()

        return ret

    def initialize(self, **kwargs):
        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        pump_mode = kwargs.pop("pump_mode", "balanced")
        direction = kwargs.pop("direction", "default")
        if pump_mode == "balanced":
            pump_mode = "balance"
        pump_mode_int = _FanMode[pump_mode].value
        self._data.store("pump_mode", pump_mode_int)
        dir_int = 0
        if direction not in ("default", "top", "bottom", "left", "right", "0", "1", "2", "3"):
            _LOGGER.warning(
                "unknown direction value: correct values are 0-3 or top, "
                "bottom, left, right, default."
            )
        if direction in ("1", "left"):
            dir_int = 1
        elif direction in ("2", "bottom"):
            dir_int = 2
        elif direction in ("3", "right"):
            dir_int = 3
        self._data.store("direction", dir_int)
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

        return [
            ("Display firmware version", self._oled_firmware_version, ""),
            ("APROM firmware version", self._aprom_firmware_version, ""),
            ("LDROM firmware version", self._ldrom_firmware_version, ""),
            ("Serial number", self.serial_number, ""),
            ("Pump mode", pump_mode, ""),
        ]

    def get_status(self, **kwargs):
        if not check_unsafe(*self._UNSAFE, **kwargs):
            _LOGGER.warning(
                f"{self.description}: disabled, requires unsafe features "
                f"'{','.join(self._UNSAFE)}'"
            )
            return []
        self._write((0x31,))
        array = self._read()
        assert array[1] == 0x31, "Unexpected value in response buffer"
        return [
            ("Fan 1 speed", u16le_from(array, offset=2), "rpm"),
            ("Fan 1 duty", u16le_from(array, offset=0x16), "%"),
            ("Fan 2 speed", u16le_from(array, offset=4), "rpm"),
            ("Fan 2 duty", u16le_from(array, offset=0x18), "%"),
            ("Fan 3 speed", u16le_from(array, offset=6), "rpm"),
            ("Fan 3 duty", u16le_from(array, offset=0x1A), "%"),
            ("Water block speed", u16le_from(array, offset=8), "rpm"),
            ("Water block duty", u16le_from(array, offset=0x1C), "%"),
            ("Pump speed", u16le_from(array, offset=0xA), "rpm"),
            ("Pump duty", u16le_from(array, offset=0x1E), "%"),
            # Temperature values are not used by the K360 model, it only reports
            # some default values that are not meaningful for the user.
            # https://github.com/liquidctl/liquidctl/pull/564#discussion_r1450753883
            # ('Temperature inlet', u16le_from(array, offset=12), '°C'),
            # ('Temperature outlet', u16le_from(array, offset=14), '°C'),
            # ('Temperature sensor 1', u16le_from(array, offset=16), '°C'),
            # ('Temperature sensor 2', u16le_from(array, offset=18), '°C'),
        ]

    def set_time(self, time, **kwargs):
        check_unsafe(*self._UNSAFE, error=True, **kwargs)
        return self.set_oled_clock(time)

    def set_hardware_status(self, T, cpu_f=0, gpu_f=0, gpu_U=0, **kwargs):
        check_unsafe(*self._UNSAFE, error=True, **kwargs)
        self.set_oled_show_cpu_status(cpu_f, T)
        self.set_oled_gpu_status(gpu_f, gpu_U)

    def get_fan_config(self):
        self._write((0x32,))
        buf = self._read()
        assert buf[1] == 0x32, "Unexpected value in returned list"
        ret = []
        for mode_index in (2, 10, 18, 26, 34):
            ret.append(_FanConfig(*buf[mode_index : mode_index + 8]))
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
        self._write((0x33,))
        buf = self._read()
        assert buf[1] == 0x32, "Unexpected value in returned list"
        ret = []
        for mode_index in (2, 10, 18, 26, 34):
            ret.append(_FanTempConfig(*buf[mode_index : mode_index + 8]))
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

    def _send_safe_temp(self):
        _LOGGER.info(
            "duty profiles on this device require continuous communication, "
            "setting initial control temperature to 100C for safety."
        )
        self.set_oled_show_cpu_status(0, 100)

    def set_profiles(self, channels, profiles, **kwargs):
        """
        Set custom or device preset fan curve for multiple channels.

        NOTE: The device will not keep updating its duty cycles
        automatically after this function is called. The device
        manages duties according to the previous temperature
        sent to it via device.set_oled_show_cpu_status()
        """
        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        fan_cfg = self.get_fan_config()
        fan_temp_cfg = self.get_fan_temp_config()
        channel_idx = [self.parse_channel(ch) for ch in channels]

        for idx, prof in zip(channel_idx, profiles):
            if type(prof) == str:
                fanmode = _FanConfig(self.BUILTIN_MODES[prof], 0, 0, 0, 0, 0, 0, 0)
                tempmode = _FanTempConfig(self.BUILTIN_MODES[prof], 0, 0, 0, 0, 0, 0, 0)
            else:
                duties, temps = map(self.clamp_and_pad, zip(*prof))
                fanmode = _FanConfig(_FanMode.CUSTOMIZE.value, *duties)
                tempmode = _FanTempConfig(_FanMode.CUSTOMIZE.value, *temps)
            for i in idx:
                fan_cfg[i] = fanmode
                fan_temp_cfg[i] = tempmode

        self._fan_cfg = fan_cfg
        self._fan_temp_cfg = fan_temp_cfg

        self.set_fan_config(fan_cfg)
        self.set_fan_temp_config(fan_temp_cfg)
        self._send_safe_temp()

    def parse_channel(self, channel):
        if channel == "pump":
            return [4]
        elif channel == "fans":
            return range(_RAD_FAN_COUNT)
        elif channel == "waterblock-fan":
            return [3]
        elif channel[:3] == "fan" and (int(channel[3:]) in range(_RAD_FAN_COUNT)):
            return [int(channel[3:])]
        else:
            raise ValueError(
                'unknown channel, should be "fans", "fan1", "fan2", "fan3", "waterblock-fan" or "pump".'
            )

    @staticmethod
    def clamp_and_pad(values):
        return ([clamp(v, 0, 100) for v in values] + [0] * _MAX_DUTIES)[:_MAX_DUTIES]

    def set_speed_profile(self, channel, profile, **kwargs):
        """
        Set custom fan curve for a given channel.

        NOTE: The device will not keep updating its duty cycles
        automatically after this function is called. The device
        manages duties according to the previous temperature
        sent to it via device.set_oled_show_cpu_status()
        """

        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        duties_temps = list(zip(*profile))
        duties, temps = tuple(self.clamp_and_pad(v) for v in duties_temps)

        for i in self.parse_channel(channel):
            self._fan_cfg[i] = _FanConfig(_FanMode.CUSTOMIZE.value, *duties)
            self._fan_temp_cfg[i] = _FanTempConfig(_FanMode.CUSTOMIZE.value, *temps)

        self.set_fan_config(self._fan_cfg)
        self.set_fan_temp_config(self._fan_temp_cfg)
        self._send_safe_temp()

    def set_fixed_speed(self, channel, duty, **kwargs):
        channel_nums = self.parse_channel(channel)

        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        for i in channel_nums:
            self._fan_cfg[i] = _FanConfig(_FanMode.CUSTOMIZE.value, *([duty] * _MAX_DUTIES))
            self._fan_temp_cfg[i] = _FanTempConfig(_FanMode.CUSTOMIZE.value, 0, 0, 0, 0, 0, 0, 0)

        self.set_fan_config(self._fan_cfg)
        self.set_fan_temp_config(self._fan_temp_cfg)

    def set_color(self, channel, mode, colors, speed=1, brightness=10, color_selection=1, **kwargs):
        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        assert channel == "sync", f'Unexpected lighting channel {channel}. Supported: "sync"'
        colors = list(colors)
        if not colors:
            color_selection = 0
        else:
            if len(colors) == 1:
                colors.append((0, 0, 0))
            self.set_color_setting(_LEDArea.JRAINBOW1.value, *colors[0], *colors[1])

        mode = self._COLOR_MODES[mode].value
        self.set_style_setting(
            _LEDArea.JRAINBOW1.value, mode, int(speed), brightness, color_selection
        )
        self.set_send_led_setting(1)

    def get_current_model_index(self):
        self._write((0xB1,), 0xCC, prefix=1)
        return self._read()[2]

    def set_screen(self, channel, mode, value, **kwargs):
        check_unsafe(*self._UNSAFE, error=True, **kwargs)

        assert channel.lower() == "lcd"
        try:
            mode = self.SCREEN_MODES[mode]
        except KeyError as e:
            raise Exception(
                f"Unknown screen mode! Should be one of: {self.SCREEN_MODES.keys()}"
            ) from e

        if value is not None:
            opts = value.split(";")

        if mode == _ScreenMode.HARDWARE:
            # hardware monitor options are a list of the values to display
            # (case-insensitive keys to MPGCooler.HWMONITORDISPLAY)
            self.set_oled_show_hardware_monitor(opts)

        if mode == _ScreenMode.IMAGE:
            # image options are: image-type, image-index[, image-file]
            if len(opts) == 3:
                self.set_oled_upload_gif(opts)
            elif len(opts) == 2:
                self.set_oled_show_profile(opts)
            else:
                raise ValueError(
                    f"Unexpected options for LCD image. Expected either:"
                    '"image-type;image-slot" or '
                    '"image-type;image-slot;image-file", '
                    "instead got: {opts}"
                )

        elif mode == _ScreenMode.BANNER:
            # banner options are: banner-type, banner-index, message[, image-file]
            if (len(opts) == 3) or (len(opts) == 4):
                if len(opts) == 4:
                    save_slot = int(opts[1])
                    assert save_slot >= 4, (
                        "Cannot overwrite preset banner images, "
                        "please use save slots starting from 4 for your uploaded files"
                    )
                    img = self._prepare_bmp(opts[3])
                    self.set_oled_upload_banner(img, banner_no=save_slot)
                self.set_oled_user_message(opts[2])
                self.set_oled_show_banner(banner_type=int(opts[0]), bmp_no=int(opts[1]))
            else:
                raise ValueError(
                    f"Unexpected options for LCD banner. Expected either:"
                    '"banner-type;save-slot;message" or '
                    '"banner-type;save-slot;message;image-file", '
                    "instead got: {opts}"
                )

        elif mode == _ScreenMode.CLOCK:
            # clock option is the display style
            self.set_oled_show_clock(int(opts[0]))

        elif mode == _ScreenMode.SETTINGS:
            # setting options are: brightness, direction
            brightness, direction = [int(x) for x in opts]
            self.set_oled_brightness_and_direction(brightness=brightness, direction=direction)

        elif mode == _ScreenMode.DISABLED:
            # switches off the display
            self.set_oled_show_disable()

    def _prepare_bmp(self, path):
        end_w, end_h = 240, 320
        img = Image.open(path)
        w, h = img.size
        wrat = end_w / w
        hrat = end_h / h
        ratio = wrat if wrat > hrat else hrat
        img = img.resize((int(ratio * w), int(ratio * h)))
        w, h = img.size
        x_start = int((w - end_w) / 2)
        y_start = int((h - end_h) / 2)
        img = img.crop((x_start, y_start, x_start + end_w, y_start + end_h))

        img = img.convert("RGB")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="BMP")
        return img_bytes

    def get_firmware_version_aprom(self):
        self._write((0xB0,), 0xCC, prefix=1)
        ret = self._read()
        return (
            ret[2] >> 4,  # high
            ret[2] & 0xF,  # low
        )

    def get_firmware_version_ldrom(self):
        self._write((0xB6,), 0xCC, prefix=1)
        ret = self._read()
        return (
            ret[2] >> 4,  # high
            ret[2] & 0xF,  # low
        )

    def get_firmware_checksum_aprom(self):
        self._write((0xB0,), 0xCC, prefix=1)
        ret = self._read()
        return (
            ret[8],  # high
            ret[9],  # low
        )

    def get_firmware_checksum_ldrom(self):
        self._write((0xB4,), 0xCC, prefix=1)
        ret = self._read()
        return (
            ret[8],  # high
            ret[9],  # low
        )

    def get_all_hardware_monitor(self):
        self.device.clear_enqueued_reports()
        return self.device.get_feature_report(0xD0, _REPORT_LENGTH)

    def set_buzzer(self, type, frequency=650):
        return self._write(
            (0xC2, 0, 0, 0, 0, 0, type, frequency & 0xFF, (frequency >> 8) & 0xFF), prefix=1
        )

    def set_led_global(self, on_off):
        return self._write((0xBB, 0, 0, 0, 0, int(on_off)), prefix=1)

    def get_led_global(self):
        self._write((0xBA,), 0xCC, prefix=1)
        ret = self._read()
        ok = len(ret) == _REPORT_LENGTH
        for j, _ in enumerate(ret):
            if (
                (j == 0 and ret[j] != 1)
                or (j == 1 and ret[j] != 90)
                or (j == 6 and ret[j] not in (0, 1))
            ):
                ok = False
            elif ret[j] != 0xCC:
                ok = False
        return ok and ret[6] == 1

    def get_led_pe0(self):
        self._write((0xA0, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 0xCC, 1, 0xF2), 0xCC, prefix=0xFA)
        ret = self._read()
        ok = True
        if (
            ret[0] != 250
            or ret[1] != 160
            or ret[2] != 205
            or ret[9] != 1
            or ret[10] != 242
            or ret[11] not in (0, 1)
        ):
            ok = 0
        for j, n in enumerate(ret, start=23):
            if j > 29:
                break
            if n != 0:
                ok = False
        for j, n in enumerate(ret, start=30):
            if n != 0xCC:
                ok = False
        return ok and ret[11] == 1

    def get_device_settings(self):
        return _DeviceSettings(
            self._feature_data[61] & 1,
            (self._feature_data[61] & 0xE) >> 1,
            (self._feature_data[62] & 0xFC) >> 2,
            self._feature_data[72] & 1,
            self._feature_data[41],
            self._feature_data[52],
            self._feature_data[63],
        )

    def get_board_sync_settings(self):
        return _BoardSyncSettings(
            (self._feature_data[82] & 1) == 1,
            (self._feature_data[78] & 0x80) >> 7 == 1,
            ((self._feature_data[82] >> 4) & 1) == 1,
            ((self._feature_data[82] >> 5) & 1) == 1,
            ((self._feature_data[82] >> 1) & 1) == 1,
            ((self._feature_data[82] >> 2) & 1) == 1,
            ((self._feature_data[82] >> 3) & 1) == 1,
        )

    def get_style_settings(self, led_area):
        return _StyleSettings(
            self._feature_data[led_area],
            (self._feature_data[led_area + 4] & 3),
            (self._feature_data[led_area + 4] >> 2) & 0x1F,
            ((self._feature_data[led_area + 8] & 0x80) >> 7),
        )

    def get_color_settings(self, led_area):
        return _ColorSettings(
            self._feature_data[led_area + 1 : led_area + 4],
            self._feature_data[led_area + 5 : led_area + 8],
        )

    def get_current_led_setting(self):
        self._feature_data = self.device.get_feature_report(self._feature_data[0], _MAX_DATA_LENGTH)
        self._feature_data[62] = clamp(self._feature_data[62] - 4, 0, 255)
        return self._feature_data

    def get_all_board(self):
        return self.device.get_feature_report(0x52, _MAX_DATA_LENGTH)

    def get_oled_firmware_version(self):
        self._write((0xF1,))
        return self._read()[2]

    def get_oled_gif_checksum(self):
        self._write((0xC2,))
        ret = self._read()
        return (
            ret[3],  # high
            ret[2],  # low
        )

    def get_oled_banner_checksum(self):
        self._write((0xD2,))
        buf = self._read()
        return (
            buf[3],  # high
            buf[2],  # low
        )

    def get_oled_m481checksum(self):
        self._write((0xF1,))
        ret = self._read()
        return (
            ret[3],  # high
            ret[2],  # low
        )

    def set_volume(self, main, left, right):
        return self._write(
            (0xC0, clamp(main, 0, 100), clamp(left, 0, 100), clamp(right, 0, 100)), 0xCC, prefix=1
        )

    def set_oled_cpu_message(self, message):
        return self._write([0x90] + list(message[:60].encode("ascii", "ignore")))

    def set_oled_show_hardware_monitor(self, opts, radiator_fan_smart_mode_on_off=True):
        """
        Command device to display hardware information on the built in display.

        Parameters
        ----------
        opts:
            Array[str] Indicates which hardware features will be presented on the screen,
                       from CPU_FREQ, CPU_TEMP, GPU_MEMORY_FREQ, GPU_USAGE, FAN_PUMP, FAN_RADIATOR, FAN_CPUMOS
        radiator_fan_smart_mode_on_off:
            Bool Indicates whether smart control is enabled, this slightly alters the visualization
        """
        show_idx = [self.HWMONITORDISPLAY[x.lower()].value for x in opts]
        show_area = [i in show_idx for i in range(_OLEDHardwareMonitorOffset.MAXIMUM.value + 1)]
        if len(show_area) < 7:
            return False
        buf = bytearray(_REPORT_LENGTH)
        buf[0] = 0xD0
        buf[1] = 0x71
        for item in iter(_OLEDHardwareMonitorOffset):
            if item.value != _OLEDHardwareMonitorOffset.MAXIMUM and show_area[item.value]:
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
            self._feature_data[_CYCLE_NUMBER_STRIPE_TYPE_MAPPING[stripe_type]] = cycle_num

    def set_cycle_number_by_led_area(self, led_area, cycle_num):
        if led_area in _CYCLE_NUMBER_LED_AREA_MAPPING:
            self._feature_data[_CYCLE_NUMBER_LED_AREA_MAPPING[led_area]] = cycle_num

    def set_device_setting(
        self, stripe_or_fan, fan_type, corsair_device_qty, ll120_outer_individual
    ):
        corsair_device_qty = clamp(corsair_device_qty, 0, 63)
        ll120_outer_individual = clamp(int(ll120_outer_individual), 0, 1)
        self._feature_data[61] = (self._feature_data[61] & 0x80) | (fan_type << 1) | stripe_or_fan
        self._feature_data[62] = corsair_device_qty << 2
        self._feature_data[72] = self._feature_data[72] | ll120_outer_individual

    def set_board_sync_setting(
        self,
        onboard_sync,
        combine_jrgb,
        combine_jpipe1,
        combine_jpipe2,
        combine_jrainbow1,
        combine_jrainbow2,
        combine_jcorsair,
    ):
        self._feature_data[82] |= clamp(int(onboard_sync), 0, 1)
        self._feature_data[78] |= 0b10000000 if combine_jrgb else 0
        self._feature_data[82] |= 0b00010000 if combine_jpipe1 else 0
        self._feature_data[82] |= 0b00100000 if combine_jpipe2 else 0
        self._feature_data[82] |= 0b00000010 if combine_jrainbow1 else 0
        self._feature_data[82] |= 0b00000100 if combine_jrainbow2 else 0
        self._feature_data[82] |= 0b00001000 if combine_jcorsair else 0

    def set_style_setting(self, led_area, lighting_mode, speed, brightness, color_selection):
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
        self._feature_data[led_area + 4] = (
            (self._feature_data[led_area + 4] & 0x80) | (brightness << 2) | speed
        )
        self._feature_data[led_area + 8] = 0b10000000 if color_selection else 0

    def set_color_setting(
        self, led_area, color1_r, color1_g, color1_b, color2_r, color2_g, color2_b
    ):
        """
        --led-area
        --color1
        --color2
        """

        self._feature_data[led_area + 1] = clamp(color1_r, 0, 255)
        self._feature_data[led_area + 2] = clamp(color1_g, 0, 255)
        self._feature_data[led_area + 3] = clamp(color1_b, 0, 255)
        self._feature_data[led_area + 4] = clamp(led_area, 0, 174)
        self._feature_data[led_area + 5] = clamp(color2_r, 0, 255)
        self._feature_data[led_area + 6] = clamp(color2_g, 0, 255)
        self._feature_data[led_area + 7] = clamp(color2_b, 0, 255)

    def set_send_led_setting(self, save):
        """applies changes, persists to device with save option"""
        self._feature_data[184] = int(bool(save))
        return self._set_all_board(self._feature_data)

    def set_direction_setting_b931_only(
        self, board_sync, jrainbow1, jrainbow2, jrainbow3, jrainbow4, jrainbow5
    ):
        """--b931-direction ?"""
        self._feature_data[83] |= int(bool(board_sync))
        self._feature_data[39] |= int(bool(jrainbow1))
        self._feature_data[61] |= int(bool(jrainbow2))
        self._feature_data[50] |= int(bool(jrainbow3))
        self._feature_data[19] |= int(bool(jrainbow4))
        self._feature_data[29] |= int(bool(jrainbow5))

    def set_oled_user_message(self, message):
        """--message"""
        return self._write([0x93] + list((message[:61] + " ").encode("ascii", "ignore")))

    def set_oled_show_gameboot(self, selection, message):
        """
        --selection
        --message
        """
        return self._write([0x73, selection] + list(message[:60].encode("ascii", "ignore")))

    def set_oled_show_profile(self, opts):
        """
        --profile-type
        --gif-number
        """
        profile_type, gif_no = map(int, opts[:2])
        data = [0x70, 0, gif_no]
        self._write(data)
        data[1] = clamp(profile_type, 0, 1)
        return self._write(data)

    def set_oled_show_banner(self, banner_type=0, bmp_no=0):
        """
        --banner-type
        --bmp-number
        """
        data = [0x79, banner_type, bmp_no]
        return self._write(data)

    def set_oled_show_disable(self):
        """--disable-oled"""
        return self._write((0x7F,))

    def _set_oled_upload(self, type, bytes, type_num=0):
        is_gif = type == _UploadType.GIF
        start_cmd = 0xC0 if is_gif else 0xD0
        content = bytes.getbuffer()
        l = len(content)
        if l > (2**20):
            raise ValueError("file size of image is too large, something went wrong!")
        _LOGGER.debug(f"size of uploaded image is {l} bytes.")
        self._write(
            (start_cmd, l & 0xFF, (l >> 8) & 0xFF, (l >> 16) & 0xFF, (l >> 24) & 0xFF, type_num)
        )
        sleep(2)
        checksum = sum(content) & 0xFFFF
        n = 0
        while n < l:
            array = [start_cmd + 1]
            o = clamp(l - n, 0, 60)
            for k in range(0, o):
                array.append(content[n + k])
            n += o
            self._write(array)
        if is_gif:
            high, low = self.get_oled_gif_checksum()
            check = (high << 8) + low
        else:
            high, low = self.get_oled_banner_checksum()
            check = (high << 8) + low

        if check != checksum:
            _LOGGER.error(
                f"invalid upload, image checksums: high {high} vs {checksum & 0xFF00}, "
                f"low {low} vs {checksum & 0xFF}."
            )

    def set_oled_upload_gif(self, opts):
        """
        --upload-gif-file
        --upload-gif-number
        """
        imgtype, gif_no = map(int, opts[:2])
        assert imgtype == 1, "Cannot override default images (image type 0)"
        file = opts[2]
        image_bytes = self._prepare_bmp(file)
        self._set_oled_upload(_UploadType.GIF, image_bytes, gif_no)

    def set_oled_upload_banner(self, bytes, banner_no=4):
        """Default is 4 to not overwrite the default banners.

        --upload-banner-file
        --upload-banner-number
        """
        self._set_oled_upload(_UploadType.BANNER, bytes, banner_no)

    def set_oled_clock(self, time):
        """
        Sends the specified time to the device.
        """
        return self._write(
            (
                0x83,
                time.year % 100,
                time.month,
                time.day,
                time.weekday(),
                time.hour,
                time.minute,
                time.second,
            )
        )

    def set_oled_show_clock(self, style):
        """--set-oled-mode clock"""
        return self._write((0x7A, clamp(style, 0, 2)))

    def set_oled_show_cpu_status(self, freq, temp):
        """--update-cpu-status"""
        freq = clamp(int(freq), 0, 65536)
        temp = clamp(int(temp), 0, 65536)
        return self._write(
            (
                0x85,
                freq & 0xFF,
                (freq >> 8) & 0xFF,
                temp & 0xFF,
                (temp >> 8) & 0xFF,
            )
        )

    @staticmethod
    def _make_buffer(array, fill=0, total_size=_REPORT_LENGTH, prefix=0xD0):
        return bytearray([prefix] + list(array) + ((total_size - (len(array) + 1)) * [fill]))

    def _write(self, array, fill=0, total_size=_REPORT_LENGTH, prefix=0xD0):
        self.device.clear_enqueued_reports()
        return self.device.write(self._make_buffer(array, fill, total_size, prefix))

    def _read(self, size=_REPORT_LENGTH):
        return bytearray(self.device.read(size))

    def set_oled_gpu_status(self, mem_freq, usage):
        """
        --set-gpu-memory-frequency
        --set-gpu-usage
        """
        mem_freq = clamp(int(mem_freq), 0, 65536)
        usage = clamp(int(usage), 0, 65536)
        return self._write(
            (
                0x86,
                mem_freq & 0xFF,
                (mem_freq >> 8) & 0xFF,
                usage & 0xFF,
                (usage >> 8) & 0xFF,
            )
        )

    def set_oled_brightness_and_direction(self, brightness=100, direction=0):
        """
        --set-oled-brightness
        --direction
        """
        return self._write((0x7E, clamp(brightness, 0, 100), clamp(direction, 0, 3)))

    def set_per_led_720byte(self, jtype, area, rgb_data):
        b = jtype
        if self.product_id != 0x7B10 and self.product_id != 0x7C34:
            b += 1
        if len(rgb_data) < 3:
            rgb_data = bytearray(3)
        rgb_data = rgb_data[:_PER_LED_LENGTH]
        self._feature_data_per_led = self._make_buffer(
            [0x37, b, area] + list(rgb_data), total_size=_PER_LED_LENGTH + 5, prefix=0x53
        )
        return self.device.send_feature_report(self._feature_data_per_led)

    def set_per_led_index(self, jtype, area, index_and_rgb, show=True, led_count=0):
        """
        --set-per-led-index
        --jtype INT
        --area INT
        --index-and-rgb hex string?
        --show (or not passed)
        --maximum-leds INT
        """
        array = bytearray(1)

        def rank_check(array):
            return (
                isinstance(array, Sequence)
                and all(isinstance(x, Sequence) for x in array)
                and all(not isinstance(xa, Sequence) for x in array for xa in x)
            )

        if len(index_and_rgb[1]) < 4 or len(index_and_rgb[0]) < 1 or not rank_check(index_and_rgb):
            raise ValueError("index_and_rgb should be a 2-dimensional list")
        if jtype == _JType.JONBOARD.value:
            array = self._per_led_rgb_jonboard
        elif jtype == _JType.JRAINBOW.value:
            area = clamp(area, 0, 1)
            array = self._per_led_rgb_jrainbow2 if area == 1 else self._per_led_rgb_jrainbow1
        elif jtype == _JType.JCORSAIR.value:
            array = self._per_led_rgb_jcorsair
        end_index = led_count if led_count > 0 else len(index_and_rgb)
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
            self.set_style_setting(
                _LEDArea.ONBOARD_LED_0.value,
                _LightingMode.CORSAIR_IQUE.value,
                _Speed.MEDIUM.value,
                10,
                _ColorSelection.USER_DEFINED.value,
            )
            self._per_led_rgb_jonboard = bytearray(_PER_LED_LENGTH)
        elif jtype == _JType.JRAINBOW.value:
            if area == 0:
                self._per_led_rgb_jrainbow1 = bytearray(_PER_LED_LENGTH)
                self.set_cycle_number(0, 200)
                self.set_style_setting(
                    _LEDArea.JRAINBOW1.value,
                    _LightingMode.CORSAIR_IQUE.value,
                    _Speed.MEDIUM.value,
                    10,
                    _ColorSelection.USER_DEFINED.value,
                )
            elif area == 1:
                self._per_led_rgb_jrainbow2 = bytearray(_PER_LED_LENGTH)
                self.set_cycle_number(1, 240)
                self.set_style_setting(
                    _LEDArea.JRAINBOW2.value,
                    _LightingMode.CORSAIR_IQUE.value,
                    _Speed.MEDIUM.value,
                    10,
                    _ColorSelection.USER_DEFINED.value,
                )
        elif jtype == _JType.JCORSAIR.value:
            self._per_led_rgb_jcorsair = bytearray(_PER_LED_LENGTH)
            self.set_style_setting(
                _LEDArea.JCORSAIR.value,
                _LightingMode.CORSAIR_IQUE.value,
                _Speed.MEDIUM.value,
                10,
                _ColorSelection.USER_DEFINED.value,
            )
            if ((self._feature_data[61] & 0xE) >> 1) == 0 and (self._feature_data[61] & 1) == 1:
                self.set_device_setting(_StripeOrFan.FAN.value, _FanType.SP.value, 5, 0)
            else:
                self.set_cycle_number(2, 240)
                self.set_device_setting(_StripeOrFan.STRIPE.value, _FanType.HD.value, 0, 0)
        self.set_board_sync_setting(True, True, True, True, False, False, False)
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
        self.set_style_setting(_LEDArea.ONBOARD_LED_0.value, which, 1, 10, 1)
        self.set_color_setting(_LEDArea.ONBOARD_LED_0.value, r, g, b, r, g, b)
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
            [_FanConfig(_FanMode.BALANCE.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.BALANCE.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self._send_safe_temp()

    def switch_to_game_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.GAME.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.GAME.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self._send_safe_temp()

    def switch_to_silent_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.SILENT.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.SILENT.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self._send_safe_temp()

    def switch_to_smart_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.SMART.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.SMART.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self._send_safe_temp()

    def switch_to_default_mode(self):
        self.set_fan_config(
            [_FanConfig(_FanMode.DEFAULT.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self.set_fan_temp_config(
            [_FanTempConfig(_FanMode.DEFAULT.value, 0, 0, 0, 0, 0, 0, 0)] * self._fan_count
        )
        self._send_safe_temp()

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
