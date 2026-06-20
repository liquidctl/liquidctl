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
        "has_lcd": False,
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
        "has_lcd": True,
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
        "has_lcd": True,
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
        "has_lcd": True,
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
        "has_lcd": True,
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
        has_lcd=config["has_lcd"],
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
        has_lcd=config["has_lcd"],
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
        has_lcd=config["has_lcd"],
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
        has_lcd=config["has_lcd"],
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


def test_set_screen_liquid(mock_ryujin3):
    with mock_ryujin3.connect():
        mock_ryujin3.set_screen("lcd", "liquid", None)
        sent = mock_ryujin3.device.requests[-1]
        assert sent[0] == PROTOCOL_HEADER
        assert sent[1] == 0x51
        assert sent[2] == 0x04


def test_set_screen_off(mock_ryujin3):
    with mock_ryujin3.connect():
        mock_ryujin3.set_screen("lcd", "off", None)
        sent = mock_ryujin3.device.requests[-1]
        assert sent[0] == PROTOCOL_HEADER
        assert sent[1] == 0x51
        assert sent[2] == 0x00


def test_set_screen_clock_24h(mock_ryujin3):
    with mock_ryujin3.connect():
        mock_ryujin3.set_screen("lcd", "clock", "24h")
        cmds = [r for r in mock_ryujin3.device.requests if r[0] == PROTOCOL_HEADER]
        cmd_bytes = [r[1] for r in cmds]
        assert 0x5D in cmd_bytes  # clock config
        assert 0x11 in cmd_bytes  # set time
        assert 0x51 in cmd_bytes  # mode switch
        mode_cmd = [r for r in cmds if r[1] == 0x51][-1]
        assert mode_cmd[2] == 0x08  # clock mode
        time_cmd = [r for r in cmds if r[1] == 0x11][-1]
        assert time_cmd[6] == 0x00  # hr_fmt 0x00 = 24h


def test_set_screen_brightness(mock_ryujin3):
    with mock_ryujin3.connect():
        mock_ryujin3.set_screen("lcd", "brightness", "75")
        sent = mock_ryujin3.device.requests[-1]
        assert sent[0] == PROTOCOL_HEADER
        assert sent[1] == 0x5C
        assert sent[2] == 0x01
        assert sent[7] == 75


def test_set_screen_standby(mock_ryujin3):
    with mock_ryujin3.connect():
        mock_ryujin3.set_screen("lcd", "standby", None)
        sent = mock_ryujin3.device.requests[-1]
        assert sent[0] == PROTOCOL_HEADER
        assert sent[1] == 0x5C
        assert sent[2] == 0x20


def test_set_screen_wake(mock_ryujin3):
    with mock_ryujin3.connect():
        mock_ryujin3.set_screen("lcd", "wake", None)
        sent = mock_ryujin3.device.requests[-1]
        assert sent[0] == PROTOCOL_HEADER
        assert sent[1] == 0x5C
        assert sent[2] == 0x10


def test_set_screen_release(mock_ryujin3):
    with mock_ryujin3.connect():
        mock_ryujin3.set_screen("lcd", "release", None)
        sent = mock_ryujin3.device.requests[-1]
        assert sent[0] == PROTOCOL_HEADER
        assert sent[1] == 0x1A
        assert sent[2] == 0x00
        assert sent[3] == 0x00
        assert sent[4] == 0x00


def test_set_screen_not_supported_ryujin2(mock_ryujin):
    with mock_ryujin.connect():
        with pytest.raises(NotSupportedByDriver):
            mock_ryujin.set_screen("lcd", "liquid", None)


# ---------------------------------------------------------------------------
# Persistent flash-slot upload (image / gif) tests
#
# These exercise the Armoury-Crate-style persistent upload path added to the
# driver: format/slot selection, the ee-signal-gated state machine, and the
# stuck-state detection. The real path uses a pyusb bulk handle and reads the
# device's async "ee" notifications; here we stub the bulk handle and script the
# ee replies through a small flow-control mock so the logic is covered without
# hardware.
# ---------------------------------------------------------------------------

import io as _io

import pytest

from liquidctl.driver.asus_ryujin import AsusRyujin, _FlashSlotStuck
from liquidctl.error import ExpectationNotMet, NotSupportedByDriver

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _make_jpeg_bytes():
    buf = _io.BytesIO()
    Image.new("RGB", (320, 240), (255, 120, 0)).save(buf, "JPEG")
    return buf.getvalue()


def _make_gif_bytes(n_frames=4):
    frames = [Image.new("RGB", (320, 240), (i * 10, 0, 255 - i * 10)) for i in range(n_frames)]
    buf = _io.BytesIO()
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:], loop=0, duration=80)
    return buf.getvalue()


def _write_tmp(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


class _FakeBulk:
    """Stub pyusb bulk handle: records writes, never touches USB."""

    def __init__(self):
        self.writes = []

    def write(self, endpoint, data, timeout=0):
        self.writes.append((endpoint, bytes(data)))
        return len(data)


def _install_flash_stubs(driver, *, erase_status=0x00, size_status=0x00, chunk_ok=True):
    """Patch the driver's bulk + ee primitives to script a flash upload.

    erase_status: 2nd payload byte of the ee13 erase reply (0x00 = clean,
                  0x10 = stuck).
    size_status:  3rd byte of the ec7f size reply (0x00 = accepted, 0x02 = reject).
    chunk_ok:     whether each chunk gets an ee14 accept.
    """
    bulk = _FakeBulk()
    driver._bulk_only_device = lambda: bulk
    driver._release_raw_usb_device = lambda: None

    state = {"phase": "header"}

    def fake_ee_wait(predicate, total_timeout=4.0):
        # Build candidate reports and return the first the predicate accepts.
        candidates = [
            bytes([0xEC, 0x71, 0x00, 0x01]) + b"\x00" * 8,  # capability
            bytes([0xEE, 0x13, erase_status, 0x01]),  # erase-ready
            bytes([0xEC, 0x7F, size_status, 0x00, 0x10]),  # ready-for-bulk
            bytes([0xEE, 0x14, 0x00, 0x10]),  # chunk accept
            bytes([0xEE, 0x13, 0x00, 0xFF]),  # flash-write done
        ]
        if not chunk_ok:
            candidates = [c for c in candidates if not (c[1] == 0x14)]
        for c in candidates:
            if predicate(c):
                return c
        return None

    driver._ee_wait = fake_ee_wait
    driver._ee_read = lambda total_timeout=4.0: None
    return bulk


@pytest.fixture
def ryujin3(mock_ryujin3):
    return mock_ryujin3


def test_set_screen_image_defaults_static_slot(ryujin3, tmp_path):
    """`image` mode uploads a JPEG (static params) to the static slot (4)."""
    path = _write_tmp(tmp_path, "x.jpg", _make_jpeg_bytes())
    captured = {}

    def spy(p, animation, slot):
        captured.update(path=p, animation=animation, slot=slot)

    ryujin3._upload_flash_slot = spy
    with ryujin3.connect():
        ryujin3.set_screen("lcd", "image", path)
    assert captured["animation"] is False
    assert captured["slot"] == 4


def test_set_screen_gif_defaults_animation_slot(ryujin3, tmp_path):
    """`gif` mode uploads a GIF (anim params) to an animation slot (3, not 4)."""
    path = _write_tmp(tmp_path, "x.gif", _make_gif_bytes())
    captured = {}

    def spy(p, animation, slot):
        captured.update(path=p, animation=animation, slot=slot)

    ryujin3._upload_flash_slot = spy
    with ryujin3.connect():
        ryujin3.set_screen("lcd", "gif", path)
    assert captured["animation"] is True
    assert captured["slot"] == 3  # animation slots are 0-3, never the static slot 4


def test_set_screen_image_requires_path(ryujin3):
    with ryujin3.connect():
        with pytest.raises(ValueError):
            ryujin3.set_screen("lcd", "image", None)


def test_set_screen_gif_requires_path(ryujin3):
    with ryujin3.connect():
        with pytest.raises(ValueError):
            ryujin3.set_screen("lcd", "gif", None)


def test_invalid_mode_lists_new_modes(ryujin3):
    with ryujin3.connect():
        with pytest.raises(ValueError) as exc:
            ryujin3.set_screen("lcd", "bogus", None)
    assert "image" in str(exc.value)
    assert "gif" in str(exc.value)


def test_encode_static_is_jpeg(ryujin3, tmp_path):
    path = _write_tmp(tmp_path, "x.png", _make_jpeg_bytes())
    with ryujin3.connect():
        payload, params = ryujin3._encode_for_flash(path, animation=False)
    assert payload[:3] == b"\xff\xd8\xff"  # JPEG magic
    assert params == [0x01, 0x01]  # static format params


def test_encode_animation_preserves_frames(ryujin3, tmp_path):
    path = _write_tmp(tmp_path, "x.gif", _make_gif_bytes(n_frames=4))
    with ryujin3.connect():
        payload, params = ryujin3._encode_for_flash(path, animation=True)
    assert payload[:6] == b"GIF89a"
    assert params == [0x01, 0x02, 0x03]  # animation format params
    out = Image.open(_io.BytesIO(payload))
    assert getattr(out, "n_frames", 1) == 4  # all frames preserved, not flattened


def test_flash_upload_happy_path_anim(ryujin3, tmp_path):
    """A clean ee sequence drives a full anim upload to the bulk endpoint."""
    path = _write_tmp(tmp_path, "x.gif", _make_gif_bytes())
    with ryujin3.connect():
        bulk = _install_flash_stubs(ryujin3, erase_status=0x00, size_status=0x00, chunk_ok=True)
        ryujin3._upload_flash_slot(path, animation=True, slot=3)
    # at least one 4096-byte bulk chunk reached EP 0x01
    assert bulk.writes, "no bulk payload was written"
    assert all(ep == 0x01 for ep, _ in bulk.writes)
    assert len(bulk.writes[0][1]) == 4096


def test_flash_upload_static_sends_slot_table(ryujin3, tmp_path):
    """Static display sequence sends the ec60 slot-table init + ec51 1f."""
    path = _write_tmp(tmp_path, "x.jpg", _make_jpeg_bytes())
    with ryujin3.connect():
        _install_flash_stubs(ryujin3)
        ryujin3._upload_flash_slot(path, animation=False, slot=4)
        cmds = [r[1] for r in ryujin3.device.requests if r[0] == 0xEC]
    assert 0x60 in cmds  # static slot-table init
    mode = [r for r in ryujin3.device.requests if r[0] == 0xEC and r[1] == 0x51][-1]
    assert mode[2] == 0x1F  # static slideshow display mode


def test_flash_upload_anim_sends_single_anim_mode(ryujin3, tmp_path):
    """Animation display uses ec51 10 01 <slot> and NO ec60 table."""
    path = _write_tmp(tmp_path, "x.gif", _make_gif_bytes())
    with ryujin3.connect():
        _install_flash_stubs(ryujin3)
        ryujin3._upload_flash_slot(path, animation=True, slot=3)
        cmds = [r[1] for r in ryujin3.device.requests if r[0] == 0xEC]
    assert 0x60 not in cmds  # animations do not use the static slot table
    mode = [r for r in ryujin3.device.requests if r[0] == 0xEC and r[1] == 0x51][-1]
    assert mode[2] == 0x10  # single-animation display mode
    assert mode[4] == 3  # addresses the requested slot


def test_flash_upload_stuck_erase_recovers_or_raises(ryujin3, tmp_path):
    """A persistently-stuck erase (ee13 1001) surfaces a clear power-cycle error."""
    path = _write_tmp(tmp_path, "x.gif", _make_gif_bytes())
    with ryujin3.connect():
        _install_flash_stubs(ryujin3, erase_status=0x10, size_status=0x02)
        # make the unstick sweep a no-op so the retry stays stuck
        ryujin3._unstick_flash = lambda: None
        with pytest.raises(ExpectationNotMet) as exc:
            ryujin3._upload_flash_slot(path, animation=True, slot=3)
    assert "power-cycle" in str(exc.value.args[0]).lower()


def test_attempt_flash_upload_raises_flashslotstuck(ryujin3, tmp_path):
    """The low-level attempt raises the internal _FlashSlotStuck on a stuck erase."""
    path = _write_tmp(tmp_path, "x.gif", _make_gif_bytes())
    with ryujin3.connect():
        _install_flash_stubs(ryujin3, erase_status=0x10, size_status=0x02)
        with pytest.raises(_FlashSlotStuck):
            ryujin3._attempt_flash_upload(path, animation=True, slot=3)


def test_flash_modes_not_supported_on_ryujin2(mock_ryujin, tmp_path):
    path = _write_tmp(tmp_path, "x.gif", _make_gif_bytes())
    with mock_ryujin.connect():
        with pytest.raises(NotSupportedByDriver):
            mock_ryujin.set_screen("lcd", "gif", path)
