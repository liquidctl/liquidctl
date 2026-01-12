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
    channel = 1

    # Enable PWM sync
    mock_lianli_uni.set_fan_control_mode(channel, ChannelMode.AUTO)

    # Disable PWM sync
    mock_lianli_uni.set_fan_control_mode(channel, ChannelMode.FIXED)


def test_set_fixed_speed(mock_lianli_uni, caplog):
    channel = 1

    # Initially, PWM is disabled, so setting a speed should work
    mock_lianli_uni.set_fixed_speed(channel, 50)


def test_pwm_sync_channel_indices(mock_lianli_uni):
    # Test setting PWM sync for valid and invalid channels
    with pytest.raises(ValueError):
        mock_lianli_uni.set_fan_control_mode(0, ChannelMode.FIXED)  # Out of range

    mock_lianli_uni.set_fan_control_mode(1, ChannelMode.FIXED)  # In range
    mock_lianli_uni.set_fan_control_mode(2, ChannelMode.FIXED)  # In range
    mock_lianli_uni.set_fan_control_mode(3, ChannelMode.FIXED)  # In range
    mock_lianli_uni.set_fan_control_mode(4, ChannelMode.FIXED)  # In range

    with pytest.raises(ValueError):
        mock_lianli_uni.set_fan_control_mode(5, ChannelMode.FIXED)  # Out of range


def test_fixed_speed_channel_indices(mock_lianli_uni):
    # Test setting fixed speed for valid and invalid channels
    with pytest.raises(ValueError):
        mock_lianli_uni.set_fixed_speed(0, 50)  # Out of range

    mock_lianli_uni.set_fixed_speed(1, 50)  # In range
    mock_lianli_uni.set_fixed_speed(2, 50)  # In range
    mock_lianli_uni.set_fixed_speed(3, 50)  # In range
    mock_lianli_uni.set_fixed_speed(4, 50)  # In range

    with pytest.raises(ValueError):
        mock_lianli_uni.set_fixed_speed(5, 50)  # Out of range
