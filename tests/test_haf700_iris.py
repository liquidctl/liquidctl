"""Unit tests for the HAF 700 EVO IRIS liquidctl driver."""

# uses the psf/black style

import pytest

import hashlib
from pathlib import Path

from liquidctl.driver.haf700_iris import (
    Haf700Iris,
    IrisPageSettings,
    _CMD_SELECT_PAGE,
    _MEDIA_MAX_FILE_SIZE,
    _MEDIA_TMPFS_SIZE_BYTES,
    _MEDIA_MODE_ID,
    _MEDIA_RAM_PREFIX,
    _packet,
    _parse_media_spec,
    _parse_value_spec,
)


def test_cpu_temperature_packet():
    instruction = IrisPageSettings(
        mode=3,
        value=42,
        minimum=0,
        maximum=100,
        scroll=0,
        reserved=b"\x00\x00\x00",
        round_speed=0,
        text_color=0xFFFFFFFF,
        text="",
        background_state=0,
        background_color=0xFF000000,
        image_name="",
        media_name="",
    )

    packet = _packet(_CMD_SELECT_PAGE, instruction.encode())

    assert packet == bytes.fromhex(
        "12 80 00 01 00 18 "
        "03 00 2a 00 00 00 64 00 "
        "00 00 00 00 "
        "ff ff ff ff "
        "00 "
        "00 "
        "ff 00 00 00 "
        "00 "
        "00"
    )


def test_parse_simple_value():
    assert _parse_value_spec("42") == {"value": "42"}


def test_parse_key_value_form():
    parsed = _parse_value_spec(
        "42;minimum=0;maximum=100;text-color=ffffffff;" "background-color=ff000000;action=update"
    )
    assert parsed == {
        "value": "42",
        "minimum": "0",
        "maximum": "100",
        "text_color": "ffffffff",
        "background_color": "ff000000",
        "action": "update",
    }


def test_parse_json_form():
    parsed = _parse_value_spec(
        '{"value": 61.7, "minimum": 0, "maximum": 100, '
        '"text_color": "ffffffff", "action": "auto"}'
    )
    assert parsed["value"] == 61.7
    assert parsed["maximum"] == 100
    assert parsed["action"] == "auto"


def test_capabilities_include_all_native_modes():
    caps = Haf700Iris.get_screen_capabilities()
    assert caps["channel"] == "lcd"
    assert caps["resolution"] == [480, 480]
    assert caps["native_telemetry"] is True
    assert caps["supports_live_update"] is True
    assert [mode["id"] for mode in caps["modes"]] == list(range(1, 14))


class _DummyUsbDevice:
    vendor_id = 0x2516
    product_id = 0x01C1
    release_number = 0x0001
    serial_number = "1234567890ABCDEF"
    bus = "usb3"
    address = 5
    port = (1, 2)


@pytest.fixture
def iris():
    return Haf700Iris(_DummyUsbDevice(), "mock HAF 700 EVO IRIS")


def test_parse_media_spec_string():
    parsed = _parse_media_spec("/tmp/example.png")
    assert parsed["path"] == Path("/tmp/example.png")
    assert parsed["cleanup"] is True


def test_parse_media_spec_mapping():
    parsed = _parse_media_spec({"path": "/tmp/example.png", "cleanup": False})
    assert parsed["path"] == Path("/tmp/example.png")
    assert parsed["cleanup"] is False


def test_capabilities_include_custom_media():
    caps = Haf700Iris.get_screen_capabilities()
    assert caps["custom_media"]["supported"] is True
    assert caps["custom_media"]["mode"] == 17
    assert caps["custom_media"]["ram_filename_prefix"] == "liquidctl/"
    assert caps["custom_media"]["formats"] == ["png", "jpg", "mp4"]
    assert caps["custom_media"]["max_file_size"] == _MEDIA_MAX_FILE_SIZE
    assert caps["custom_media"]["ram_size"] == _MEDIA_TMPFS_SIZE_BYTES


def test_custom_media_mode_routes_to_media_handler(iris, monkeypatch):
    calls = []
    monkeypatch.setattr(iris, "_set_media", lambda value: calls.append(value))

    iris.set_screen("lcd", "image", "/tmp/test.png")

    assert calls == ["/tmp/test.png"]


def test_media_uses_content_addressed_ram_name(iris, monkeypatch, tmp_path):
    media = tmp_path / "test.jpeg"
    media.write_bytes(b"hello world")
    expected_hash = hashlib.sha256(b"hello world").hexdigest()
    expected_remote = f"{_MEDIA_RAM_PREFIX}{expected_hash}.jpg"

    uploaded = []
    selected = []
    cleaned = []

    monkeypatch.setattr(iris, "_ensure_media_tmpfs", lambda: None)
    monkeypatch.setattr(iris, "_file_exists", lambda remote: False)
    monkeypatch.setattr(
        iris,
        "_upload_media",
        lambda remote, data: uploaded.append((remote, data)),
    )

    def fake_select(instruction):
        selected.append(instruction)
        iris._selected_instruction = instruction

    monkeypatch.setattr(iris, "_select", fake_select)
    monkeypatch.setattr(
        iris,
        "_cleanup_liquidctl_media",
        lambda keep: cleaned.append(keep),
    )

    iris._set_media(str(media))

    assert uploaded == [(expected_remote, b"hello world")]
    assert len(selected) == 1
    assert selected[0].mode == _MEDIA_MODE_ID
    assert selected[0].media_name == expected_remote
    assert cleaned == [expected_remote]


def test_existing_media_skips_upload(iris, monkeypatch, tmp_path):
    media = tmp_path / "test.png"
    media.write_bytes(b"same")

    uploaded = []
    monkeypatch.setattr(iris, "_ensure_media_tmpfs", lambda: None)
    monkeypatch.setattr(iris, "_file_exists", lambda remote: True)
    monkeypatch.setattr(
        iris,
        "_upload_media",
        lambda remote, data: uploaded.append((remote, data)),
    )
    monkeypatch.setattr(
        iris,
        "_select",
        lambda instruction: setattr(iris, "_selected_instruction", instruction),
    )

    iris._set_media({"path": str(media), "cleanup": False})

    assert uploaded == []
    assert iris._selected_instruction is not None
    assert iris._selected_instruction.mode == _MEDIA_MODE_ID


def test_cleanup_keeps_current_media(iris, monkeypatch):
    deleted = []
    monkeypatch.setattr(
        iris,
        "_list_liquidctl_media",
        lambda: ["keep.png", "old.png", "other.mp4"],
    )
    monkeypatch.setattr(iris, "_delete_file", lambda remote: deleted.append(remote))

    iris._cleanup_liquidctl_media("liquidctl/keep.png")

    assert deleted == ["liquidctl/old.png", "liquidctl/other.mp4"]


def test_file_exists_uses_magicbox_status_and_echo(iris, monkeypatch):
    remote = "liquidctl/example.png"
    raw = remote.encode("utf-8")
    calls = []

    def fake_send(command, payload=b"", expect_response=False, restore_before_retry=False):
        calls.append((command, payload, expect_response, restore_before_retry))
        from liquidctl.driver.haf700_iris import _CMD_FILE_EXISTS

        return _CMD_FILE_EXISTS, b"\x01" + raw

    monkeypatch.setattr(iris, "_send_resilient", fake_send)

    assert iris._file_exists(remote) is True
    assert calls[0][1] == raw
    assert calls[0][2] is True


def test_named_delete_always_uses_state_one(iris, monkeypatch):
    from liquidctl.driver.haf700_iris import _CMD_DELETE_FILE

    remote = "liquidctl/old.png"
    expected_payload = b"\x01" + remote.encode("utf-8")
    calls = []

    def fake_send(command, payload=b"", expect_response=False, restore_before_retry=False):
        calls.append((command, payload, expect_response, restore_before_retry))
        return _CMD_DELETE_FILE, payload

    monkeypatch.setattr(iris, "_send_resilient", fake_send)
    iris._delete_file(remote)

    assert calls == [(_CMD_DELETE_FILE, expected_payload, True, False)]


def test_upload_media_once_uses_join_chunks_exit_and_verify(iris, monkeypatch):
    from liquidctl.driver.haf700_iris import (
        _CMD_UPLOAD_CHUNK,
        _CMD_FINISH_UPLOAD,
        _CMD_BEGIN_UPLOAD,
    )

    remote = "liquidctl/test.png"
    data = b"example-media"
    calls = []

    def fake_send(command, payload=b"", expect_response=False):
        calls.append((command, payload, expect_response))
        if command == _CMD_BEGIN_UPLOAD:
            return command, b"\x00\x00\x00\x00" + remote.encode("utf-8")
        if command == _CMD_UPLOAD_CHUNK:
            return command, b"\x00\x00\x00\x04"
        if command == _CMD_FINISH_UPLOAD:
            return command, b""
        raise AssertionError(f"unexpected command {command:#x}")

    monkeypatch.setattr(iris, "_send_once", fake_send)
    monkeypatch.setattr(iris, "_file_exists", lambda name: name == remote)

    iris._upload_media_once(remote, data)

    assert calls[0] == (
        _CMD_BEGIN_UPLOAD,
        len(data).to_bytes(4, "big") + remote.encode("utf-8"),
        True,
    )
    assert calls[1] == (_CMD_UPLOAD_CHUNK, b"\x00\x00\x00\x00" + data, True)
    assert calls[2] == (_CMD_FINISH_UPLOAD, b"", True)


def test_media_rejects_unsupported_extension(iris, tmp_path):
    media = tmp_path / "test.gif"
    media.write_bytes(b"GIF89a")

    with pytest.raises(ValueError, match="unsupported HAF700 media type"):
        iris._set_media(str(media))


def test_media_rejects_oversized_file_before_reading(iris, monkeypatch, tmp_path):
    media = tmp_path / "too-large.mp4"
    with media.open("wb") as output:
        output.truncate(_MEDIA_MAX_FILE_SIZE + 1)

    def fail_read_bytes(self):
        raise AssertionError("oversized media should be rejected before read_bytes()")

    monkeypatch.setattr(type(media), "read_bytes", fail_read_bytes)

    with pytest.raises(ValueError, match="media file for HAF700 is too large"):
        iris._set_media(str(media))
