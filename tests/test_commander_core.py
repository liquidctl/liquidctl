import pytest
from collections import deque

from liquidctl import ExpectationNotMet
from liquidctl.driver.commander_core import CommanderCore
from _testutils import noop


def int_to_le(num, length=2, byteorder='little', signed=False):
    return int(num).to_bytes(length=length, byteorder=byteorder, signed=signed)


class MockCommanderCoreDevice:
    def __init__(self):
        self.vendor_id = 0x1b1c
        self.product_id = 0x0c1c
        self.address = "addr"
        self.release_number = None
        self.serial_number = None
        self.bus = None
        self.port = None

        self.open = noop
        self.close = noop
        self.clear_enqueued_reports = noop

        self._read = deque()
        self.sent = list()

        self._last_write = bytes()
        self._modes = {}

        self._awake = False

        self.response_prefix = ()
        self.firmware_version = (0x00, 0x00, 0x00)
        self.led_counts = (None, None, None, None, None, None, None)
        self.speeds = (None, None, None, None, None, None, None)
        self.temperatures = (None, None)

    def read(self, length):
        data = bytearray([0x00, self._last_write[2], 0x00])
        data.extend(self.response_prefix)

        if self._last_write[2] == 0x02:  # Firmware version
            for i in range(0, 3):
                data.append(self.firmware_version[i])
        if self._awake:
            if self._last_write[2] == 0x08:  # Get data
                channel = self._last_write[3]
                mode = self._modes[channel]
                if mode == 0x17:  # Get speeds
                    data.extend([0x06, 0x00])
                    data.append(len(self.speeds))
                    for i in self.speeds:
                        if i is None:
                            data.extend([0x00, 0x00])
                        else:
                            data.extend(int_to_le(i))
                elif mode == 0x20:  # LED detect
                    data.extend([0x0f, 0x00])
                    data.append(len(self.led_counts))
                    for i in self.led_counts:
                        if i is None:
                            data.extend(int_to_le(3)+int_to_le(0))
                        else:
                            data.extend(int_to_le(2))
                            data.extend(int_to_le(i))
                elif mode == 0x21:  # Get temperatures
                    data.extend([0x10, 0x00])
                    data.append(len(self.temperatures))
                    for i in self.temperatures:
                        if i is None:
                            data.append(1)
                            data.extend(int_to_le(0))
                        else:
                            data.append(0)
                            data.extend(int_to_le(int(i*10)))

        return list(data)[:length]

    def write(self, data):
        data = bytes(data)  # ensure data is convertible to bytes
        self._last_write = data

        if data[2] == 0x0d:
            channel = data[3]
            if self._modes[channel] is None:
                self._modes[channel] = data[4]
        elif data[2] == 0x05 and data[3] == 0x01:
            self._modes[data[4]] = None
        elif data[2] == 0x01 and data[3] == 0x03 and data[4] == 0x00:
            self._awake = data[5] == 0x02

        return len(data)


@pytest.fixture
def commander_core_device():
    device = MockCommanderCoreDevice()
    core = CommanderCore(device, 'Corsair Commander Core (experimental)')
    core.connect()
    return core


def test_initialize_commander_core(commander_core_device):
    commander_core_device.device.firmware_version = (0x01, 0x02, 0x21)
    commander_core_device.device.led_counts = (27, None, 1, 2, 4, 8, 16)
    commander_core_device.device.temperatures = (None, 45.6)
    res = commander_core_device.initialize()

    assert len(res) == 10

    assert res[0][1] == '1.2.33'  # Firmware

    # LED counts
    assert res[1][1] == 27
    assert res[2][1] is None
    assert res[3][1] == 1
    assert res[4][1] == 2
    assert res[5][1] == 4
    assert res[6][1] == 8
    assert res[7][1] == 16

    # Temperature sensors connected
    assert res[8][1] is False
    assert res[9][1] is True

    # Ensure device is asleep at end
    assert not commander_core_device.device._awake


def test_initialize_error_commander_core(commander_core_device):
    """This tests sends invalid data to ensure the device gets set back to hardware mode on error"""
    commander_core_device.device.response_prefix = (0x00, 0x00)

    with pytest.raises(ExpectationNotMet):
        commander_core_device.initialize()

    # Ensure device is asleep at end
    assert not commander_core_device.device._awake


def test_status_commander_core(commander_core_device):
    commander_core_device.device.speeds = (2357, 918, 903, 501, 1104, 1824, 104)
    commander_core_device.device.temperatures = (12.3, 45.6)
    res = commander_core_device.get_status()

    assert len(res) == 9

    # Speeds of pump and fans
    assert res[0][1] == 2357
    assert res[1][1] == 918
    assert res[2][1] == 903
    assert res[3][1] == 501
    assert res[4][1] == 1104
    assert res[5][1] == 1824
    assert res[6][1] == 104

    # Temperatures
    assert res[7][1] == 12.3
    assert res[8][1] == 45.6

    # Ensure device is asleep at end
    assert not commander_core_device.device._awake


def test_status_error_commander_core(commander_core_device):
    """This tests sends invalid data to ensure the device gets set back to hardware mode on error"""
    commander_core_device.device.response_prefix = (0x00, 0x00)

    with pytest.raises(ExpectationNotMet):
        commander_core_device.initialize()

    # Ensure device is asleep at end
    assert not commander_core_device.device._awake
