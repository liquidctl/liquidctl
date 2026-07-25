# uses the psf/black style

from struct import pack
from datetime import datetime

import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.msi import (
    MpgCooler,
    MpgCoolerLcd,
    _REPORT_LENGTH,
    _DEFAULT_FEATURE_DATA,
    _LightingMode,
)
from liquidctl.error import NotSupportedByDevice, UnsafeFeaturesNotEnabled


@pytest.fixture
def mpgCoreLiquidK360Device():
    description = "Mock MPG CoreLiquid K360"
    device = _MockCoreLiquid(vendor_id=0xFFFF, product_id=0xB130)
    dev = MpgCooler(device, description)

    dev.connect()
    return dev


@pytest.fixture
def mpgCoreLiquidDeviceExperimental():
    _, pid, desc, kwargs = MpgCooler._MATCHES[-1]
    description = "Mock " + desc
    unsafe = kwargs["_unsafe"]
    device = _MockCoreLiquid(vendor_id=0xFFFF, product_id=pid)
    dev = MpgCooler(device, description, **kwargs, unsafe=unsafe)

    dev.connect(unsafe=unsafe)
    return dev


@pytest.fixture
def mpgCoreLiquidD360Device():
    # The D360 reuses the K360 cooling/monitoring protocol but has a different
    # display, so it is matched with oled_compatible=False.  It is not gated
    # behind an unsafe feature.
    _, pid, desc, kwargs = [m for m in MpgCooler._MATCHES if m[1] == 0xEDFC][0]
    device = _MockCoreLiquid(vendor_id=0xFFFF, product_id=pid)
    dev = MpgCooler(device, "Mock " + desc, **kwargs)

    dev.connect()
    return dev


@pytest.fixture
def mpgCoreLiquidK360DeviceInvalid():
    description = "Mock MPG CoreLiquid K360"
    device = _MockCoreLiquidInvalid(vendor_id=0xFFFF, product_id=0xB130)
    dev = MpgCooler(device, description)

    dev.connect()
    return dev


class _MockCoreLiquid(MockHidapiDevice):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._fan_configs = (4, 20, 40, 50, 60, 70, 80, 90)
        self._fan_temp_configs = (4, 30, 40, 50, 60, 70, 80, 90)
        self._model_idx = 255  # TODO: check the correct model index from device
        self._feature_data = Report(_DEFAULT_FEATURE_DATA[0], _DEFAULT_FEATURE_DATA[1:])

        self.preload_read(self._feature_data)

    def write(self, data):
        reply = bytearray(_REPORT_LENGTH)
        reply[0:2] = data[0:2]
        if list(data[:2]) == [0x01, 0xB1]:  # get current model idx request
            reply[2] = self._model_idx
        elif list(data[:2]) == [0xD0, 0x31]:  # get status request
            reply[2:23] = (
                pack("<h", 496)
                + pack("<h", 517)
                + pack("<h", 509)
                + pack("<h", 1045)
                + pack("<h", 1754)
                + bytearray([0, 0, 0, 0, 0x7D, 0, 0x7D, 0, 0, 0])
                + pack("<h", 20)
                + pack("<h", 20)
                + pack("<h", 20)
                + pack("<h", 20)
                + pack("<h", 50)
            )
            self.preload_read(Report(0, reply))
        elif list(data[:2]) == [0xD0, 0x32]:  # get fan config request
            for i in (2, 10, 18, 26, 34):
                reply[i : i + 10] = self._fan_configs
            self.preload_read(Report(0, reply))
        elif list(data[:2]) == [0xD0, 0x33]:  # get fan T config request
            reply[1] = 0x32
            for i in (2, 10, 18, 26, 34):
                reply[i : i + 10] = self._fan_temp_configs
            self.preload_read(Report(0, reply))
        elif list(data[1:3]) == [0xB0, 0xCC]:  # get ldrom fw
            self.preload_read(Report(0, reply))
        elif list(data[1:3]) == [0xB6, 0xCC]:  # get aprom fw
            self.preload_read(Report(0, reply))
        elif data[1] == 0xF1:  # get screen fw
            self.preload_read(Report(0, reply))
        return super().write(data)


class _MockCoreLiquidInvalid(MockHidapiDevice):
    def read(self, length):
        buf = bytearray([0xD0, 0x32] + (62 * [0]))
        return buf[:length]


def test_mpg_core_liquid_k360_initializes(mpgCoreLiquidK360Device):
    mpgCoreLiquidK360Device.initialize()

    writes = len(mpgCoreLiquidK360Device.device.sent)
    assert (
        writes
        == 9
        # 1 get fan config,
        # 2 get fan T config,
        # 3 get aprom fw,
        # 4 get ldrom fw,
        # 5 get display fw,
        # 6 set screen settings,
        # 7 set fan config,
        # 8 set fan T config,
        # 9 set safe control temperature
    )


def test_mpg_core_liquid_k360_get_status(mpgCoreLiquidK360Device):
    dev = mpgCoreLiquidK360Device
    (
        fan1,
        fan1d,
        fan2,
        fan2d,
        fan3,
        fan3d,
        wbfan,
        wbfand,
        pump,
        pumpd,
    ) = dev.get_status()
    assert fan1[1] == 496
    assert fan1d[1] == 20
    assert fan2[1] == 517
    assert fan2d[1] == 20
    assert fan3[1] == 509
    assert fan3d[1] == 20
    assert wbfan[1] == 1045
    assert wbfand[1] == 20
    assert pump[1] == 1754
    assert pumpd[1] == 50
    assert dev.device.sent[-1].number == 0xD0
    assert dev.device.sent[-1].data[0] == 0x31


def test_mpg_core_liquid_k360_get_status_invalid_read(mpgCoreLiquidK360DeviceInvalid):
    dev = mpgCoreLiquidK360DeviceInvalid
    with pytest.raises(AssertionError):
        dev.get_status()


def test_mpg_core_liquid_k360_set_fixed_speeds(mpgCoreLiquidK360Device):
    mpgCoreLiquidK360Device.set_fixed_speed("pump", 65)

    fan_report, T_report = mpgCoreLiquidK360Device.device.sent[-2:]
    assert fan_report.data[33:41] == [3] + [65] * 7


def test_mpg_core_liquid_k360_set_speed_profile(mpgCoreLiquidK360Device):
    duties = [20, 30, 34, 40, 50]
    temps = [30, 50, 80, 90, 100]
    curve_profile = zip(duties, temps)

    mpgCoreLiquidK360Device.set_speed_profile("fans", curve_profile)

    fan_report, T_report = mpgCoreLiquidK360Device.device.sent[-3:-1]

    # fan 1
    assert fan_report.data[1:9] == [3] + duties + [0] * 2
    assert T_report.data[1:9] == [3] + temps + [0] * 2
    # fan 2
    assert fan_report.data[9:17] == [3] + duties + [0] * 2
    assert T_report.data[9:17] == [3] + temps + [0] * 2
    # fan 3
    assert fan_report.data[17:25] == [3] + duties + [0] * 2
    assert T_report.data[17:25] == [3] + temps + [0] * 2


def test_mpg_core_liquid_k360_set_color(mpgCoreLiquidK360Device):
    colors = [[255, 255, 0], [0, 255, 255]]
    mode = "clock"
    speed = 2
    brightness = 5
    use_color = 1

    mpgCoreLiquidK360Device.set_color(
        "sync", mode, colors, speed=speed, brightness=brightness, color_selection=use_color
    )
    report = mpgCoreLiquidK360Device.device.sent[-1]

    assert report.data[30] == 20  # mode
    assert report.data[34] == (brightness << 2) | speed  # brightness, speed
    assert report.data[31:34] == colors[0]
    assert report.data[35:38] == colors[1]


def test_mpg_core_liquid_k360_not_totally_broken(mpgCoreLiquidK360Device):
    """Reasonable calls to untested APIs do not raise exceptions"""
    dev = mpgCoreLiquidK360Device
    dev.initialize()
    _ = dev.get_status()

    profile = ((0, 30), (25, 40), (60, 60), (100, 75))
    dev.set_speed_profile("pump", profile)
    dev.set_fixed_speed("waterblock-fan", 42)
    dev.set_screen("lcd", "image", "0;4")
    dev.set_screen("lcd", "banner", "1;0;Hello, world")
    dev.set_screen("lcd", "disable", "")
    dev.set_screen("lcd", "clock", "0")
    dev.set_screen("lcd", "hardware", "cpu_temp;cpu_freq")


def test_mpg_core_liquid_k360_set_clock(mpgCoreLiquidK360Device):
    time = datetime(2012, 12, 21, 9, 54, 20)

    mpgCoreLiquidK360Device.set_time(time)

    report = mpgCoreLiquidK360Device.device.sent[-1]
    assert report.data[:8] == [131, 12, 12, 21, 4, 9, 54, 20]


def test_mpg_core_liquid_k360_set_hw_status(mpgCoreLiquidK360Device):
    cpu_freq = 3500.0
    cpu_T = 54.0
    gpu_f = 7000

    mpgCoreLiquidK360Device.set_hardware_status(cpu_T, cpu_f=cpu_freq, gpu_f=gpu_f)

    cpu_report = mpgCoreLiquidK360Device.device.sent[-2]
    assert cpu_report.data[:5] == [133, 172, 13, 54, 0]

    gpu_report = mpgCoreLiquidK360Device.device.sent[-1]
    assert gpu_report.data[:5] == [134, 88, 27, 0, 0]


def test_unsafe_core_liquid_get_status(mpgCoreLiquidDeviceExperimental):
    status = mpgCoreLiquidDeviceExperimental.get_status()
    assert status == []

    status = mpgCoreLiquidDeviceExperimental.get_status(unsafe=["other"])
    assert status == []

    status = mpgCoreLiquidDeviceExperimental.get_status(unsafe=["experimental_coreliquid_cooler"])
    assert mpgCoreLiquidDeviceExperimental.device.sent[-1].number == 0xD0


def test_unsafe_core_liquid_set_fixed_speed(mpgCoreLiquidDeviceExperimental):
    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_fixed_speed("pump", 65)

    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_fixed_speed("pump", 65, unsafe=["other"])

    mpgCoreLiquidDeviceExperimental.set_fixed_speed(
        "pump", 65, unsafe=["experimental_coreliquid_cooler"]
    )


def test_unsafe_core_liquid_set_speed_profile(mpgCoreLiquidDeviceExperimental):
    duties = [20, 30, 34, 40, 50]
    temps = [30, 50, 80, 90, 100]
    curve_profile = zip(duties, temps)
    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_speed_profile("fans", curve_profile)

    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_speed_profile("fans", curve_profile, unsafe=["other"])

    mpgCoreLiquidDeviceExperimental.set_speed_profile(
        "fans", curve_profile, unsafe=["experimental_coreliquid_cooler"]
    )


def test_unsafe_core_liquid_set_color(mpgCoreLiquidDeviceExperimental):
    colors = [[255, 255, 0], [0, 255, 255]]
    mode = "clock"
    speed = 2
    brightness = 5
    use_color = 1

    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_color(
            "sync", mode, colors, speed=speed, brightness=brightness, color_selection=use_color
        )

    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_color(
            "sync",
            mode,
            colors,
            speed=speed,
            brightness=brightness,
            color_selection=use_color,
            unsafe=["other"],
        )

    mpgCoreLiquidDeviceExperimental.set_color(
        "sync",
        mode,
        colors,
        speed=speed,
        brightness=brightness,
        color_selection=use_color,
        unsafe=["experimental_coreliquid_cooler"],
    )


def test_unsafe_core_liquid_set_clock(mpgCoreLiquidDeviceExperimental):
    time = datetime(2012, 12, 21, 9, 54, 20)

    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_time(time)

    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_time(time, unsafe=["other"])

    mpgCoreLiquidDeviceExperimental.set_time(time, unsafe=["experimental_coreliquid_cooler"])


def test_unsafe_core_liquid_set_hw_status(mpgCoreLiquidDeviceExperimental):
    cpu_freq = 3500.0
    cpu_T = 54.0

    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_hardware_status(cpu_T, cpu_f=cpu_freq)

    with pytest.raises(UnsafeFeaturesNotEnabled):
        mpgCoreLiquidDeviceExperimental.set_hardware_status(cpu_T, cpu_f=cpu_freq, unsafe=["other"])

    mpgCoreLiquidDeviceExperimental.set_hardware_status(
        cpu_T, cpu_f=cpu_freq, unsafe=["experimental_coreliquid_cooler"]
    )


def test_mpg_core_liquid_parse_channel(mpgCoreLiquidK360Device):
    dev = mpgCoreLiquidK360Device
    assert dev.parse_channel("pump") == [4]
    assert dev.parse_channel("waterblock-fan") == [3]
    assert list(dev.parse_channel("fans")) == [0, 1, 2]
    # radiator fans are 1-indexed for the user (fan1..fan3)
    assert dev.parse_channel("fan1") == [0]
    assert dev.parse_channel("fan2") == [1]
    assert dev.parse_channel("fan3") == [2]
    for bad in ("fanX", "fan", "fan0", "fan9", ""):
        with pytest.raises(ValueError):
            dev.parse_channel(bad)


# --- MSI MPG Coreliquid D360 -------------------------------------------------
# The D360 shares the K360 cooling/monitoring protocol but uses a different
# display; it is matched with oled_compatible=False.  Unlike the two suspected
# variants, it is verified and not gated behind an unsafe feature.


def test_mpg_core_liquid_d360_is_matched():
    match = [m for m in MpgCooler._MATCHES if m[1] == 0xEDFC]
    assert len(match) == 1, "D360 (0xEDFC) should be matched exactly once"
    vid, pid, desc, kwargs = match[0]
    assert vid == 0x0DB0
    assert "D360" in desc
    assert kwargs["oled_compatible"] is False
    assert kwargs["fixed_speed_needs_temp"] is True
    assert "_unsafe" not in kwargs  # verified device, no unsafe gating


def test_mpg_core_liquid_d360_not_oled_compatible(mpgCoreLiquidD360Device):
    assert mpgCoreLiquidD360Device._oled_compatible is False


def test_mpg_core_liquid_d360_get_status_needs_no_unsafe(mpgCoreLiquidD360Device):
    dev = mpgCoreLiquidD360Device
    fan1, fan1d, fan2, fan2d, fan3, fan3d, wbfan, wbfand, pump, pumpd = dev.get_status()
    assert fan1[1] == 496
    assert pump[1] == 1754
    assert pumpd[1] == 50


def test_mpg_core_liquid_d360_initialize_omits_display_fw(mpgCoreLiquidD360Device):
    status = mpgCoreLiquidD360Device.initialize()
    labels = [row[0] for row in status]
    assert "Display firmware version" not in labels
    assert "Pump mode" in labels


def test_mpg_core_liquid_d360_set_fixed_speed_feeds_temp(mpgCoreLiquidD360Device):
    mpgCoreLiquidD360Device.set_fixed_speed("pump", 65)

    # writes: fan config (0x40), fan temp config (0x41), control temp (0x85)
    fan_report, T_report, temp_report = mpgCoreLiquidD360Device.device.sent[-3:]
    assert fan_report.data[0] == 0x40
    assert fan_report.data[33:41] == [3] + [65] * 7
    # the D360 needs a control temperature for the duty to take effect
    assert temp_report.data[0] == 0x85


def test_mpg_core_liquid_k360_set_fixed_speed_does_not_feed_temp(mpgCoreLiquidK360Device):
    # the temp self-feed is scoped to the D-series and must not change the K360
    mpgCoreLiquidK360Device.set_fixed_speed("pump", 65)
    assert mpgCoreLiquidK360Device.device.sent[-1].data[0] == 0x41  # fan temp config, no 0x85


def test_mpg_core_liquid_d360_lcd_not_supported(mpgCoreLiquidD360Device):
    with pytest.raises(NotSupportedByDevice):
        mpgCoreLiquidD360Device.set_screen("lcd", "disable", "")


def test_mpg_core_liquid_d360_set_time_not_supported(mpgCoreLiquidD360Device):
    time = datetime(2012, 12, 21, 9, 54, 20)
    with pytest.raises(NotSupportedByDevice):
        mpgCoreLiquidD360Device.set_time(time)


# --- MSI MPG Coreliquid D-series LCD -----------------------------------------
# The panel is a separate USB device (0db0:8dbf) from the cooler, with its own
# framing: 6b 5a <cmd> 00 <length u32le> <payload>, over report id 1.


def _u32le(value):
    return [value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF]


class _MockCoreLiquidLcd(MockHidapiDevice):
    """Mock panel that answers GET_DEV_INFO (0x14) with 0x15."""

    def __init__(self, firmware=6, brightness=100, orientation=0, **kwargs):
        super().__init__(**kwargs)
        self.firmware = firmware
        self.brightness = brightness
        self.orientation = orientation
        self.bulk_reports = 0

    def write(self, data):
        data = bytes(data)
        if data[0] == 2:  # bulk file data
            self.bulk_reports += 1
        elif len(data) > 3 and data[1] == 0x6B and data[2] == 0x5A:
            cmd, payload = data[3], data[9:]
            if cmd == 0x18:  # SET_LCM_BACKLIGHT
                self.brightness = int.from_bytes(payload[:4], "little")
            elif cmd == 0x1A:  # SET_LCM_DIR
                self.orientation = int.from_bytes(payload[:4], "little")
        return super().write(data)

    def get_input_report(self, report_id, length):
        frame = [0x6B, 0x5A, 0x15, 0x00] + _u32le(20)
        frame += _u32le(self.firmware) + _u32le(self.brightness) + _u32le(self.orientation)
        frame += _u32le(0) + _u32le(0)
        report = [report_id] + frame
        return report + [0] * (length - len(report))


@pytest.fixture
def mpgCoolerLcdDevice():
    # connect() is skipped on purpose: on Windows it opens a real Win32 HID
    # handle, and with _output left unset the driver writes through the mock
    device = _MockCoreLiquidLcd(vendor_id=0x0DB0, product_id=0x8DBF)
    return MpgCoolerLcd(device, "Mock MSI MPG Coreliquid D-series LCD")


def test_mpg_cooler_lcd_is_matched():
    match = [m for m in MpgCoolerLcd._MATCHES if m[1] == 0x8DBF]
    assert len(match) == 1
    vid, pid, desc, kwargs = match[0]
    assert vid == 0x0DB0
    assert "LCD" in desc


def test_mpg_cooler_lcd_initialize(mpgCoolerLcdDevice):
    status = dict((row[0], row[1]) for row in mpgCoolerLcdDevice.initialize())
    assert status["Firmware version"] == 6
    assert status["Brightness"] == 100
    assert status["Orientation"] == 0


def test_mpg_cooler_lcd_get_status(mpgCoolerLcdDevice):
    status = dict((row[0], row[1]) for row in mpgCoolerLcdDevice.get_status())
    assert status["Brightness"] == 100
    assert status["Orientation"] == 0


def test_mpg_cooler_lcd_set_brightness(mpgCoolerLcdDevice):
    mpgCoolerLcdDevice.set_screen("lcd", "brightness", 40)

    report = mpgCoolerLcdDevice.device.sent[-1]
    assert report.number == 1  # report id
    assert report.data[0:3] == [0x6B, 0x5A, 0x18]  # magic + SET_LCM_BACKLIGHT
    assert report.data[8] == 40  # payload starts at frame offset 8
    assert mpgCoolerLcdDevice.device.brightness == 40


def test_mpg_cooler_lcd_brightness_is_clamped(mpgCoolerLcdDevice):
    mpgCoolerLcdDevice.set_screen("lcd", "brightness", 150)
    assert mpgCoolerLcdDevice.device.brightness == 100


def test_mpg_cooler_lcd_set_orientation(mpgCoolerLcdDevice):
    mpgCoolerLcdDevice.set_screen("lcd", "orientation", 270)

    report = mpgCoolerLcdDevice.device.sent[-1]
    assert report.data[0:3] == [0x6B, 0x5A, 0x1A]  # SET_LCM_DIR
    assert report.data[8] == 14 and report.data[9] == 1  # 270 == 0x010e, little endian
    assert mpgCoolerLcdDevice.device.orientation == 270


def test_mpg_cooler_lcd_rejects_bad_orientation(mpgCoolerLcdDevice):
    with pytest.raises(ValueError):
        mpgCoolerLcdDevice.set_screen("lcd", "orientation", 45)


def test_mpg_cooler_lcd_rejects_unknown_channel_and_mode(mpgCoolerLcdDevice):
    with pytest.raises(ValueError):
        mpgCoolerLcdDevice.set_screen("oled", "brightness", 50)
    with pytest.raises(ValueError):
        mpgCoolerLcdDevice.set_screen("lcd", "nonsense", 1)


def test_mpg_cooler_lcd_rejects_non_mp4(mpgCoolerLcdDevice, tmp_path):
    image = tmp_path / "picture.png"
    image.write_bytes(b"not really a png")
    with pytest.raises(ValueError):
        mpgCoolerLcdDevice.set_screen("lcd", "video", str(image))


def test_mpg_cooler_lcd_uploads_and_plays_video(mpgCoolerLcdDevice, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(bytes(2500))  # spans three 1023-byte bulk reports

    mpgCoolerLcdDevice.set_screen("lcd", "video", str(video))

    dev = mpgCoolerLcdDevice.device
    assert dev.bulk_reports == 3
    commands = [r.data[2] for r in dev.sent if r.number == 1 and r.data[0] == 0x6B]
    # file node, data start, data end, display mode, play media node
    for expected in (0x20, 0x22, 0x26, 0x50, 0x40):
        assert expected in commands, f"missing command {expected:#04x}"
    # the slot holding the media must be enabled, else nothing is displayed
    mode = next(r for r in dev.sent if r.number == 1 and r.data[2] == 0x50)
    assert mode.data[8] == 1  # image mode
    assert mode.data[10] == 8  # eight slots
    assert mode.data[11 + 7] == 1  # screen[7] enabled


def test_mpg_cooler_lcd_does_not_support_cooling(mpgCoolerLcdDevice):
    with pytest.raises(NotSupportedByDevice):
        mpgCoolerLcdDevice.set_fixed_speed("fan", 50)
    with pytest.raises(NotSupportedByDevice):
        mpgCoolerLcdDevice.set_speed_profile("fan", [(20, 30)])
    with pytest.raises(NotSupportedByDevice):
        mpgCoolerLcdDevice.set_color("sync", "steady", [[255, 0, 0]])


def test_mpg_cooler_lcd_saves_when_requested(mpgCoolerLcdDevice, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(bytes(1000))

    mpgCoolerLcdDevice.set_screen("lcd", "video", f"{video};save")

    dev = mpgCoolerLcdDevice.device
    commands = [r.data[2] for r in dev.sent if r.number == 1 and r.data[0] == 0x6B]
    assert 0x28 in commands, "media was not committed with SAVE_FILE_NODE"
    # the mode and settings nodes are written so the panel restores them
    # in SEND_FILE_NODE the payload starts at offset 8 and holds the 4-byte
    # length followed by the node name
    nodes = [
        bytes(r.data[12:44]).split(b"\x00")[0].decode()
        for r in dev.sent
        if r.number == 1 and r.data[0] == 0x6B and r.data[2] == 0x20
    ]
    assert "HMI_FW_Mode.ini" in nodes
    assert "HMI_FW_Setting.ini" in nodes


def test_mpg_cooler_lcd_does_not_save_by_default(mpgCoolerLcdDevice, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(bytes(1000))

    mpgCoolerLcdDevice.set_screen("lcd", "video", str(video))

    dev = mpgCoolerLcdDevice.device
    commands = [r.data[2] for r in dev.sent if r.number == 1 and r.data[0] == 0x6B]
    assert 0x28 not in commands


def test_mpg_cooler_lcd_rejects_unknown_video_option(mpgCoolerLcdDevice, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(bytes(10))
    with pytest.raises(ValueError):
        mpgCoolerLcdDevice.set_screen("lcd", "video", f"{video};bogus")
