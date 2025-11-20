import pytest, logging
from _testutils import MockHidapiDevice
from liquidctl.driver.lianli_uni import LianLiUni

@pytest.fixture
def mock_lianli_uni():
    # Mock device for testing
    raw = MockHidapiDevice()
    return LianLiUni(raw, "Mock Lian Li Uni SL V2", device_type="SLV2")

def test_initialize(mock_lianli_uni):
    status = mock_lianli_uni.initialize()
    
    # Verify initialization status
    assert ("Device", "Mock Lian Li Uni SL V2", "") in status
    assert ("Firmware version", "N/A", "") in status
    
    # Verify PWM sync is disabled on all channels
    for channel, state in mock_lianli_uni.pwm_channels.items():
        assert state == False

def test_get_status(mock_lianli_uni):
    # Set some mock speeds and verify they are reported
    mock_lianli_uni.channel_speeds = {
        0: 25.0,
        1: 50.0,
        2: 75.0,
        3: 100.0,
    }

    status = mock_lianli_uni.get_status()
    
    expected_status = [
        ("Channel 1", 25.0, "%"),
        ("Channel 2", 50.0, "%"),
        ("Channel 3", 75.0, "%"),
        ("Channel 4", 100.0, "%"),
    ]
    
    assert sorted(status) == sorted(expected_status)

def test_toggle_pwm_sync(mock_lianli_uni):
    # Test enabling and disabling PWM sync
    channel = 0
    
    # Initial state should be False
    assert not mock_lianli_uni.pwm_channels[channel]
    
    # Enable PWM sync
    mock_lianli_uni.toggle_pwm_sync(channel, desired_state=True)
    assert mock_lianli_uni.pwm_channels[channel]
    
    # Disable PWM sync
    mock_lianli_uni.toggle_pwm_sync(channel, desired_state=False)
    assert not mock_lianli_uni.pwm_channels[channel]

def test_set_fixed_speed(mock_lianli_uni, caplog):
    channel = 0
    
    # Initially, PWM is disabled, so setting a speed should work
    mock_lianli_uni.set_fixed_speed(channel, 50)
    assert mock_lianli_uni.channel_speeds[channel] == 50
    
    # Enable PWM, attempting to set speed should log a warning
    mock_lianli_uni.toggle_pwm_sync(channel, desired_state=True)
    with caplog.at_level(logging.WARNING):
        mock_lianli_uni.set_fixed_speed(channel, 75)
    
    # Check that the appropriate warning was logged
    assert "Cannot set fixed speed for Channel 1: PWM is enabled" in caplog.text

def test_invalid_channel_index(mock_lianli_uni):
    # Test setting PWM sync for an invalid channel
    with pytest.raises(ValueError):
        mock_lianli_uni.toggle_pwm_sync(5)  # Out of range
    
    with pytest.raises(ValueError):
        mock_lianli_uni.set_fixed_speed(5, 50)  # Out of range

def test_disconnect(mock_lianli_uni):
    # Ensure the disconnect method can be called without error
    mock_lianli_uni.disconnect()
