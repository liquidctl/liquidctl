import pytest, logging
from _testutils import MockHidapiDevice
from liquidctl.driver.lianli_uni import LianLiUni, ChannelMode


@pytest.fixture
def mock_lianli_uni():
    # Mock device for testing
    raw = MockHidapiDevice()
    return LianLiUni(raw, "Mock Lian Li Uni SL V2", device_type="SLV2")

def test_toggle_pwm_sync(mock_lianli_uni):
    # Test enabling and disabling PWM sync
    channel = 0

    # Enable PWM sync
    mock_lianli_uni.set_fan_control_mode(channel, ChannelMode.AUTO)

    # Disable PWM sync
    mock_lianli_uni.set_fan_control_mode(channel, ChannelMode.FIXED)


def test_set_fixed_speed(mock_lianli_uni, caplog):
    channel = 0

    # Initially, PWM is disabled, so setting a speed should work
    mock_lianli_uni.set_fixed_speed(channel, 50)


def test_invalid_channel_index(mock_lianli_uni):
    # Test setting PWM sync for an invalid channel
    with pytest.raises(ValueError):
        mock_lianli_uni.set_fan_control_mode(5, ChannelMode.FIXED)  # Out of range

    with pytest.raises(ValueError):
        mock_lianli_uni.set_fixed_speed(5, 50)  # Out of range

