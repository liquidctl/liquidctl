"""Tests for the ASUS Ryuo I 240 driver.

Copyright Bloodhundur and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

import pytest

from _testutils import MockHidapiDevice
from liquidctl.driver.asus_ryuo import AsusRyuo

_PREFIX = 0xEC


class _MockRyuoDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0x0B05, product_id=0x1887)
        self.requests = []
        self.response = None

    def write(self, data):
        super().write(data)
        self.requests.append(list(data))

        assert data[0] == _PREFIX
        header = data[1]
        if header == 0x82:
            # Firmware: "AURO0-S452-0205"
            self.response = bytes.fromhex("ec024155524f302d533435322d30323035")
        elif header == 0xEA:
            # Sensor register: byte 3 = coolant temp (32°C)
            self.response = bytearray(65)
            self.response[0] = _PREFIX
            self.response[1] = 0x6A
            self.response[3] = 32  # coolant temp
        else:
            self.response = None

    def read(self, length, **kwargs):
        pre = super().read(length, **kwargs)
        if pre:
            return pre

        buf = bytearray(65)
        buf[0] = _PREFIX

        if self.response:
            if isinstance(self.response, (bytes, bytearray)):
                buf[: len(self.response)] = self.response
            else:
                response = bytes.fromhex(self.response)
                buf[: len(response)] = response

        return buf[:length]


@pytest.fixture
def mockRyuo():
    device = AsusRyuo(_MockRyuoDevice(), "Mock Asus Ryuo I")
    device.connect()
    return device


# -- initialize --


def test_initialize_reports_firmware(mockRyuo):
    (firmware_status,) = mockRyuo.initialize()
    assert firmware_status[0] == "Firmware version"
    assert firmware_status[1] == "AURO0-S452-0205"
    assert firmware_status[2] == ""


# -- get_status --


def test_get_status_reports_coolant_temp(mockRyuo):
    status = mockRyuo.get_status()
    assert len(status) == 1
    assert status[0][0] == "Liquid temperature"
    assert status[0][1] == 32
    assert status[0][2] == "°C"


def test_get_status_sends_correct_request(mockRyuo):
    mockRyuo.get_status()
    # Last request before the read should be the sensor query
    req = mockRyuo.device.requests[-1]
    assert req[0] == _PREFIX
    assert req[1] == 0xEA


# -- set_fixed_speed --


def test_set_fixed_speed_sends_duty(mockRyuo):
    mockRyuo.set_fixed_speed(channel="fans", duty=40)
    req = mockRyuo.device.requests[-1]
    assert req[0] == _PREFIX
    assert req[1] == 0x2A
    assert req[2] == 40


def test_set_fixed_speed_clamps_to_100(mockRyuo):
    mockRyuo.set_fixed_speed(channel="fans", duty=200)
    req = mockRyuo.device.requests[-1]
    assert req[2] == 100


def test_set_fixed_speed_clamps_to_0(mockRyuo):
    mockRyuo.set_fixed_speed(channel="fans", duty=-10)
    req = mockRyuo.device.requests[-1]
    assert req[2] == 0


def test_set_fixed_speed_rejects_invalid_channel(mockRyuo):
    with pytest.raises(ValueError):
        mockRyuo.set_fixed_speed(channel="pump", duty=50)


# -- set_color --


def test_set_color_static(mockRyuo):
    mockRyuo.set_color(channel="led", mode="static", colors=[(255, 0, 0)])
    # Should have sent LED mode command + save command
    assert len(mockRyuo.device.requests) >= 2
    led_req = mockRyuo.device.requests[-2]
    assert led_req[0] == _PREFIX
    assert led_req[1] == 0x3B  # CMD_LED_MODE
    assert led_req[4] == 0x01  # static mode
    assert led_req[5] == 255  # R
    assert led_req[6] == 0  # G
    assert led_req[7] == 0  # B

    save_req = mockRyuo.device.requests[-1]
    assert save_req[0] == _PREFIX
    assert save_req[1] == 0x3F  # CMD_LED_SAVE
    assert save_req[2] == 0x55


def test_set_color_breathing(mockRyuo):
    mockRyuo.set_color(channel="led", mode="breathing", colors=[(0, 255, 0)])
    led_req = mockRyuo.device.requests[-2]
    assert led_req[4] == 0x02  # breathing mode


def test_set_color_off(mockRyuo):
    mockRyuo.set_color(channel="led", mode="off", colors=[])
    led_req = mockRyuo.device.requests[-2]
    assert led_req[4] == 0x00  # off mode
    assert led_req[5] == 0  # R=0
    assert led_req[6] == 0  # G=0
    assert led_req[7] == 0  # B=0


def test_set_color_rejects_invalid_channel(mockRyuo):
    with pytest.raises(ValueError):
        mockRyuo.set_color(channel="fans", mode="static", colors=[(255, 0, 0)])


def test_set_color_rejects_invalid_mode(mockRyuo):
    with pytest.raises(ValueError):
        mockRyuo.set_color(channel="led", mode="disco", colors=[(255, 0, 0)])


# -- set_screen --


def test_set_screen_rejects_invalid_channel(mockRyuo):
    with pytest.raises(ValueError):
        mockRyuo.set_screen(channel="fans", mode="static", value="test.png")


def test_set_screen_rejects_invalid_mode(mockRyuo):
    with pytest.raises(ValueError):
        mockRyuo.set_screen(channel="lcd", mode="video", value="test.mp4")


def test_set_screen_rejects_missing_value(mockRyuo):
    with pytest.raises(ValueError):
        mockRyuo.set_screen(channel="lcd", mode="static", value=None)


def test_set_screen_uploads_gif(mockRyuo, tmp_path):
    """Test that set_screen processes an image and sends the upload protocol."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    # Create a small test image
    img = Image.new("RGB", (160, 128), (255, 0, 0))
    test_file = tmp_path / "test.gif"
    img.save(str(test_file), format="GIF")

    mockRyuo.set_screen(channel="lcd", mode="static", value=str(test_file))

    # Verify the upload protocol sequence
    reqs = mockRyuo.device.requests
    # Should have: init(0x51), slot(0x6B), stop(0x6C), force_stop(0x6C),
    # prepare(0x6C), data chunks(0x6E...), complete(0x6C), finalize(0x6C),
    # commit(0x51), slot_again(0x6B), start_playback(0x6E)
    cmds = [r[1] for r in reqs]

    # Step 1: Init transfer
    assert cmds[0] == 0x51
    assert reqs[0][2] == 0xA0

    # Step 2: Set file slot
    assert cmds[1] == 0x6B

    # Steps 3-4: Stop animation
    assert cmds[2] == 0x6C
    assert reqs[2][2] == 0x01
    assert cmds[3] == 0x6C
    assert reqs[3][2] == 0x03

    # Step 5: Prepare transfer
    assert cmds[4] == 0x6C
    assert reqs[4][2] == 0x04

    # Step 6: Data chunks (at least one)
    assert cmds[5] == 0x6E

    # Find end of data chunks
    data_end = 5
    while data_end < len(cmds) and cmds[data_end] == 0x6E:
        data_end += 1

    # Step 7: Transfer complete
    assert cmds[data_end] == 0x6C
    assert reqs[data_end][2] == 0x05

    # Step 8: Finalize
    assert cmds[data_end + 1] == 0x6C
    assert reqs[data_end + 1][2] == 0xFF

    # Step 9: Commit
    assert cmds[data_end + 2] == 0x51
    assert reqs[data_end + 2][2] == 0x10

    # Step 10: Set slot + start playback
    assert cmds[data_end + 3] == 0x6B
    assert cmds[data_end + 4] == 0x6E
    assert reqs[data_end + 4][2] == 0x00  # start playback
