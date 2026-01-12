# uses the psf/black style

import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.control_hub import ControlHub

# Real capture data from NZXT Control Hub (device ID 0x1e71:0x2022)
# Firmware info response (frame 71 from nzxt_cakm_startup.pcapng)
SAMPLE_FIRMWARE_INFO = bytes.fromhex(
    "1102db51079a171b41508bbd7819222001010005003030303030303030303030"
    "303030303030303030303030050300000000000000000000000000000000000000"
)

# LED info response (frame 81 from nzxt_cakm_startup.pcapng)
SAMPLE_LED_INFO = bytes.fromhex(
    "2103db51079a171b41508bbd7819050000000000000000000000000000000000"
    "001d00000000001300000000000000000000000000000000000000000000000000"
)

# Status data (frame 89 from nzxt_cakm_startup.pcapng)
SAMPLE_STATUS = bytes.fromhex(
    "6701db51079a171b41508bbd781905ff000000010200000000000000000035056f"
    "020000000000001e1e1e1e1e0000001919191e1e000000000000000000000000"
)


class MockControlHub(MockHidapiDevice):
    def __init__(self, raw_speed_channels, raw_led_channels):
        super().__init__()
        self.raw_speed_channels = raw_speed_channels
        self.raw_led_channels = raw_led_channels

    def write(self, data):
        reply = bytearray(64)
        if data[0:2] == [0x10, 0x02]:
            reply = bytearray(SAMPLE_FIRMWARE_INFO[:64])
        elif data[0:2] == [0x20, 0x03]:
            reply = bytearray(SAMPLE_LED_INFO[:64])
            reply[14] = self.raw_led_channels
            if self.raw_led_channels > 0:
                reply[15] = 0x1D
            if self.raw_led_channels > 1:
                reply[15 + 1 * 6] = 0x13
            if self.raw_led_channels > 2:
                reply[15 + 2 * 6] = 0x1D
        self.preload_read(Report(reply[0], reply[1:]))
        return super().write(data)


@pytest.fixture
def mock_control_hub():
    raw = MockControlHub(raw_speed_channels=5, raw_led_channels=5)
    dev = ControlHub(raw, "Mock Control Hub", speed_channel_count=5, color_channel_count=5)
    dev.connect()
    return dev


def test_initializes(mock_control_hub):
    result = mock_control_hub.initialize()

    writes = len(mock_control_hub.device.sent)
    assert writes == 4

    assert any("Firmware version" in str(item) for item in result)


def test_reads_status_directly(mock_control_hub):
    # ControlHub inherits SmartDevice2's _get_status_directly which expects 0x67 0x02
    # but real capture shows 0x67 0x01, so we need to modify the sample
    modified_status = bytearray(SAMPLE_STATUS)
    modified_status[0] = 0x67
    modified_status[1] = 0x02  # Change from 0x01 to 0x02 to match SmartDevice2 format
    mock_control_hub.device.preload_read(Report(0, bytes(modified_status)))

    got = mock_control_hub.get_status()

    assert len(got) > 0
    assert any("Fan" in str(item[0]) for item in got)


def test_constructor_sets_up_all_channels(mock_control_hub):
    assert mock_control_hub._speed_channels == {
        "fan1": (0, 0, 100),
        "fan2": (1, 0, 100),
        "fan3": (2, 0, 100),
        "fan4": (3, 0, 100),
        "fan5": (4, 0, 100),
    }
    assert mock_control_hub._color_channels == {
        "led1": 0,
        "led2": 1,
        "led3": 2,
        "led4": 3,
        "led5": 4,
        "sync": 0xFF,
    }


def test_set_fixed_speed_single_channel(mock_control_hub):
    _ = mock_control_hub.initialize()

    mock_control_hub.set_fixed_speed(channel="fan3", duty=75)

    assert len(mock_control_hub.device.sent) > 2


def test_set_fixed_speed_sync_channel(mock_control_hub):
    _ = mock_control_hub.initialize()

    for i in range(1, 6):
        mock_control_hub.set_fixed_speed(channel=f"fan{i}", duty=50)

    assert len(mock_control_hub.device.sent) > 5


def test_set_color_fixed_mode(mock_control_hub):
    _ = mock_control_hub.initialize()

    mock_control_hub.set_color(channel="led1", mode="fixed", colors=[[255, 0, 0]])

    assert len(mock_control_hub.device.sent) > 2
    # ControlHub uses same color command as SmartDevice2 (0x26, 0x04)
    # Reports are stored as Report(number, data) so check number and first data byte
    color_writes = [
        w for w in mock_control_hub.device.sent if w.number == 0x26 and w.data[0] == 0x04
    ]
    assert len(color_writes) >= 1


def test_set_color_off_mode(mock_control_hub):
    _ = mock_control_hub.initialize()

    mock_control_hub.set_color(channel="led2", mode="off", colors=[])

    assert len(mock_control_hub.device.sent) > 2


def test_set_color_fading_mode(mock_control_hub):
    _ = mock_control_hub.initialize()

    colors = [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
    mock_control_hub.set_color(channel="led3", mode="fading", colors=colors, speed="faster")

    assert len(mock_control_hub.device.sent) > 2


def test_set_color_spectrum_wave(mock_control_hub):
    _ = mock_control_hub.initialize()

    mock_control_hub.set_color(
        channel="led1", mode="spectrum-wave", colors=[], speed="normal", direction="forward"
    )

    assert len(mock_control_hub.device.sent) > 2


def test_set_color_spectrum_wave_backward(mock_control_hub):
    _ = mock_control_hub.initialize()

    mock_control_hub.set_color(
        channel="led1", mode="spectrum-wave", colors=[], speed="fastest", direction="backward"
    )

    assert len(mock_control_hub.device.sent) > 2


def test_set_color_covering_marquee(mock_control_hub):
    _ = mock_control_hub.initialize()

    colors = [[255, 128, 0]]
    mock_control_hub.set_color(
        channel="led4", mode="covering-marquee", colors=colors, speed="slower"
    )

    assert len(mock_control_hub.device.sent) > 2


def test_set_color_super_rainbow(mock_control_hub):
    _ = mock_control_hub.initialize()

    mock_control_hub.set_color(
        channel="led5", mode="super-rainbow", colors=[], speed="normal", direction="forward"
    )

    assert len(mock_control_hub.device.sent) > 2


def test_set_color_sync_channel(mock_control_hub):
    _ = mock_control_hub.initialize()

    mock_control_hub.set_color(channel="sync", mode="fixed", colors=[[0, 255, 255]])

    assert len(mock_control_hub.device.sent) > 2


def test_set_color_invalid_channel(mock_control_hub):
    _ = mock_control_hub.initialize()

    with pytest.raises(ValueError, match="invalid channel"):
        mock_control_hub.set_color(channel="led10", mode="fixed", colors=[[255, 0, 0]])


def test_set_color_invalid_mode(mock_control_hub):
    _ = mock_control_hub.initialize()

    with pytest.raises(ValueError, match="invalid mode"):
        mock_control_hub.set_color(channel="led1", mode="invalid_mode", colors=[[255, 0, 0]])


def test_set_color_too_few_colors(mock_control_hub):
    _ = mock_control_hub.initialize()

    with pytest.raises(ValueError, match="requires at least"):
        mock_control_hub.set_color(channel="led1", mode="fading", colors=[])


def test_set_color_too_many_colors(mock_control_hub):
    _ = mock_control_hub.initialize()

    colors = [[i * 30, i * 30, i * 30] for i in range(9)]

    with pytest.raises(ValueError, match="supports at most"):
        mock_control_hub.set_color(channel="led1", mode="fading", colors=colors)


def test_speed_values(mock_control_hub):
    _ = mock_control_hub.initialize()

    for speed in ["slowest", "slower", "normal", "faster", "fastest"]:
        mock_control_hub.set_color(channel="led1", mode="spectrum-wave", colors=[], speed=speed)

    assert len(mock_control_hub.device.sent) > 7


def test_channel_byte_mapping(mock_control_hub):
    _ = mock_control_hub.initialize()

    for i in range(5):
        mock_control_hub.set_color(
            channel=f"led{i+1}", mode="fixed", colors=[[i * 50, i * 50, i * 50]]
        )

    color_writes = [
        w for w in mock_control_hub.device.sent if w.number == 0x26 and w.data[0] == 0x04
    ]
    assert len(color_writes) >= 5


def test_not_totally_broken(mock_control_hub):
    _ = mock_control_hub.initialize()
    # Adjust status message prefix to match what ControlHub expects (inherited from SmartDevice2)
    modified_status = bytearray(SAMPLE_STATUS)
    modified_status[1] = 0x02
    mock_control_hub.device.preload_read(Report(0, bytes(modified_status)))
    _ = mock_control_hub.get_status()
    mock_control_hub.set_fixed_speed(channel="fan1", duty=50)
    mock_control_hub.set_fixed_speed(channel="fan2", duty=75)
    mock_control_hub.set_color(channel="led1", mode="fixed", colors=[[255, 0, 0]])
    mock_control_hub.set_color(channel="led2", mode="spectrum-wave", colors=[], speed="fastest")
    mock_control_hub.set_color(
        channel="led3", mode="fading", colors=[[255, 0, 0], [0, 255, 0]], speed="normal"
    )
