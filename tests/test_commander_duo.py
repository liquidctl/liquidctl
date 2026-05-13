from collections import deque

from _testutils import noop
from liquidctl.driver.commander_duo import CommanderDuo
from liquidctl.error import ExpectationNotMet, NotSupportedByDriver


def int_to_le(num, length=2, signed=False):
    return int(num).to_bytes(length=length, byteorder="little", signed=signed)


class MockCommanderDuoDevice:
    def __init__(self):
        self.vendor_id = 0x1B1C
        self.product_id = 0x0C56
        self.address = "addr"
        self.path = b"path"
        self.release_number = None
        self.serial_number = None
        self.bus = None
        self.port = None

        self.open = noop
        self.close = noop
        self.clear_enqueued_reports = noop

        self.sent = []
        self._last_write = bytes()
        self._read_frames = deque()
        self._mode = None
        self._awake = False

        self.firmware_version = (0x00, 0x08, 0x69, 0x00)
        self.fan_statuses = (0x03, 0x01)
        self.speeds = (1124, 0)
        self.temperatures = (30.6, None)
        self.led_counts = (15, 0)
        self.fixed_speed_writes = []
        self.endpoint_writes = []
        self.color_writes = []

    def read(self, length):
        if self._read_frames:
            return list(self._read_frames.popleft())[:length]

        command = self._last_write[2]
        data = bytearray([0x00, command, 0x00])

        if command == 0x02:
            data.extend(self.firmware_version)
        elif command == 0x08:
            data.extend(self._data_for_mode())
        elif command in [0x06, 0x07]:
            data.extend([0x03, 0x00])

        return list(data)[:length]

    def write(self, data):
        data = bytes(data)
        self.sent.append(data)
        self._last_write = data

        if data[0] != 0x00 or data[1] != 0x08:
            raise ValueError("Start of packets going out should be 00:08")

        command = data[2]
        if command == 0x01 and data[3:6] == bytes([0x03, 0x00, 0x02]):
            self._awake = True
        elif command == 0x01 and data[3:6] == bytes([0x03, 0x00, 0x01]):
            self._awake = False
        elif command == 0x0D:
            self._mode = data[4]
        elif command == 0x05:
            self._mode = None
        elif data[2:4] == bytes([0x06, 0x01]):
            data_length = int.from_bytes(data[4:6], byteorder="little")
            data_type = data[8:10]
            payload = data[10 : 8 + data_length]
            self.endpoint_writes.append((data_length, data_type, payload))
            if data_type == bytes([0x07, 0x00]):
                self.fixed_speed_writes.append((data_type, payload))
        elif data[2:4] in [bytes([0x06, 0x00]), bytes([0x07, 0x00])]:
            self.color_writes.append(data[4:])

        return len(data)

    def queue_read_data_response(self, data_type, payload, frame):
        frames = {
            "initial": 2,
            "more": 3,
            "final": 4,
            "close": 5,
        }
        for index in range(6):
            if index == frames[frame]:
                self._read_frames.append(
                    bytes([0x00, 0x08, 0x00]) + bytes(data_type) + bytes(payload)
                )
            else:
                self._read_frames.append(bytes([0x00, 0x08, 0x00, 0xFF, 0xFF]))

    def _data_for_mode(self):
        if self._mode == 0x17:
            data = bytearray([0x06, 0x00, len(self.speeds)])
            for speed in self.speeds:
                data.extend(int_to_le(speed))
            return data
        if self._mode == 0x1A:
            return bytes([0x09, 0x00, len(self.fan_statuses), *self.fan_statuses])
        if self._mode == 0x20:
            data = bytearray([0x0F, 0x00, len(self.led_counts)])
            for count in self.led_counts:
                data.extend(int_to_le(2 if count else 3))
                data.extend(int_to_le(count))
            return data
        if self._mode == 0x21:
            data = bytearray([0x10, 0x00, len(self.temperatures)])
            for temp in self.temperatures:
                if temp is None:
                    data.append(1)
                    data.extend(int_to_le(0))
                else:
                    data.append(0)
                    data.extend(int_to_le(temp * 10))
            return data
        return bytes([0xFF, 0xFF])


def _make_commander_duo_device():
    device = MockCommanderDuoDevice()
    duo = CommanderDuo(device, "Corsair Commander DUO")
    duo.connect()
    return duo


def _assert_raises(exception, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exception:
        return
    raise AssertionError(f"{exception.__name__} was not raised")


def test_initialize_commander_duo():
    commander_duo_device = _make_commander_duo_device()

    res = commander_duo_device.initialize()

    assert res[0] == ("Firmware version", "0.8.105", "")
    assert res[1] == ("Fan port 1 connected", True, "")
    assert res[2] == ("Fan port 2 connected", False, "")
    assert res[3] == ("Temperature sensor 1 connected", True, "")
    assert res[4] == ("Temperature sensor 2 connected", False, "")
    assert res[5] == ("ARGB port 1 LED count", 15, "")
    assert res[6] == ("ARGB port 2 LED count", 0, "")
    assert not commander_duo_device.device._awake


def test_initialize_commander_duo_parses_firmware_0_10_112():
    commander_duo_device = _make_commander_duo_device()
    commander_duo_device.device.firmware_version = (0x00, 0x0A, 0x70, 0x00)

    res = commander_duo_device.initialize()

    assert res[0] == ("Firmware version", "0.10.112", "")


def test_status_commander_duo():
    commander_duo_device = _make_commander_duo_device()

    res = commander_duo_device.get_status()

    assert res == [
        ("Fan speed 1", 1124, "rpm"),
        ("Fan speed 2", 0, "rpm"),
        ("Temperature 1", 30.6, "°C"),
    ]
    assert not commander_duo_device.device._awake


def test_read_data_accepts_matching_payload_in_initial_frame():
    _check_read_data_accepts_matching_payload_in_frame("initial")


def test_read_data_accepts_matching_payload_in_more_frame():
    _check_read_data_accepts_matching_payload_in_frame("more")


def test_read_data_accepts_matching_payload_in_final_frame():
    _check_read_data_accepts_matching_payload_in_frame("final")


def test_read_data_accepts_matching_payload_in_close_frame():
    _check_read_data_accepts_matching_payload_in_frame("close")


def _check_read_data_accepts_matching_payload_in_frame(frame):
    commander_duo_device = _make_commander_duo_device()

    commander_duo_device.device.queue_read_data_response(
        data_type=(0x09, 0x00),
        payload=(0x02, 0x03, 0x01),
        frame=frame,
    )

    assert commander_duo_device._get_connected_fans() == [True, False]


def test_set_fixed_speed_commander_duo_uses_mode_0x18():
    commander_duo_device = _make_commander_duo_device()

    commander_duo_device.set_fixed_speed("fan1", 61)

    close_writes = [
        sent for sent in commander_duo_device.device.sent if sent[2:5] == bytes([0x05, 0x01, 0x01])
    ]
    open_writes = [
        sent for sent in commander_duo_device.device.sent if sent[2:4] == bytes([0x0D, 0x01])
    ]
    write_writes = [
        sent for sent in commander_duo_device.device.sent if sent[2:4] == bytes([0x06, 0x01])
    ]

    assert close_writes[-1][5] == 0x18
    assert open_writes[-1][4] == 0x18
    assert write_writes[-1][4:15] == bytes(
        [0x07, 0x00, 0x00, 0x00, 0x07, 0x00, 0x01, 0x00, 0x00, 0x3D, 0x00]
    )
    assert commander_duo_device.device.fixed_speed_writes[-1] == (
        bytes([0x07, 0x00]),
        bytes([0x01, 0x00, 0x00, 0x3D, 0x00]),
    )
    assert commander_duo_device.device._awake


def test_set_fixed_speed_commander_duo_keeps_software_mode_active():
    commander_duo_device = _make_commander_duo_device()

    commander_duo_device.set_fixed_speed("fan1", 58)

    sleep_commands = [
        sent
        for sent in commander_duo_device.device.sent
        if sent[2:6] == bytes([0x01, 0x03, 0x00, 0x01])
    ]
    assert not sleep_commands
    assert commander_duo_device.device._awake


def test_set_fixed_speed_commander_duo_clamps_duty():
    commander_duo_device = _make_commander_duo_device()

    commander_duo_device.set_fixed_speed("fan1", -10)
    commander_duo_device.set_fixed_speed("fan1", 110)

    assert commander_duo_device.device.fixed_speed_writes[0] == (
        bytes([0x07, 0x00]),
        bytes([0x01, 0x00, 0x00, 0x00, 0x00]),
    )
    assert commander_duo_device.device.fixed_speed_writes[1] == (
        bytes([0x07, 0x00]),
        bytes([0x01, 0x00, 0x00, 0x64, 0x00]),
    )


def test_set_fixed_speed_commander_duo_rejects_invalid_channels():
    commander_duo_device = _make_commander_duo_device()

    for channel in ["fan", "fans", "fan3", -1, 2]:
        _assert_raises(ValueError, commander_duo_device.set_fixed_speed, channel, 50)


def test_set_speed_profile_commander_duo_is_not_supported():
    commander_duo_device = _make_commander_duo_device()

    _assert_raises(
        NotSupportedByDriver, commander_duo_device.set_speed_profile, "fan1", [(25, 30), (40, 80)]
    )


def test_set_color_commander_duo_sets_led_ports_and_writes_rgb_data():
    commander_duo_device = _make_commander_duo_device()

    commander_duo_device.set_color("argb1", "fixed", [(255, 0, 0)], maximum_leds=2)

    endpoint_writes = commander_duo_device.device.endpoint_writes
    color_writes = commander_duo_device.device.color_writes

    assert endpoint_writes[0] == (7, bytes([0x0D, 0x00]), bytes([0x02, 0x01, 0x01, 0x01, 0x00]))
    assert endpoint_writes[1] == (7, bytes([0x0C, 0x00]), bytes([0x02, 0x02, 0x00, 0x00, 0x00]))
    assert color_writes[0][:8] == bytes([0x08, 0x00, 0x00, 0x00, 0x12, 0x00, 0xFF, 0x00])
    assert color_writes[0][8:12] == bytes([0x00, 0xFF, 0x00, 0x00])
    assert commander_duo_device.device.sent[-1][2:5] == bytes([0x05, 0x01, 0x01])
    assert commander_duo_device.device.sent[-1][5] == 0x22
    assert commander_duo_device.device._awake


def test_set_color_commander_duo_honors_sync_channel_and_start_led():
    commander_duo_device = _make_commander_duo_device()
    commander_duo_device.device.led_counts = (3, 2)

    commander_duo_device.set_color("sync", "fixed", [(0x01, 0x02, 0x03)], start_led=2)

    assert commander_duo_device.device.endpoint_writes[0] == (
        7,
        bytes([0x0D, 0x00]),
        bytes([0x02, 0x01, 0x01, 0x01, 0x01]),
    )
    assert commander_duo_device.device.endpoint_writes[1] == (
        7,
        bytes([0x0C, 0x00]),
        bytes([0x02, 0x03, 0x00, 0x02, 0x00]),
    )
    assert commander_duo_device.device.color_writes[0][:6] == bytes(
        [0x11, 0x00, 0x00, 0x00, 0x12, 0x00]
    )
    color_payload = commander_duo_device.device.color_writes[0]
    assert color_payload[6:21] == bytes(
        [
            0x00,
            0x00,
            0x00,
            0x01,
            0x02,
            0x03,
            0x01,
            0x02,
            0x03,
            0x00,
            0x00,
            0x00,
            0x01,
            0x02,
            0x03,
        ]
    )
    assert set(color_payload[21:]) == {0x00}


def test_set_color_commander_duo_splits_large_volatile_rgb_writes():
    commander_duo_device = _make_commander_duo_device()
    commander_duo_device.device.led_counts = (20, 0)

    commander_duo_device.set_color("argb1", "fixed", [(0x01, 0x02, 0x03)])

    color_write_commands = [
        sent[2:4]
        for sent in commander_duo_device.device.sent
        if sent[2:4] in [bytes([0x06, 0x00]), bytes([0x07, 0x00])]
    ]
    assert color_write_commands == [bytes([0x06, 0x00]), bytes([0x07, 0x00])]
    expected_payload = bytes(
        [0x3E, 0x00, 0x00, 0x00, 0x12, 0x00] + [0x01, 0x02, 0x03] * 20
    )
    assert commander_duo_device.device.color_writes[0][:61] == expected_payload[:61]
    assert commander_duo_device.device.color_writes[1][:5] == expected_payload[61:]
    assert set(commander_duo_device.device.color_writes[0][61:]) == {0x00}
    assert set(commander_duo_device.device.color_writes[1][5:]) == {0x00}
    assert commander_duo_device.device.sent[-1][2:5] == bytes([0x05, 0x01, 0x01])
    assert commander_duo_device.device.sent[-1][5] == 0x22


def test_set_color_commander_duo_rejects_invalid_mode():
    commander_duo_device = _make_commander_duo_device()

    _assert_raises(ValueError, commander_duo_device.set_color, "argb1", "rainbow", [])


def test_set_color_commander_duo_rejects_invalid_channel():
    commander_duo_device = _make_commander_duo_device()

    _assert_raises(ValueError, commander_duo_device.set_color, "fan1", "fixed", [(255, 0, 0)])


def test_set_color_commander_duo_rejects_invalid_non_volatile_channel_without_write():
    commander_duo_device = _make_commander_duo_device()

    _assert_raises(
        ValueError,
        commander_duo_device.set_color,
        "fan1",
        "fixed",
        [(255, 0, 0)],
        non_volatile=True,
    )

    assert not commander_duo_device.device.sent
    assert not commander_duo_device.device.endpoint_writes
    assert not commander_duo_device.device.color_writes


def test_set_color_commander_duo_writes_device_memory_color_when_non_volatile(caplog):
    commander_duo_device = _make_commander_duo_device()

    commander_duo_device.set_color(
        "argb1", "fixed", [(0x11, 0x22, 0x33)], maximum_leds=2, non_volatile=True
    )

    open_writes = [
        sent for sent in commander_duo_device.device.sent if sent[2:4] == bytes([0x0D, 0x01])
    ]
    close_writes = [
        sent
        for sent in commander_duo_device.device.sent
        if sent[2:5] == bytes([0x05, 0x01, 0x01])
    ]
    wake_writes = [
        sent
        for sent in commander_duo_device.device.sent
        if sent[2:6] == bytes([0x01, 0x03, 0x00, 0x02])
    ]

    assert "Device Memory lighting is not supported" not in caplog.text
    assert wake_writes
    assert commander_duo_device.device.sent.index(
        wake_writes[-1]
    ) < commander_duo_device.device.sent.index(open_writes[-1])
    assert open_writes[-1][4:6] == bytes([0x65, 0x6D])
    assert close_writes[-1][5:7] == bytes([0x00, 0x00])
    assert commander_duo_device.device.endpoint_writes[-1] == (
        14,
        bytes([0x7E, 0x20]),
        bytes([0x09, 0x00, 0x00, 0x00, 0x01, 0xFF, 0x33, 0x22, 0x11, 0x02, 0x00, 0x01]),
    )
    assert any(sent[2:4] == bytes([0x09, 0x01]) for sent in commander_duo_device.device.sent)
    assert commander_duo_device.device.sent[-1][2:6] == bytes([0x01, 0x03, 0x00, 0x01])
    assert not commander_duo_device.device.color_writes
    assert not commander_duo_device.device._awake


def test_set_color_commander_duo_writes_device_memory_off_when_non_volatile():
    commander_duo_device = _make_commander_duo_device()

    commander_duo_device.set_color("sync", "off", [], non_volatile=True)

    assert commander_duo_device.device.endpoint_writes[-1] == (
        14,
        bytes([0x7E, 0x20]),
        bytes([0x09, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01]),
    )
    assert not commander_duo_device.device.color_writes
    assert not commander_duo_device.device._awake


def test_set_color_commander_duo_writes_device_memory_rainbow_when_non_volatile():
    commander_duo_device = _make_commander_duo_device()

    commander_duo_device.set_color("sync", "rainbow", [], non_volatile=True)

    assert commander_duo_device.device.endpoint_writes[-1] == (
        10,
        bytes([0x02, 0xA4]),
        bytes([0x08, 0x04, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01]),
    )
    assert not commander_duo_device.device.color_writes
    assert not commander_duo_device.device._awake


def test_set_color_commander_duo_device_memory_lighting_only_opens_lighting_endpoint():
    for mode, colors in (
        ("fixed", [(0x11, 0x22, 0x33)]),
        ("off", []),
        ("rainbow", []),
    ):
        commander_duo_device = _make_commander_duo_device()

        commander_duo_device.set_color("sync", mode, colors, non_volatile=True)

        open_endpoints = [
            sent[4:6]
            for sent in commander_duo_device.device.sent
            if sent[2:4] == bytes([0x0D, 0x01])
        ]
        device_memory_endpoints = [
            endpoint for endpoint in open_endpoints if endpoint.endswith(bytes([0x6D]))
        ]

        assert device_memory_endpoints == [bytes([0x65, 0x6D])]
        assert bytes([0x61, 0x6D]) not in open_endpoints
        assert bytes([0x62, 0x6D]) not in open_endpoints
        assert bytes([0x63, 0x6D]) not in open_endpoints


def test_set_color_commander_duo_does_not_invent_led_count_without_override():
    commander_duo_device = _make_commander_duo_device()
    commander_duo_device.device.led_counts = (0, 0)

    commander_duo_device.set_color("argb1", "fixed", [(255, 0, 0)])

    endpoint_writes = commander_duo_device.device.endpoint_writes
    color_writes = commander_duo_device.device.color_writes

    assert endpoint_writes[0] == (7, bytes([0x0D, 0x00]), bytes([0x02, 0x01, 0x00, 0x01, 0x00]))
    assert endpoint_writes[1] == (7, bytes([0x0C, 0x00]), bytes([0x02, 0x00, 0x00, 0x00, 0x00]))
    assert color_writes[0][:6] == bytes([0x02, 0x00, 0x00, 0x00, 0x12, 0x00])
    assert set(color_writes[0][6:]) == {0x00}
    assert commander_duo_device.device._awake


def test_set_color_commander_duo_maximum_leds_overrides_zero_detected_count():
    commander_duo_device = _make_commander_duo_device()
    commander_duo_device.device.led_counts = (0, 0)

    commander_duo_device.set_color("argb1", "fixed", [(0x01, 0x02, 0x03)], maximum_leds=2)

    assert commander_duo_device.device.endpoint_writes[0] == (
        7,
        bytes([0x0D, 0x00]),
        bytes([0x02, 0x01, 0x01, 0x01, 0x00]),
    )
    assert commander_duo_device.device.endpoint_writes[1] == (
        7,
        bytes([0x0C, 0x00]),
        bytes([0x02, 0x02, 0x00, 0x00, 0x00]),
    )
    assert commander_duo_device.device.color_writes[0][:12] == bytes(
        [0x08, 0x00, 0x00, 0x00, 0x12, 0x00, 0x01, 0x02, 0x03, 0x01, 0x02, 0x03]
    )
    assert set(commander_duo_device.device.color_writes[0][12:]) == {0x00}


def test_read_data_commander_duo_raises_on_wrong_dtype():
    commander_duo_device = _make_commander_duo_device()
    for _ in range(18):
        commander_duo_device.device._read_frames.append(bytes([0x00, 0x08, 0x00, 0xFF, 0xFF, 0x00]))

    _assert_raises(ExpectationNotMet, commander_duo_device._get_connected_fans)


def test_software_mode_context_can_restore_hardware_mode_when_requested():
    commander_duo_device = _make_commander_duo_device()

    with commander_duo_device._software_mode_context(restore_hardware_mode=True):
        assert commander_duo_device.device._awake

    assert not commander_duo_device.device._awake
