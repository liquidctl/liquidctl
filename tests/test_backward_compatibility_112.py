"""Test backward compatibility with liquidctl 1.12.x."""

# uses the psf/black style

import pytest
from _testutils import MockHidapiDevice, Report, MockRuntimeStorage

from test_commander_pro import commanderProDevice


def test_initialize_commander_pro_fan_modes(commanderProDevice, caplog):
    """Fix #615 but preserve API compatibility."""

    responses = [
        "000009d4000000000000000000000000",  # firmware
        "00000500000000000000000000000000",  # bootloader
        "00010100010000000000000000000000",  # temp probes
        "00010102000000000000000000000000",  # fan set (throw away)
        "00010102000000000000000000000000",  # fan set (throw away)
        "00010102000000000000000000000000",  # fan set (throw away)
        "00010102000000000000000000000000",  # fan probes
    ]
    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice.initialize(direct_access=True, fan_modes={"4": "dc"})

    sent = commanderProDevice.device.sent
    assert len(sent) == 5
    assert sent[3].data[0] == 0x28
    assert sent[3].data[2] == 3
    assert sent[3].data[3] == 1

    assert "deprecated parameter name `fan_modes`" in caplog.text
