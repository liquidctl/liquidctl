import pytest

from _testutils import MockHidapiDevice, MockPyusbDevice

import json
from types import SimpleNamespace

from PIL import Image, ImageDraw

import liquidctl.driver.asus_ryujin_lcd as asus_ryujin_lcd
from liquidctl.driver.asus_ryujin import AsusRyujin
from liquidctl.driver.asus_ryujin_lcd import (
    _format_lcd_value,
    _iter_lcd_animation,
    _load_lcd_stats_config,
    _load_lcd_static_background,
    _parse_lcd_color,
    _prepare_lcd_frame,
    _read_lcd_custom_stats,
    _render_lcd_stats,
)

PROTOCOL_HEADER = 0xEC
CMD_GET_FIRMWARE = 0x82
CMD_GET_STATUS = 0x99
CMD_GET_PUMP_DUTY = 0x9A
CMD_GET_FAN_SPEEDS = 0xA0
CMD_GET_FAN_DUTY = 0xA1
CMD_SET_PUMP_DUTY = 0x1A
CMD_SET_FAN_DUTY = 0x21
CMD_GET_LCD_MODE = 0xD0
CMD_SET_LCD_MODE = 0x51
CMD_ANNOUNCE_LCD_FRAME = 0x7F
DEVICE_CONFIGS = {
    0x1988: {
        "name": "Mock ASUS Ryujin II",
        "fan_count": 4,
        "pump_speed_offset": 5,
        "pump_fan_speed_offset": 7,
        "temp_offset": 3,
        "duty_channel": 0,
        "responses": {
            CMD_GET_FIRMWARE: "ec02004155524a312d533735302d30313034",
            CMD_GET_STATUS: "ec19001b056405100e",
            CMD_GET_PUMP_DUTY: "ec1a0000223c",
            CMD_GET_FAN_SPEEDS: "ec200000000c03ee02",
            CMD_GET_FAN_DUTY: "ec2100005b",
            CMD_SET_PUMP_DUTY: "ec1a",
            CMD_SET_FAN_DUTY: "ec21",
        },
        "expected_firmware": "AURJ1-S750-0104",
        "expected_status": [
            ("Liquid temperature", 27.5, "°C"),
            ("Pump speed", 1380, "rpm"),
            ("Pump fan speed", 3600, "rpm"),
            ("Pump duty", 34, "%"),
            ("Pump fan duty", 60, "%"),
            ("External fan duty", 36, "%"),
            ("External fan 1 speed", 780, "rpm"),
            ("External fan 2 speed", 750, "rpm"),
            ("External fan 3 speed", 0, "rpm"),
            ("External fan 4 speed", 0, "rpm"),
        ],
    },
    0x1BCB: {
        "name": "Mock Ryujin III EXTREME",
        "fan_count": 0,
        "pump_speed_offset": 7,
        "pump_fan_speed_offset": 10,
        "temp_offset": 5,
        "duty_channel": 1,
        "responses": {
            CMD_GET_FIRMWARE: "ec02004155524a332d533546392d30313034",
            CMD_GET_STATUS: "ec190000001d09ec041e6603",
            CMD_GET_PUMP_DUTY: "ec1a00011e1e",
            CMD_GET_LCD_MODE: "ec50000131140000",
            CMD_SET_PUMP_DUTY: "ec1a",
        },
        "expected_firmware": "AURJ3-S5F9-0104",
        "expected_status": [
            ("Liquid temperature", 29.9, "°C"),
            ("Pump speed", 1260, "rpm"),
            ("Pump fan speed", 870, "rpm"),
            ("Pump duty", 30, "%"),
            ("Pump fan duty", 30, "%"),
        ],
    },
    0x1ADE: {
        "name": "Mock Ryujin III EVA EDITION",
        "fan_count": 0,
        "pump_speed_offset": 7,
        "pump_fan_speed_offset": 10,
        "temp_offset": 5,
        "duty_channel": 1,
        "responses": {
            CMD_GET_FIRMWARE: "ec02004155524a322d533735302d30313039",
            CMD_GET_STATUS: "ec1900000021002e0e644803",
            CMD_GET_PUMP_DUTY: "ec1a0001281e",
            CMD_SET_PUMP_DUTY: "ec1a",
        },
        "expected_firmware": "AURJ2-S750-0109",
        "expected_status": [
            ("Liquid temperature", 33.0, "°C"),
            ("Pump speed", 3630, "rpm"),
            ("Pump fan speed", 840, "rpm"),
            ("Pump duty", 40, "%"),
            ("Pump fan duty", 30, "%"),
        ],
    },
    0x1AA2: {
        "name": "Mock Ryujin III 360",
        "fan_count": 0,
        "pump_speed_offset": 7,
        "pump_fan_speed_offset": 10,
        "temp_offset": 5,
        "duty_channel": 1,
        "responses": {
            CMD_GET_FIRMWARE: "ec02004155524a332d533546392d30313034",
            CMD_GET_STATUS: "ec190000001d09ec041e6603",
            CMD_GET_PUMP_DUTY: "ec1a00011e1e",
            CMD_SET_PUMP_DUTY: "ec1a",
        },
        "expected_firmware": "AURJ3-S5F9-0104",
        "expected_status": [
            ("Liquid temperature", 29.9, "°C"),
            ("Pump speed", 1260, "rpm"),
            ("Pump fan speed", 870, "rpm"),
            ("Pump duty", 30, "%"),
            ("Pump fan duty", 30, "%"),
        ],
    },
    0x1ADA: {
        "name": "Mock Ryujin III WHITE EDITION",
        "fan_count": 0,
        "pump_speed_offset": 7,
        "pump_fan_speed_offset": 10,
        "temp_offset": 5,
        "duty_channel": 1,
        "responses": {
            CMD_GET_FIRMWARE: "ec02004155524a332d533546392d30313034",
            CMD_GET_STATUS: "ec190000001d09ec041e6603",
            CMD_GET_PUMP_DUTY: "ec1a00011e1e",
            CMD_SET_PUMP_DUTY: "ec1a",
        },
        "expected_firmware": "AURJ2-S750-0108",
        "expected_status": [
            ("Liquid temperature", 29.9, "°C"),
            ("Pump speed", 1260, "rpm"),
            ("Pump fan speed", 870, "rpm"),
            ("Pump duty", 30, "%"),
            ("Pump fan duty", 30, "%"),
        ],
    },
}


class _MockRyujinDevice(MockHidapiDevice):
    def __init__(self, vendor_id: int, product_id: int):
        super().__init__(vendor_id, product_id)
        self.requests = []
        self.response = None
        self.config = DEVICE_CONFIGS.get(product_id, {})

    def write(self, data):
        super().write(data)
        self.requests.append(data)

        assert data[0] == PROTOCOL_HEADER
        command = data[1]

        self.response = self.config.get("responses", {}).get(command)

    def read(self, length, **kwargs):
        pre = super().read(length, **kwargs)
        if pre:
            return pre

        buf = bytearray(65)
        buf[0] = PROTOCOL_HEADER

        if self.response:
            response = bytes.fromhex(self.response)
            buf[: len(response)] = response

        return buf[:length]


def _create_mock_ryujin(product_id):
    config = DEVICE_CONFIGS[product_id]
    return AsusRyujin(
        _MockRyujinDevice(vendor_id=0x0B05, product_id=product_id),
        config["name"],
        fan_count=config["fan_count"],
        pump_speed_offset=config["pump_speed_offset"],
        pump_fan_speed_offset=config["pump_fan_speed_offset"],
        temp_offset=config["temp_offset"],
        duty_channel=config["duty_channel"],
    )


def test_prepare_lcd_frame_preserves_pixel_positions_and_rgb_order(tmp_path):
    width, height = 640, 480
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width // 2 - 1, height // 2 - 1), fill=(255, 0, 0))
    draw.rectangle((width // 2, 0, width - 1, height // 2 - 1), fill=(0, 255, 0))
    draw.rectangle((0, height // 2, width // 2 - 1, height - 1), fill=(0, 0, 255))
    draw.rectangle((width // 2, height // 2, width - 1, height - 1), fill=(255, 255, 255))
    path = tmp_path / "corners.png"
    image.save(path)

    frame = _prepare_lcd_frame(path)
    row_size = width * 3

    assert len(frame) == width * height * 3
    assert frame[0:3] == bytes((255, 0, 0))
    assert frame[row_size - 3 : row_size] == bytes((0, 255, 0))
    assert frame[-row_size : -row_size + 3] == bytes((0, 0, 255))
    assert frame[-3:] == bytes((255, 255, 255))


def test_set_static_screen_uses_validated_lcd_sequence(mock_ryujin3, tmp_path):
    image = Image.new("RGB", (640, 480), color=(255, 0, 0))
    path = tmp_path / "red.png"
    image.save(path)
    bulk_device = MockPyusbDevice(vendor_id=0x0B05, product_id=0x1BCB)
    mock_ryujin3._bulk_device = bulk_device

    with mock_ryujin3.connect():
        mock_ryujin3.set_screen(channel="lcd", mode="static", value=path)

    assert [request[1] for request in mock_ryujin3.device.requests[-3:]] == [
        CMD_GET_LCD_MODE,
        CMD_SET_LCD_MODE,
        CMD_ANNOUNCE_LCD_FRAME,
    ]
    assert mock_ryujin3.device.requests[-2][2:5] == [0x20, 0x00, 0x00]
    assert mock_ryujin3.device.requests[-1][2:7] == [0x03, 0x00, 0x10, 0x0E, 0x00]
    transfer, endpoint, frame = bulk_device._sent_xfers[-1]
    assert transfer == "write"
    assert endpoint == 0x02
    assert len(frame) == 640 * 480 * 3
    assert frame[:3] == bytes((255, 0, 0))


@pytest.mark.parametrize("mode", ["static", "gif"])
def test_invalid_lcd_asset_does_not_switch_to_raw_mode(mock_ryujin3, tmp_path, mode):
    path = tmp_path / f"missing.{mode}"

    with mock_ryujin3.connect():
        with pytest.raises(ValueError, match=f"invalid {mode} configuration"):
            mock_ryujin3.set_screen(channel="lcd", mode=mode, value=path)

    assert not mock_ryujin3.device.requests


def test_invalid_stats_background_does_not_switch_to_raw_mode(mock_ryujin3, tmp_path):
    path = tmp_path / "stats.json"
    path.write_text(json.dumps({"background": "missing.gif"}))

    with mock_ryujin3.connect():
        with pytest.raises(ValueError, match="invalid stats configuration"):
            mock_ryujin3.set_screen(channel="lcd", mode="stats", value=path)

    assert not mock_ryujin3.device.requests


def test_lcd_animation_frames_are_converted_and_keep_their_duration(tmp_path):
    path = tmp_path / "two-frames.gif"
    Image.new("RGB", (640, 480), color=(255, 0, 0)).save(
        path,
        save_all=True,
        append_images=[Image.new("RGB", (640, 480), color=(0, 0, 255))],
        duration=[50, 100],
        loop=0,
    )

    frames = _iter_lcd_animation(path)
    first_frame, first_duration = next(frames)
    second_frame, second_duration = next(frames)

    assert first_frame[:3] == bytes((255, 0, 0))
    assert first_duration == 0.05
    assert second_frame[:3] == bytes((0, 0, 255))
    assert second_duration == 0.1


def test_lcd_statistics_renderer_returns_a_full_nonblank_frame(tmp_path):
    background_path = tmp_path / "background.png"
    Image.new("RGB", (640, 480), color=(1, 2, 3)).save(background_path)
    path = tmp_path / "stats.json"
    path.write_text(
        json.dumps(
            {
                "background_color": "100713",
                "font_color": "B300FF",
                "background_opacity": 0.2,
                "interval": 3,
                "title": "COOLER",
                "background": "background.png",
                "layout": {
                    "liquid": {
                        "background_color": "210B2D",
                        "background_opacity": 0.2,
                        "offset_x": -4,
                        "offset_y": 6,
                        "font_color": "B300FF",
                        "stats": [{"stat": "liquid_temperature", "indicator": "LIQUID"}],
                    }
                },
            }
        )
    )
    config = _load_lcd_stats_config(path, None)
    background = _load_lcd_static_background(config["background"])
    frame = _render_lcd_stats(
        [
            ("Liquid temperature", 29.9, "°C"),
            ("Pump speed", 1260, "rpm"),
            ("Pump fan speed", 870, "rpm"),
        ],
        config,
        0,
        3,
        background,
    )

    assert config["background_color"] == (16, 7, 19)
    assert config["font_color"] == (179, 0, 255)
    assert config["background_opacity"] == 0.2
    assert config["interval"] == 3
    assert config["title"] == "COOLER"
    assert list(config["layout"]) == ["liquid"]
    assert config["layout"]["liquid"]["background_color"] == (33, 11, 45)
    assert config["layout"]["liquid"]["background_opacity"] == 0.2
    assert config["layout"]["liquid"]["offset_x"] == -4
    assert config["layout"]["liquid"]["offset_y"] == 6
    assert config["layout"]["liquid"]["font_color"] == (179, 0, 255)
    assert config["background"] == background_path
    assert len(frame) == 640 * 480 * 3
    assert frame[:3] == bytes((4, 3, 6))
    assert any(frame)


def test_lcd_statistics_color_accepts_optional_hash_and_rejects_invalid_values():
    assert _parse_lcd_color("B300FF") == (179, 0, 255)
    assert _parse_lcd_color("#B300FF") == (179, 0, 255)
    assert _parse_lcd_color(100713) == (16, 7, 19)
    with pytest.raises(ValueError, match="six-digit RGB"):
        _parse_lcd_color("purple")


@pytest.mark.parametrize("interval", [0, -1])
def test_lcd_statistics_shorthand_rejects_non_positive_intervals(interval):
    with pytest.raises(ValueError, match="interval must be greater than zero"):
        _load_lcd_stats_config("B300FF", interval)


def test_contrib_lcd_dashboard_examples_only_use_cooler_telemetry():
    examples = (
        "extra/contrib/asus_ryujin/example_layouts/ryujin_extreme_stats.json",
        "extra/contrib/asus_ryujin/example_layouts/ryujin_extreme_st4.json",
    )

    for path in examples:
        config = _load_lcd_stats_config(path, None)
        stats = [stat["stat"] for card in config["layout"].values() for stat in card["stats"]]
        assert set(stats) <= {
            "liquid_temperature",
            "pump_duty",
            "pump_speed",
            "pump_fan_duty",
            "pump_fan_speed",
        }


@pytest.mark.parametrize(
    "value,unit,max_digits,expected",
    [
        (35.2, "°C", 5, "35.2°C"),
        (1860, "rpm", 5, "1860rpm"),
        (12_430, "MHz", 5, "12430MHz"),
        (1_200_000, "", 5, "1.2M"),
        ("4.25", "GHz", 5, "4.25GHz"),
        ("N/A", "", 5, "N/A"),
    ],
)
def test_lcd_statistics_values_fit_their_digit_budget(value, unit, max_digits, expected):
    assert _format_lcd_value(value, unit, max_digits) == expected


def test_lcd_custom_stat_runs_an_argv_command_without_a_shell(monkeypatch):
    config = _load_lcd_stats_config(None, None)
    config["layout"] = {
        "custom": {
            "background_color": None,
            "font_color": None,
            "stats": [
                {
                    "stat": "custom",
                    "indicator": "TEST",
                    "command": ["metric-tool", "--value"],
                    "unit": "widgets",
                }
            ],
        }
    }
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout="42\n")

    monkeypatch.setattr(asus_ryujin_lcd.subprocess, "run", run)
    custom_values = _read_lcd_custom_stats(config, 0)
    frame = _render_lcd_stats([], config, 0, 5, custom_values=custom_values)

    assert len(frame) == 640 * 480 * 3
    assert calls == [
        (
            ["metric-tool", "--value"],
            {
                "shell": False,
                "capture_output": True,
                "check": True,
                "text": True,
                "timeout": 2,
            },
        )
    ]


def test_lcd_custom_stat_rejects_a_shell_command_string(tmp_path):
    path = tmp_path / "stats.json"
    path.write_text(
        json.dumps(
            {
                "layout": {
                    "custom": {
                        "stats": [
                            {"stat": "custom", "indicator": "TEST", "command": "echo 42"}
                        ]
                    }
                }
            }
        )
    )

    with pytest.raises(ValueError, match="non-empty list of strings"):
        _load_lcd_stats_config(path, None)


@pytest.fixture
def mock_ryujin():
    return _create_mock_ryujin(0x1988)


@pytest.fixture
def mock_ryujin3():
    return _create_mock_ryujin(0x1BCB)


@pytest.mark.parametrize("product_id", [0x1988, 0x1BCB, 0x1ADE, 0x1AA2])
def test_initialize(product_id):
    config = DEVICE_CONFIGS[product_id]
    device = _create_mock_ryujin(product_id)

    with device.connect():
        (firmware_status,) = device.initialize()
        assert firmware_status[1] == config["expected_firmware"]


@pytest.mark.parametrize("product_id", [0x1988, 0x1BCB, 0x1ADE, 0x1AA2])
def test_status(product_id):
    config = DEVICE_CONFIGS[product_id]
    device = _create_mock_ryujin(product_id)

    with device.connect():
        actual = device.get_status()

        expected = []
        for item in config["expected_status"]:
            name, value, unit = item
            if name == "Liquid temperature":
                expected.append((name, pytest.approx(value), unit))
            else:
                expected.append((name, value, unit))

        assert sorted(actual) == sorted(expected)


def test_set_fixed_speeds_ryujin2(mock_ryujin):
    with mock_ryujin.connect():
        mock_ryujin.set_fixed_speed(channel="pump", duty=10)
        assert mock_ryujin.device.requests[-1][2] == 0x00
        assert mock_ryujin.device.requests[-1][3] == 0x0A

        mock_ryujin.set_fixed_speed(channel="pump-fan", duty=20)
        assert mock_ryujin.device.requests[-1][2] == 0x00
        assert mock_ryujin.device.requests[-1][4] == 0x14

        mock_ryujin.set_fixed_speed(channel="external-fans", duty=30)
        assert mock_ryujin.device.requests[-1][4] == 0x4C

        mock_ryujin.set_fixed_speed(channel="fans", duty=40)
        assert mock_ryujin.device.requests[-2][4] == 0x28
        assert mock_ryujin.device.requests[-1][4] == 0x66


def test_set_fixed_speeds_ryujin3(mock_ryujin3):
    with mock_ryujin3.connect():
        mock_ryujin3.set_fixed_speed(channel="pump", duty=70)
        assert mock_ryujin3.device.requests[-1][2] == 0x01
        assert mock_ryujin3.device.requests[-1][3] == 0x46

        mock_ryujin3.set_fixed_speed(channel="pump-fan", duty=50)
        assert mock_ryujin3.device.requests[-1][2] == 0x01
        assert mock_ryujin3.device.requests[-1][4] == 0x32
