# uses the psf/black style

from struct import pack
from datetime import datetime


import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.msi import MpgCooler, _REPORT_LENGTH, _DEFAULT_FEATURE_DATA, _LightingMode


@pytest.fixture
def mpgCoreLiquidK360Device():
    description = "Mock MPG CoreLiquid K360"
    device = _MockCoreLiquid(vendor_id=0xFFFF, product_id=0xB130)
    dev = MpgCooler(device, description)

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
        == 5  # get fan config, get fan T config, set screen settings, set default fan config, set default fan T config
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

    fan_report, T_report = mpgCoreLiquidK360Device.device.sent[-2:]

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
        None, mode, colors, speed=speed, brightness=brightness, color_selection=use_color
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
    dev.set_fixed_speed("waterblock fan", 42)
    dev.set_screen("lcd", "image", "0;4")
    dev.set_screen("lcd", "banner", "1;0;Hello, world")
    dev.set_screen("lcd", "disable", "")
    dev.set_screen("lcd", "clock", "0")
    dev.set_screen("lcd", "hardware", "cpu_temp;cpu_freq")


def test_mpg_core_liquid_k360_set_clock(mpgCoreLiquidK360Device):
    time = datetime(2012, 12, 21, 9, 54, 20)

    mpgCoreLiquidK360Device.set_oled_clock(time)

    report = mpgCoreLiquidK360Device.device.sent[-1]
    assert report.data[:8] == [131, 12, 12, 21, 4, 9, 54, 20]


def test_mpg_core_liquid_k360_set_hw_status(mpgCoreLiquidK360Device):
    cpu_freq = 3500.0
    cpu_T = 54.0

    mpgCoreLiquidK360Device.set_oled_show_cpu_status(cpu_freq, cpu_T)

    report = mpgCoreLiquidK360Device.device.sent[-1]
    assert report.data[:5] == [133, 172, 13, 54, 0]
