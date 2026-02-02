import pytest
from _testutils import MockHidapiDevice

from liquidctl.driver.lianli_uni import LianLiUni, ChannelMode

_STABLE_NAMES = [f"fan{i}" for i in range(1, 5)]
_UNSTABLE_NAMES = list(range(1, 5))
_VALID_CHANNELS = _STABLE_NAMES + _UNSTABLE_NAMES
_INVALID_CHANNELS = ["fan0", "fan5", 0, 5]


@pytest.fixture
def mock_lianli_uni():
    # Mock device for testing
    raw = MockHidapiDevice()
    return LianLiUni(raw, "Mock Lian Li Uni SL V2", device_type="SLV2")


@pytest.mark.parametrize("channel", _VALID_CHANNELS)
def test_toggle_pwm_sync(mock_lianli_uni, channel):
    # Enable PWM sync
    mock_lianli_uni.set_fan_control_mode(channel, ChannelMode.AUTO)
    # Disable PWM sync
    mock_lianli_uni.set_fan_control_mode(channel, ChannelMode.FIXED)


@pytest.mark.parametrize("channel", _VALID_CHANNELS)
def test_set_fixed_speed(mock_lianli_uni, channel):
    # Initially, PWM is disabled, so setting a speed should work
    mock_lianli_uni.set_fixed_speed(channel, 50)


@pytest.mark.parametrize("channel", _INVALID_CHANNELS)
def test_pwm_sync_invalid_channel_indices(mock_lianli_uni, channel):
    with pytest.raises(ValueError):
        mock_lianli_uni.set_fan_control_mode(channel, ChannelMode.FIXED)


@pytest.mark.parametrize("channel", _INVALID_CHANNELS)
def test_fixed_speed_invalid_channel_indices(mock_lianli_uni, channel):
    with pytest.raises(ValueError):
        mock_lianli_uni.set_fixed_speed(channel, 50)
