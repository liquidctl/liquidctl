import pytest
from collections import deque

from liquidctl import ExpectationNotMet
from liquidctl.driver.commander_core import CommanderCore
from _testutils import noop
from liquidctl.util import u16le_from


def int_to_le(num, length=2, byteorder='little', signed=False):
    return int(num).to_bytes(length=length, byteorder=byteorder, signed=signed)


class MockCommanderCoreDevice:
    def __init__(self):
        self.vendor_id = 0x1b1c
        self.product_id = 0x0c1c
        self.address = 'addr'
        self.path = b'path'
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
        self.speeds_mode = (0, 0, 0, 0, 0, 0, 0)
        self.speeds = (None, None, None, None, None, None, None)
        self.fixed_speeds = (0, 0, 0, 0, 0, 0, 0)
        self.temperatures = (None, None)
        self.curve_points_by_device = [[],[],[],[],[],[],[]]

    def read(self, length):
        data = bytearray([0x00, self._last_write[2], 0x00])
        data.extend(self.response_prefix)

        if self._last_write[2] == 0x02:  # Firmware version
            for i in range(0, 3):
                data.append(self.firmware_version[i])
        if self._awake:
            if self._last_write[2] == 0x08 or self._last_write[2] == 0x09:  # Get data
                channel = self._last_write[3]
                mode = self._modes.get(channel)
                if mode[1] == 0x00:
                    if mode[0] == 0x17:  # Get speeds
                        data.extend([0x06, 0x00])
                        data.append(len(self.speeds))
                        for i in self.speeds:
                            if i is None:
                                data.extend([0x00, 0x00])
                            else:
                                data.extend(int_to_le(i))
                    elif mode[0] == 0x1a:  # Speed devices connected
                        data.extend([0x09, 0x00])
                        data.append(len(self.speeds))
                        for i in self.speeds:
                            data.extend([0x01 if i is None else 0x07])
                    elif mode[0] == 0x20:  # LED detect
                        data.extend([0x0f, 0x00])
                        data.append(len(self.led_counts))
                        for i in self.led_counts:
                            if i is None:
                                data.extend(int_to_le(3)+int_to_le(0))
                            else:
                                data.extend(int_to_le(2))
                                data.extend(int_to_le(i))
                    elif mode[0] == 0x21:  # Get temperatures
                        data.extend([0x10, 0x00])
                        data.append(len(self.temperatures))
                        for i in self.temperatures:
                            if i is None:
                                data.append(1)
                                data.extend(int_to_le(0))
                            else:
                                data.append(0)
                                data.extend(int_to_le(int(i*10)))
                    else:
                        raise NotImplementedError(f'Read for {mode.hex(":")}')
                elif mode[1] == 0x6d:
                    if mode[0] == 0x60:
                        data.extend([0x03, 0x00])
                        data.append(len(self.speeds_mode))
                        for i in self.speeds_mode:
                            data.append(i)
                    elif mode[0] == 0x61:
                        data.extend([0x04, 0x00])
                        data.append(len(self.fixed_speeds))
                        for i in self.fixed_speeds:
                            data.extend(int_to_le(i))
                    elif mode[0] == 0x62:
                        data.extend([0x05, 0x00]) # data type
                        num_ports = len(self.curve_points_by_device)
                        data.append(num_ports)
                        for i in range(num_ports):
                            data.append(0) # temp sensor
                            data.append(len(self.curve_points_by_device[i])) # num curve points
                            for (temp, duty) in self.curve_points_by_device[i]:
                                data.extend(int_to_le(temp * 10)) # temperature
                                data.extend(int_to_le(duty)) # duty
                    else:
                        raise NotImplementedError(f'Read for {mode.hex(":")}')
                else:
                    raise NotImplementedError(f'Read for {mode.hex(":")}')
            elif self._last_write[2] == 0x09:  # Get more data
                channel = self._last_write[3]
                mode = self._modes.get(channel)
                if mode[1] == 0x6d:
                    if mode[0] == 0x62:
                        for i in range(3, 7):
                            data.append(0) # temp sensor
                            data.append(len(self.curve_points_by_device[i])) # num curve points
                            for (temp, duty) in self.curve_points_by_device[i]:
                                data.extend(int_to_le(temp * 10))
                                data.extend(int_to_le(duty))



        return list(data)[:length]

    def write(self, data):
        data = bytes(data)  # ensure data is convertible to bytes
        self._last_write = data
        if data[0] != 0x00 or data[1] != 0x08:
            raise ValueError('Start of packets going out should be 00:08')
        if data[2] == 0x0d:
            channel = data[3]
            if  self._modes.get(channel) is None:
                self._modes[channel] = data[4:6]
            else:
                raise ExpectationNotMet('Previous channel was not reset')
        elif data[2] == 0x05 and data[3] == 0x01:
            self._modes[data[4]] = None
        elif data[2] == 0x01 and data[3] == 0x03 and data[4] == 0x00:
            self._awake = data[5] == 0x02
        elif self._awake:
            channel = data[3]
            mode = self._modes.get(channel)

            if data[2] == 0x06:  # Write command
                self.data_length = u16le_from(data[4:6])
                self.written_data_type = data[8:10]
                self.written_data = data[10:8+self.data_length]
                if len(self.written_data) < self.data_length - 2:
                    return
            if data[2] == 0x07: # Write More command
                self.written_data += data[4:]
                if len(self.written_data) < self.data_length - 2:
                    return

            if data[2] == 0x06 or data[2] == 0x07:
                if mode[1] == 0x6d:
                    if mode[0] == 0x60 and list(self.written_data_type) == [0x03, 0x00]:
                        self.speeds_mode = tuple(self.written_data[i+1] for i in range(0, self.written_data[0]))
                    elif mode[0] == 0x61 and list(self.written_data_type) == [0x04, 0x00]:
                        self.fixed_speeds = tuple(u16le_from(self.written_data[i*2+1:i*2+3]) for i in range(0, self.written_data[0]))
                    elif mode[0] == 0x62 and list(self.written_data_type) == [0x05, 0x00]:
                        curve_index = 1
                        for port_index in range(0, self.written_data[0]):
                            self.curve_points_by_device[port_index] = []
                            # get number of curve points
                            num_points = self.written_data[curve_index + 1]

                            # store temperature and duty
                            for i in range(num_points):
                                point_index = curve_index + 2 + i*4
                                cp_temp = u16le_from(self.written_data[point_index: point_index + 2]) / 10
                                cp_duty = u16le_from(self.written_data[point_index + 2: point_index + 4])
                                self.curve_points_by_device[port_index].append((cp_temp, cp_duty))

                            # update index to next curve
                            curve_index += 4 * num_points + 2
                    else:
                        raise NotImplementedError('Invalid Write command')
                else:
                    raise NotImplementedError('Invalid Write command')

        return len(data)



@pytest.fixture
def commander_core_device():
    device = MockCommanderCoreDevice()
    core = CommanderCore(device, 'Corsair Commander Core', True)
    core.connect()
    return core


def test_initialize_commander_core(commander_core_device):
    commander_core_device.device.firmware_version = (0x01, 0x02, 0x21)
    commander_core_device.device.speeds = (None, 104, None, None, None, None, 918)
    commander_core_device.device.led_counts = (27, None, 1, 2, 4, 8, 16)
    commander_core_device.device.temperatures = (None, 45.6)
    res = commander_core_device.initialize()

    assert len(res) == 17

    assert res[0][1] == '1.2.33'  # Firmware

    # LED counts
    assert res[1][1] == 27
    assert res[2][1] is None
    assert res[3][1] == 1
    assert res[4][1] == 2
    assert res[5][1] == 4
    assert res[6][1] == 8
    assert res[7][1] == 16

    # Speed devices connected
    assert not res[8][1]
    assert res[9][1]
    assert not res[10][1]
    assert not res[11][1]
    assert not res[12][1]
    assert not res[13][1]
    assert res[14][1]

    # Temperature sensors connected
    assert not res[15][1]
    assert res[16][1]

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


def test_set_fixed_speed_fan2_commander_core(commander_core_device):
    """This tests setting the speed of a single channel"""
    commander_core_device.device.speeds_mode = (1, 2, 3, 4, 5, 6, 7)
    commander_core_device.device.fixed_speeds = (8, 9, 10, 11, 12, 13, 14)

    commander_core_device.set_fixed_speed('fan2', 95)

    assert commander_core_device.device.speeds_mode == (1, 2, 0, 4, 5, 6, 7)
    assert commander_core_device.device.fixed_speeds == (8, 9, 95, 11, 12, 13, 14)
    # Ensure device is asleep at end
    assert not commander_core_device.device._awake


def test_set_fixed_speed_fans_commander_core(commander_core_device):
    """This tests setting the speed of all the fans"""
    commander_core_device.device.speeds_mode = (1, 2, 3, 4, 5, 6, 7)
    commander_core_device.device.fixed_speeds = (8, 9, 10, 11, 12, 13, 14)

    commander_core_device.set_fixed_speed('fans', 61)

    assert commander_core_device.device.speeds_mode == (1, 0, 0, 0, 0, 0, 0)
    assert commander_core_device.device.fixed_speeds == (8, 61, 61, 61, 61, 61, 61)
    # Ensure device is asleep at end
    assert not commander_core_device.device._awake


def test_set_fixed_speed_error_commander_core(commander_core_device):
    """This tests sends invalid data to ensure the device gets set back to hardware mode on error"""
    commander_core_device.device.response_prefix = (0x00, 0x00)

    with pytest.raises(ExpectationNotMet):
        commander_core_device.set_fixed_speed('fan1', 95)

    # Ensure device is asleep at end
    assert not commander_core_device.device._awake


def test_set_speed_profile_fans_commander_core(commander_core_device):
    """This tests setting the speed of all the fans"""
    commander_core_device.device.speeds_mode = (0, 0, 0, 0, 0, 0, 0)
    commander_core_device.device.fixed_speeds = (8, 9, 10, 11, 12, 13, 14)

    commander_core_device.set_speed_profile('fans', [
        (22, 0), (32, 25), (34, 50), (36, 75), (38,85), (40,95), (42, 100)
    ])

    assert commander_core_device.device.speeds_mode == (0, 2, 2, 2, 2, 2, 2)
    assert commander_core_device.device.curve_points_by_device[0] == []
    assert commander_core_device.device.curve_points_by_device[1] == [(22, 0), (32, 25), (34, 50), (36, 75), (38, 85), (40, 95), (42, 100)]
    assert commander_core_device.device.curve_points_by_device[2] == [(22, 0), (32, 25), (34, 50), (36, 75), (38, 85), (40, 95), (42, 100)]
    assert commander_core_device.device.curve_points_by_device[3] == [(22, 0), (32, 25), (34, 50), (36, 75), (38, 85), (40, 95), (42, 100)]
    assert commander_core_device.device.curve_points_by_device[4] == [(22, 0), (32, 25), (34, 50), (36, 75), (38, 85), (40, 95), (42, 100)]
    assert commander_core_device.device.curve_points_by_device[5] == [(22, 0), (32, 25), (34, 50), (36, 75), (38, 85), (40, 95), (42, 100)]
    assert commander_core_device.device.curve_points_by_device[6] == [(22, 0), (32, 25), (34, 50), (36, 75), (38, 85), (40, 95), (42, 100)]

    # Ensure device is asleep at end
    assert not commander_core_device.device._awake

def test_set_speed_curve_profile_single_channel_commander_core(commander_core_device):
    """This tests setting the speed curve profile of a single fan"""
    commander_core_device.device.speeds_mode = (0, 0, 0, 0, 0, 0, 0)
    commander_core_device.device.fixed_speeds = (8, 9, 10, 11, 12, 13, 14)
    commander_core_device.device.curve_points_by_device[0] = []
    commander_core_device.device.curve_points_by_device[1] = []
    commander_core_device.device.curve_points_by_device[2] = []
    commander_core_device.device.curve_points_by_device[3] = []
    commander_core_device.device.curve_points_by_device[4] = []
    commander_core_device.device.curve_points_by_device[5] = []
    commander_core_device.device.curve_points_by_device[6] = []

    commander_core_device.set_speed_profile('pump', [(22, 0), (42, 100)])
    commander_core_device.set_speed_profile('fan1', [(22, 1), (42, 10)])
    commander_core_device.set_speed_profile('fan2', [(22, 2), (42, 20)])
    commander_core_device.set_speed_profile('fan3', [(22, 3), (42, 30)])
    commander_core_device.set_speed_profile('fan4', [(22, 4), (42, 40)])
    commander_core_device.set_speed_profile('fan5', [(22, 5), (42, 50)])
    commander_core_device.set_speed_profile('fan6', [(22, 6), (42, 60)])

    assert commander_core_device.device.speeds_mode == (2, 2, 2, 2, 2, 2, 2)
    assert commander_core_device.device.curve_points_by_device[0] == [(22, 0), (42, 100)]
    assert commander_core_device.device.curve_points_by_device[1] == [(22, 1), (42, 10)]
    assert commander_core_device.device.curve_points_by_device[2] == [(22, 2), (42, 20)]
    assert commander_core_device.device.curve_points_by_device[3] == [(22, 3), (42, 30)]
    assert commander_core_device.device.curve_points_by_device[4] == [(22, 4), (42, 40)]
    assert commander_core_device.device.curve_points_by_device[5] == [(22, 5), (42, 50)]
    assert commander_core_device.device.curve_points_by_device[6] == [(22, 6), (42, 60)]

    # Ensure device is asleep at end
    assert not commander_core_device.device._awake


def test_parse_channels_commander_core():
    """This test will go through and thoroughly test CommanderCore._parse_channels so we don't have to in other tests"""
    core = CommanderCore(MockCommanderCoreDevice(), 'Corsair Commander Core', True)
    tests = [
        ('pump', [0]), ('fans', [1, 2, 3, 4, 5, 6]),
        ('fan1', [1]), ('fan2', [2]), ('fan3', [3]), ('fan4', [4]), ('fan5', [5]), ('fan6', [6])
    ]

    for (val, answer) in tests:
        assert list(core._parse_channels(val)) == answer



def test_parse_channels_commander_core_xt():
    """Test Core XT-specific channel layout"""
    corext = CommanderCore(MockCommanderCoreDevice(), 'Corsair Commander Core', False)
    tests = [
        ('fans', [0, 1, 2, 3, 4, 5]),
        ('fan1', [0]), ('fan2', [1]), ('fan3', [2]), ('fan4', [3]), ('fan5', [4]), ('fan6', [5])
    ]

    for (val, answer) in tests:
        assert list(corext._parse_channels(val)) == answer


def test_parse_channels_error_commander_core():
    """This tests to make sure we get an error with an invalid channel"""
    core = CommanderCore(MockCommanderCoreDevice(), 'Corsair Commander Core', True)
    with pytest.raises(ValueError):
        core._parse_channels('fan')
