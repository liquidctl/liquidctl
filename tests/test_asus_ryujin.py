import pytest

from _testutils import MockHidapiDevice
from liquidctl.driver.asus_ryujin import AsusRyujin
from liquidctl.error import NotSupportedByDriver

PROTOCOL_HEADER = 0xEC
CMD_GET_FIRMWARE = 0x82
CMD_GET_STATUS = 0x99
CMD_GET_PUMP_DUTY = 0x9A
CMD_GET_FAN_SPEEDS = 0xA0
CMD_GET_FAN_DUTY = 0xA1
CMD_SET_PUMP_DUTY = 0x1A
CMD_SET_FAN_DUTY = 0x21
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


@pytest.fixture
def mock_ryujin():
    product_id = 0x1988
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


@pytest.fixture
def mock_ryujin3():
    product_id = 0x1BCB
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


@pytest.mark.parametrize("product_id", [0x1988, 0x1BCB, 0x1ADE, 0x1AA2])
def test_initialize(product_id):
    config = DEVICE_CONFIGS[product_id]
    device = AsusRyujin(
        _MockRyujinDevice(vendor_id=0x0B05, product_id=product_id),
        config["name"],
        fan_count=config["fan_count"],
        pump_speed_offset=config["pump_speed_offset"],
        pump_fan_speed_offset=config["pump_fan_speed_offset"],
        temp_offset=config["temp_offset"],
        duty_channel=config["duty_channel"],
    )

    with device.connect():
        (firmware_status,) = device.initialize()
        assert firmware_status[1] == config["expected_firmware"]


@pytest.mark.parametrize("product_id", [0x1988, 0x1BCB, 0x1ADE, 0x1AA2])
def test_status(product_id):
    config = DEVICE_CONFIGS[product_id]
    device = AsusRyujin(
        _MockRyujinDevice(vendor_id=0x0B05, product_id=product_id),
        config["name"],
        fan_count=config["fan_count"],
        pump_speed_offset=config["pump_speed_offset"],
        pump_fan_speed_offset=config["pump_fan_speed_offset"],
        temp_offset=config["temp_offset"],
        duty_channel=config["duty_channel"],
    )

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


def test_set_screen_monitor_ryujin2(mock_ryujin):
    with mock_ryujin.connect():
        mock_ryujin.set_screen("lcd", "monitor", "CPU Temp.=47.0°C;CPU Freq.=6.100GHz")

        requests = mock_ryujin.device.requests
        assert len(requests) == 4

        line0, line1, layout, mode = (bytes(r) for r in requests)
        assert len(line0) == 65 and len(layout) == 65

        assert line0[:3] == bytes([0xEC, 0x53, 0x00])
        assert line0[3:13] == b"CPU Temp.\x00"
        assert line0[39:46] == "47.0\u2103".encode()
        assert line0[46:] == bytes(19)

        assert line1[:3] == bytes([0xEC, 0x53, 0x01])
        assert line1[39:47] == "6.100\u338f".encode()

        # dark theme, 2 lines, first line in the temperature group
        assert layout[:9] == bytes([0xEC, 0x52, 0x02, 0x01, 0x02, 0x02, 0x00, 0x00, 0x00])
        assert layout[9:26] == bytes([0xFF] * 17)
        assert layout[26:] == bytes(39)

        assert mode[:3] == bytes([0xEC, 0x51, 0x21])


@pytest.mark.parametrize(
    "value,glyph,group",
    [
        ("1260rpm", "\u218c", 1),
        ("0.718 V", "\u218a", 0),
        ("4.2\u218d", "\u218d", 4),
        ("6.1GHz", "\u338f", 3),
    ],
)
def test_set_screen_monitor_group_from_unit(mock_ryujin, value, glyph, group):
    with mock_ryujin.connect():
        mock_ryujin.set_screen("lcd", "monitor", f"Sensor={value}")
        line, layout, _ = (bytes(r) for r in mock_ryujin.device.requests)
        assert glyph.encode() in line[39:]
        assert layout[3] == 0x00
        assert layout[4] == layout[5] == group


def test_set_screen_monitor_truncates_label(mock_ryujin):
    with mock_ryujin.connect():
        mock_ryujin.set_screen("lcd", "monitor", "CPU Fan Speed=625rpm")
        line = bytes(mock_ryujin.device.requests[0])
        assert line[3:15] == b"CPU Fan Spe\x00"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "no-equals",
        "A=1;B=2;C=3;D=4;E=5",
        "A=1",
        "A=123456789012°C",
        "A=47°C;B=123456789012°C",
    ],
)
def test_set_screen_monitor_rejects_bad_values(mock_ryujin, value):
    with mock_ryujin.connect():
        with pytest.raises(ValueError):
            mock_ryujin.set_screen("lcd", "monitor", value)
        assert mock_ryujin.device.requests == []


def test_set_screen_unsupported(mock_ryujin, mock_ryujin3):
    with mock_ryujin.connect():
        with pytest.raises(NotSupportedByDriver):
            mock_ryujin.set_screen("lcd", "static", "image.png")
    with mock_ryujin3.connect():
        with pytest.raises(NotSupportedByDriver):
            mock_ryujin3.set_screen("lcd", "monitor", "CPU=47°C")
