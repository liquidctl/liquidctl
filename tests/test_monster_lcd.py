import pytest
from _testutils import MockHidapiDevice

import json

import liquidctl.driver.monster_lcd as monster_lcd_driver
from liquidctl.driver.monster_lcd import MonsterLcd, _pack_frame
from liquidctl.driver.usb import HidapiDevice
from liquidctl.error import NotSupportedByDevice


@pytest.fixture
def mock_monster_lcd():
    device = MockHidapiDevice(vendor_id=0x1D6B, product_id=0x0130, address="addr")
    dev = MonsterLcd(
        device,
        "mock Monster Tulpar TD3 AIO LCD",
        _time=lambda: 1700000000,
        _sleep=lambda _: None,
    )
    dev.connect()
    return dev


def _unescape(data):
    unescaped = bytearray()
    index = 0
    while index < len(data):
        if data[index] != 0x5B:
            unescaped.append(data[index])
            index += 1
        else:
            escaped = data[index + 1]
            unescaped.append({0x01: 0x5A, 0x02: 0x5B}[escaped])
            index += 2
    return bytes(unescaped)


def _decode_report(report):
    assert report.number == 0
    frame = bytes(report.data)
    assert frame[0] == 0x5A
    assert frame[-1] == 0x5A
    inner = _unescape(frame[1:-1])
    assert int.from_bytes(inner[:2], "big") == len(inner) + 2
    assert sum(inner[:-1]) & 0xFF == inner[-1]
    return inner[2:-1]


def _decode_request(report):
    payload = _decode_report(report)
    head, separator, body = payload.partition(b"\r\n\r\n")
    assert separator
    lines = head.decode().split("\r\n")
    headers = dict(line.split("=", 1) for line in lines[1:])
    return lines[0], headers, body


def test_known_frame_and_escaping():
    assert _pack_frame(b"abc").hex() == "5a00086162632e5a"
    frame = _pack_frame(b"Z[")
    assert b"\x5b\x01" in frame
    assert b"\x5b\x02" in frame


def test_initialize_is_ack_optional_and_exact(mock_monster_lcd):
    assert mock_monster_lcd.initialize(startup_gap=0) == []

    assert len(mock_monster_lcd.device.sent) == 4
    requests = [_decode_request(report) for report in mock_monster_lcd.device.sent]
    assert [request[0] for request in requests] == [
        "POST conn 1",
        "POST power 1",
        "STATE all 1",
        "POST power 1",
    ]
    assert json.loads(requests[1][2]) == {}
    assert json.loads(requests[3][2]) == {"event": "resume"}
    assert requests[0][1]["SeqNumber"] == "0"
    assert requests[3][1]["SeqNumber"] == "3"
    assert all(request[1]["Date"] == "1700000000000" for request in requests)


def test_initialize_rejects_negative_gap(mock_monster_lcd):
    with pytest.raises(ValueError, match="cannot be negative"):
        mock_monster_lcd.initialize(startup_gap=-1)
    assert not mock_monster_lcd.device.sent


def test_keep_alive_sends_resume_then_state(mock_monster_lcd):
    assert mock_monster_lcd.keep_alive() == [0, 1]
    requests = [_decode_request(report) for report in mock_monster_lcd.device.sent]
    assert [request[0] for request in requests] == ["POST power 1", "STATE all 1"]
    assert json.loads(requests[0][2]) == {"event": "resume"}
    assert requests[1][2] == b""


@pytest.mark.parametrize(
    ("value", "firmware_value"),
    [(0, 10), (5, 15), (50, 55), (100, 100), (-10, 10), (110, 100)],
)
def test_set_brightness_maps_to_firmware_range(mock_monster_lcd, value, firmware_value):
    mock_monster_lcd.set_screen("lcd", "brightness", str(value))
    first_line, _, body = _decode_request(mock_monster_lcd.device.sent[0])
    assert first_line == "POST brightness 1"
    assert json.loads(body) == {"value": firmware_value}


@pytest.mark.parametrize("orientation", [0, 90, 180, 270])
def test_set_orientation(mock_monster_lcd, orientation):
    mock_monster_lcd.set_screen("lcd", "orientation", str(orientation))
    first_line, _, body = _decode_request(mock_monster_lcd.device.sent[0])
    assert first_line == "POST rotate 1"
    assert json.loads(body) == {"degree": orientation}


def test_set_orientation_rejects_non_right_angle(mock_monster_lcd):
    with pytest.raises(ValueError, match="one of 0, 90, 180 or 270"):
        mock_monster_lcd.set_screen("lcd", "orientation", "45")
    assert not mock_monster_lcd.device.sent


def test_wake_and_keep_alive_modes_accept_no_value(mock_monster_lcd):
    assert mock_monster_lcd.set_screen("lcd", "wake", None) == 0
    assert mock_monster_lcd.set_screen("lcd", "keep-alive", None) == [1, 2]


def test_screen_mode_validation(mock_monster_lcd):
    with pytest.raises(ValueError, match="only the 'lcd' channel"):
        mock_monster_lcd.set_screen("pump", "brightness", "50")
    with pytest.raises(ValueError, match="requires a value"):
        mock_monster_lcd.set_screen("lcd", "brightness", None)
    with pytest.raises(ValueError, match="requires an integer"):
        mock_monster_lcd.set_screen("lcd", "brightness", "bright")
    with pytest.raises(ValueError, match="does not accept a value"):
        mock_monster_lcd.set_screen("lcd", "wake", "now")
    with pytest.raises(ValueError, match="unsupported screen mode"):
        mock_monster_lcd.set_screen("lcd", "gif", "image.gif")


def test_unsupported_cooling_and_color_methods(mock_monster_lcd):
    with pytest.raises(NotSupportedByDevice):
        mock_monster_lcd.set_fixed_speed("fan", 50)
    with pytest.raises(NotSupportedByDevice):
        mock_monster_lcd.set_speed_profile("fan", [(30, 40)])
    with pytest.raises(NotSupportedByDevice):
        mock_monster_lcd.set_color("lcd", "fixed", [(255, 0, 0)])


def test_get_status_is_empty(mock_monster_lcd):
    assert mock_monster_lcd.get_status() == []


def test_libusb_hidapi_fallback_finds_device_when_hidraw_does_not(monkeypatch):
    preferred_hidapi = object()
    libusb_hidapi = object()
    fallback_device = MockHidapiDevice(
        vendor_id=0x1D6B,
        product_id=0x0130,
        address="fallback-address",
    )

    def enumerate_devices(cls, api, vid=None, pid=None):
        assert (vid, pid) == (0x1D6B, 0x0130)
        if api is preferred_hidapi:
            return iter(())
        assert api is libusb_hidapi
        return iter((fallback_device,))

    monkeypatch.setattr(monster_lcd_driver, "_PREFERRED_HIDAPI", preferred_hidapi)
    monkeypatch.setattr(monster_lcd_driver, "_LIBUSB_HIDAPI", libusb_hidapi)
    monkeypatch.setattr(HidapiDevice, "enumerate", classmethod(enumerate_devices))

    devices = list(
        monster_lcd_driver._MonsterLcdLibusbHidapiBus().find_devices(
            vendor=0x1D6B,
            product=0x0130,
        )
    )

    assert len(devices) == 1
    assert isinstance(devices[0], MonsterLcd)
    assert devices[0].device is fallback_device


def test_libusb_hidapi_fallback_avoids_duplicate_hidraw_device(monkeypatch):
    preferred_hidapi = object()
    libusb_hidapi = object()
    preferred_device = MockHidapiDevice(vendor_id=0x1D6B, product_id=0x0130)
    used_libusb_fallback = False

    def enumerate_devices(cls, api, vid=None, pid=None):
        nonlocal used_libusb_fallback
        assert (vid, pid) == (0x1D6B, 0x0130)
        if api is preferred_hidapi:
            return iter((preferred_device,))
        used_libusb_fallback = True
        return iter(())

    monkeypatch.setattr(monster_lcd_driver, "_PREFERRED_HIDAPI", preferred_hidapi)
    monkeypatch.setattr(monster_lcd_driver, "_LIBUSB_HIDAPI", libusb_hidapi)
    monkeypatch.setattr(HidapiDevice, "enumerate", classmethod(enumerate_devices))

    devices = list(monster_lcd_driver._MonsterLcdLibusbHidapiBus().find_devices())

    assert devices == []
    assert not used_libusb_fallback
