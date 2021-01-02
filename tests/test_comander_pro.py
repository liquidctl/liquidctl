import pytest

from liquidctl.driver.commander_pro import _quoted, _prepare_profile, _get_fan_mode_description, CommanderPro
from liquidctl.error import NotSupportedByDevice

from _testutils import MockHidapiDevice, Report, MockRuntimeStorage

# hardcoded responce data expected for some of the calls:
# commander pro: firmware request (0.9.214)
# commander pro: bootloader req (2.3)
# commander pro: get temp config ( 3 sensors)
# commander pro: get fan configs (3 DC fans, 1 PWM fan) # note I have not tested it with pwm fans
# commander pro:


@pytest.fixture
def commanderProDeviceUnconnected():
    device = MockHidapiDevice(vendor_id=0x1b1c, product_id=0x0c10, address='addr')
    return CommanderPro(device, 'Corsair Commander Pro (experimental)', 6, 4, 2)


@pytest.fixture
def lightingNodeProDeviceUnconnected():
    device = MockHidapiDevice(vendor_id=0x1b1c, product_id=0x0c0b, address='addr')
    return CommanderPro(device, 'Corsair Lighting Node Pro (experimental)', 0, 0, 2)


@pytest.fixture
def commanderProDevice():
    device = MockHidapiDevice(vendor_id=0x1b1c, product_id=0x0c10, address='addr')
    pro = CommanderPro(device, 'Corsair Commander Pro (experimental)', 6, 4, 2)
    pro.connect()
    pro._data = MockRuntimeStorage(key_prefixes='testing')
    return pro


@pytest.fixture
def lightingNodeProDevice():
    device = MockHidapiDevice(vendor_id=0x1b1c, product_id=0x0c0b, address='addr')
    node = CommanderPro(device, 'Corsair Lighting Node Pro (experimental)', 0, 0, 2)
    node.connect()
    node._data = MockRuntimeStorage(key_prefixes='testing')
    return node


# prepare profile
def test_prepare_profile_valid_max_rpm():
    assert _prepare_profile([[10, 400], [20, 5000]], 60) == [(10, 400), (20, 5000), (60, 5000), (60, 5000), (60, 5000), (60, 5000)]


def test_prepare_profile_add_max_rpm():
    assert _prepare_profile([[10, 400]], 60) == [(10, 400), (60, 5000), (60, 5000), (60, 5000), (60, 5000), (60, 5000)]
    assert _prepare_profile([[10, 400], [20, 500], [30, 600], [40, 700], [50, 800]], 60) == [(10, 400), (20, 500), (30, 600), (40, 700), (50, 800), (60, 5000)]


def test_prepare_profile_missing_max_rpm():
    with pytest.raises(ValueError):
        _prepare_profile([[10, 400], [20, 500], [30, 600], [40, 700], [50, 800], [55, 900]], 60)


def test_prepare_profile_full_set():
    assert _prepare_profile([[10, 400], [20, 500], [30, 600], [40, 700], [45, 2000], [50, 5000]], 60) == [(10, 400), (20, 500), (30, 600), (40, 700), (45, 2000), (50, 5000)]


def test_prepare_profile_too_many_points():
    with pytest.raises(ValueError):
        _prepare_profile([[10, 400], [20, 500], [30, 600], [40, 700], [50, 800], [55, 900]], 60)


def test_prepare_profile_no_points():
    assert _prepare_profile([], 60) == [(60, 5000), (60, 5000), (60, 5000), (60, 5000), (60, 5000), (60, 5000)]


def test_prepare_profile_empty_list():
    assert _prepare_profile([], 60) == [(60, 5000), (60, 5000), (60, 5000), (60, 5000), (60, 5000), (60, 5000)]


def test_prepare_profile_above_max_temp():
    assert _prepare_profile([[10, 400], [70, 2000]], 60) == [(10, 400), (60, 5000), (60, 5000), (60, 5000), (60, 5000), (60, 5000)]


def test_prepare_profile_temp_low():
    assert _prepare_profile([[-10, 400], [70, 2000]], 60) == [(-10, 400), (60, 5000), (60, 5000), (60, 5000), (60, 5000), (60, 5000)]


def test_prepare_profile_max_temp():
    assert _prepare_profile([], 100) == [(100, 5000), (100, 5000), (100, 5000), (100, 5000), (100, 5000), (100, 5000)]


# quoted
def test_quoted_empty():
    assert _quoted() == ''


def test_quoted_single():
    assert _quoted('one arg') == "'one arg'"


def test_quoted_valid():
    assert _quoted('one', 'two') == "'one', 'two'"


def test_quoted_not_string():
    assert _quoted('test', 500) == "'test', 500"


# fan modes
def test_get_fan_mode_description_auto():
    assert _get_fan_mode_description(0x00) == 'Auto/Disconnected'


def test_get_fan_mode_description_unknown():
    assert _get_fan_mode_description(0x03) == 'UNKNOWN'
    assert _get_fan_mode_description(0x04) == 'UNKNOWN'
    assert _get_fan_mode_description(0x10) == 'UNKNOWN'
    assert _get_fan_mode_description(0xff) == 'UNKNOWN'


def test_get_fan_mode_description_dc():
    assert _get_fan_mode_description(0x01) == 'DC'


def test_get_fan_mode_description_pwm():
    assert _get_fan_mode_description(0x02) == 'PWM'


# class methods
def test_commander_constructor(commanderProDeviceUnconnected):

    assert commanderProDeviceUnconnected._data is None
    assert commanderProDeviceUnconnected._fan_names == ['fan1', 'fan2', 'fan3', 'fan4', 'fan5', 'fan6']
    assert commanderProDeviceUnconnected._led_names == ['led1', 'led2']
    assert commanderProDeviceUnconnected._temp_probs == 4
    assert commanderProDeviceUnconnected._fan_count == 6


def test_lighting_constructor(lightingNodeProDeviceUnconnected):
    assert lightingNodeProDeviceUnconnected._data is None
    assert lightingNodeProDeviceUnconnected._fan_names == []
    assert lightingNodeProDeviceUnconnected._led_names == ['led1', 'led2']
    assert lightingNodeProDeviceUnconnected._temp_probs == 0
    assert lightingNodeProDeviceUnconnected._fan_count == 0


def test_connect_commander(commanderProDeviceUnconnected):
    commanderProDeviceUnconnected.connect()
    assert commanderProDeviceUnconnected._data is not None


def test_connect_lighting(lightingNodeProDeviceUnconnected):
    lightingNodeProDeviceUnconnected.connect()
    assert lightingNodeProDeviceUnconnected._data is not None


def test_initialize_commander_pro(commanderProDevice):

    responses = [
        '000009d4000000000000000000000000',  # firmware
        '00000500000000000000000000000000',  # bootloader
        '00010100010000000000000000000000',  # temp probes
        '00010102000000000000000000000000'   # fan probes
    ]
    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    res = commanderProDevice.initialize()

    assert len(res) == 12
    assert res[0][1] == '0.9.212'
    assert res[1][1] == '0.5'

    assert res[2][1] == 'Connected'
    assert res[3][1] == 'Connected'
    assert res[4][1] == 'Not Connected'
    assert res[5][1] == 'Connected'

    assert res[6][1] == 'DC'
    assert res[7][1] == 'DC'
    assert res[8][1] == 'PWM'
    assert res[9][1] == 'Auto/Disconnected'
    assert res[10][1] == 'Auto/Disconnected'
    assert res[11][1] == 'Auto/Disconnected'

    data = commanderProDevice._data.load('fan_modes', None)
    assert data is not None
    assert len(data) == 6
    assert data[0] == 0x01
    assert data[1] == 0x01
    assert data[2] == 0x02
    assert data[3] == 0x00
    assert data[4] == 0x00
    assert data[5] == 0x00

    data = commanderProDevice._data.load('temp_sensors_connected', None)
    assert data is not None
    assert len(data) == 4
    assert data[0] == 0x01
    assert data[1] == 0x01
    assert data[2] == 0x00
    assert data[3] == 0x01


def test_initialize_lighting_node(lightingNodeProDevice):
    responses = [
        '000009d4000000000000000000000000',  # firmware
        '00000500000000000000000000000000'  # bootloader
    ]
    for d in responses:
        lightingNodeProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    res = lightingNodeProDevice.initialize()

    assert len(res) == 2
    assert res[0][1] == '0.9.212'
    assert res[1][1] == '0.5'

    data = lightingNodeProDevice._data.load('fan_modes', None)
    assert data is None

    data = lightingNodeProDevice._data.load('temp_sensors_connected', None)
    assert data is None


def test_get_status_commander_pro(commanderProDevice):

    responses = [
        '000a8300000000000000000000000000',  # temp sensor 1
        '000b6a00000000000000000000000000',  # temp sensor 2
        '000a0e00000000000000000000000000',  # temp sensor 4
        '002f2200000000000000000000000000',  # get 12v
        '00136500000000000000000000000000',  # get 5v
        '000d1f00000000000000000000000000',  # get 3.3v
        '0003ac00000000000000000000000000',  # fan speed 1
        '0003ab00000000000000000000000000',  # fan speed 2
        '0003db00000000000000000000000000'  # fan speed 3
    ]
    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._data.store('fan_modes', [0x01, 0x01, 0x02, 0x00, 0x00, 0x00])
    commanderProDevice._data.store('temp_sensors_connected', [0x01, 0x01, 0x00, 0x01])

    res = commanderProDevice.get_status()

    assert len(res) == 13

    # voltages
    assert res[0][1] == 12.066   # 12v
    assert res[1][1] == 4.965    # 5v
    assert res[2][1] == 3.359    # 3.3v

    # temp probes
    assert res[3][1] == 26.91
    assert res[4][1] == 29.22
    assert res[5][1] == 0.0
    assert res[6][1] == 25.74

    # fans rpm
    assert res[7][1] == 940
    assert res[8][1] == 939
    assert res[9][1] == 987
    assert res[10][1] == 0
    assert res[11][1] == 0
    assert res[12][1] == 0

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 9

    assert sent[0].data[0] == 0x11
    assert sent[1].data[0] == 0x11
    assert sent[2].data[0] == 0x11

    assert sent[3].data[0] == 0x12
    assert sent[4].data[0] == 0x12
    assert sent[5].data[0] == 0x12

    assert sent[6].data[0] == 0x21
    assert sent[7].data[0] == 0x21
    assert sent[8].data[0] == 0x21


def test_get_status_lighting_pro(lightingNodeProDevice):

    res = lightingNodeProDevice.get_status()
    assert len(res) == 0


def test_get_temp_valid_sensor_commander(commanderProDevice):

    response = '000a8300000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))

    commanderProDevice._data.store('temp_sensors_connected', [0x01, 0x01, 0x01, 0x01])

    res = commanderProDevice._get_temp(1)

    assert res == 26.91

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1
    assert sent[0].data[0] == 0x11
    assert sent[0].data[1] == 1


def test_get_temp_invalid_sensor_low_commander(commanderProDevice):
    response = '000a8300000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))

    commanderProDevice._data.store('temp_sensors_connected', [0x01, 0x01, 0x01, 0x01])

    with pytest.raises(ValueError):
        commanderProDevice._get_temp(-1)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0


def test_get_temp_invalid_sensor_high_commander(commanderProDevice):
    response = '000a8300000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))

    commanderProDevice._data.store('temp_sensors_connected', [0x01, 0x01, 0x01, 0x01])

    with pytest.raises(ValueError):
        commanderProDevice._get_temp(4)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0


def test_get_temp_lighting(lightingNodeProDevice):
    response = '000a8300000000000000000000000000'
    lightingNodeProDevice.device.preload_read(Report(0, bytes.fromhex(response)))

    lightingNodeProDevice._data.store('temp_sensors_connected', [0x00, 0x00, 0x00, 0x00])

    with pytest.raises(ValueError):
        lightingNodeProDevice._get_temp(2)

    # check the commands sent
    sent = lightingNodeProDevice.device.sent
    assert len(sent) == 0


def test_get_fan_rpm_valid_commander(commanderProDevice):

    response = '0003ac00000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))
    commanderProDevice._data.store('fan_modes', [0x01, 0x01, 0x02, 0x00, 0x00, 0x00])

    res = commanderProDevice._get_fan_rpm(1)
    assert res == 940

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1
    assert sent[0].data[0] == 0x21
    assert sent[0].data[1] == 1


def test_get_fan_rpm_invalid_low_commander(commanderProDevice):

    response = '0003ac00000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))

    commanderProDevice._data.store('fan_modes', [0x01, 0x01, 0x02, 0x00, 0x00, 0x00])

    with pytest.raises(ValueError):
        commanderProDevice._get_fan_rpm(-1)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0


def test_get_fan_rpm_invalid_high_commander(commanderProDevice):
    response = '0003ac00000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))

    commanderProDevice._data.store('fan_modes', [0x01, 0x01, 0x02, 0x00, 0x00, 0x00])

    with pytest.raises(ValueError):
        commanderProDevice._get_fan_rpm(7)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0


def test_get_fan_rpm_lighting(lightingNodeProDevice):
    response = '0003ac00000000000000000000000000'
    lightingNodeProDevice.device.preload_read(Report(0, bytes.fromhex(response)))

    with pytest.raises(ValueError):
        lightingNodeProDevice._get_fan_rpm(7)

    # check the commands sent
    sent = lightingNodeProDevice.device.sent
    assert len(sent) == 0


def test_get_hw_fan_channels_all(commanderProDevice):

    res = commanderProDevice._get_hw_fan_channels('sync')
    assert res == [0, 1, 2, 3, 4, 5]


def test_get_hw_fan_channels_uppercase(commanderProDevice):
    res = commanderProDevice._get_hw_fan_channels('FaN3')
    assert res == [2]


def test_get_hw_fan_channels_lowercase(commanderProDevice):
    res = commanderProDevice._get_hw_fan_channels('fan2')
    assert res == [1]


def test_get_hw_fan_channels_invalid(commanderProDevice):
    with pytest.raises(ValueError):
        commanderProDevice._get_hw_fan_channels('fan23')

    with pytest.raises(ValueError):
        commanderProDevice._get_hw_fan_channels('fan7')

    with pytest.raises(ValueError):
        commanderProDevice._get_hw_fan_channels('fan0')

    with pytest.raises(ValueError):
        commanderProDevice._get_hw_fan_channels('bob')


def test_get_hw_led_channels_all(commanderProDevice):

    res = commanderProDevice._get_hw_led_channels('led')
    assert res == [0, 1]


def test_get_hw_led_channels_uppercase(commanderProDevice):
    res = commanderProDevice._get_hw_led_channels('LeD2')
    assert res == [1]


def test_get_hw_led_channels_lowercase(commanderProDevice):
    res = commanderProDevice._get_hw_led_channels('led1')
    assert res == [0]


def test_get_hw_led_channels_invalid(commanderProDevice):
    with pytest.raises(ValueError):
        commanderProDevice._get_hw_led_channels('led0')

    with pytest.raises(ValueError):
        commanderProDevice._get_hw_led_channels('led3')

    with pytest.raises(ValueError):
        commanderProDevice._get_hw_led_channels('bob')


def test_set_fixed_speed_low(commanderProDevice):

    response = '00000000000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))
    commanderProDevice._data.store('fan_modes', [0x01, 0x01, 0x01, 0x01, 0x01, 0x01])

    commanderProDevice.set_fixed_speed('fan4', -10)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1

    assert sent[0].data[0] == 0x23
    assert sent[0].data[1] == 0x03
    assert sent[0].data[2] == 0x00


def test_set_fixed_speed_high(commanderProDevice):
    response = '00000000000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))
    commanderProDevice._data.store('fan_modes', [0x01, 0x01, 0x01, 0x01, 0x01, 0x01])

    commanderProDevice.set_fixed_speed('fan3', 110)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1

    assert sent[0].data[0] == 0x23
    assert sent[0].data[1] == 0x02
    assert sent[0].data[2] == 0x64


def test_set_fixed_speed_valid(commanderProDevice):

    response = '00000000000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))
    commanderProDevice._data.store('fan_modes', [0x01, 0x01, 0x01, 0x01, 0x01, 0x01])

    commanderProDevice.set_fixed_speed('fan2', 50)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1

    assert sent[0].data[0] == 0x23
    assert sent[0].data[1] == 0x01
    assert sent[0].data[2] == 0x32


def test_set_fixed_speed_valid_unconfigured(commanderProDevice):

    response = '00000000000000000000000000000000'
    commanderProDevice.device.preload_read(Report(0, bytes.fromhex(response)))
    commanderProDevice._data.store('fan_modes', [0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    commanderProDevice.set_fixed_speed('fan2', 50)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0


def test_set_fixed_speed_valid_multi_fan(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._data.store('fan_modes', [0x01, 0x00, 0x01, 0x01, 0x00, 0x00])

    commanderProDevice.set_fixed_speed('sync', 50)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 3

    assert sent[0].data[0] == 0x23
    assert sent[0].data[1] == 0x00
    assert sent[0].data[2] == 0x32

    assert sent[1].data[0] == 0x23
    assert sent[1].data[1] == 0x02
    assert sent[1].data[2] == 0x32

    assert sent[2].data[0] == 0x23
    assert sent[2].data[1] == 0x03
    assert sent[2].data[2] == 0x32


def test_set_fixed_speed_lighting(lightingNodeProDevice):
    response = '00000000000000000000000000000000'
    lightingNodeProDevice.device.preload_read(Report(0, bytes.fromhex(response)))

    with pytest.raises(NotSupportedByDevice):
        lightingNodeProDevice.set_fixed_speed('sync', 50)

    # check the commands sent
    sent = lightingNodeProDevice.device.sent
    assert len(sent) == 0


def test_set_speed_profile_valid_multi_fan(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._data.store('temp_sensors_connected', [0x01, 0x01, 0x00, 0x01])
    commanderProDevice._data.store('fan_modes', [0x01, 0x00, 0x01, 0x01, 0x00, 0x00])
    commanderProDevice.set_speed_profile('sync', [(10, 500), (20, 1000)])

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 3

    assert sent[0].data[0] == 0x25
    assert sent[0].data[1] == 0x00
    assert sent[0].data[2] == 0x00

    assert sent[0].data[3] == 0x03
    assert sent[0].data[4] == 0xe8
    assert sent[0].data[15] == 0x01
    assert sent[0].data[16] == 0xf4

    assert sent[1].data[0] == 0x25
    assert sent[1].data[1] == 0x02
    assert sent[1].data[2] == 0x00

    assert sent[2].data[0] == 0x25
    assert sent[2].data[1] == 0x03
    assert sent[2].data[2] == 0x00


def test_set_speed_profile_invalid_temp_sensor(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._data.store('temp_sensors_connected', [0x01, 0x01, 0x00, 0x01])
    commanderProDevice._data.store('fan_modes', [0x01, 0x00, 0x01, 0x01, 0x00, 0x00])

    commanderProDevice.set_speed_profile('fan1', [(10, 500), (20, 1000)], temperature_sensor=10)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1

    assert sent[0].data[0] == 0x25
    assert sent[0].data[1] == 0x00
    assert sent[0].data[2] == 0x03

    assert sent[0].data[3] == 0x03
    assert sent[0].data[4] == 0xe8
    assert sent[0].data[15] == 0x01
    assert sent[0].data[16] == 0xf4


def test_set_speed_profile_no_temp_sensors(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._data.store('temp_sensors_connected', [0x00, 0x00, 0x00, 0x00])
    commanderProDevice._data.store('fan_modes', [0x01, 0x00, 0x01, 0x01, 0x00, 0x00])

    with pytest.raises(ValueError):
        commanderProDevice.set_speed_profile('sync', [(10, 500), (20, 1000)], temperature_sensor=1)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0


def test_set_speed_profile_valid(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._data.store('temp_sensors_connected', [0x01, 0x01, 0x00, 0x01])
    commanderProDevice._data.store('fan_modes', [0x01, 0x00, 0x01, 0x01, 0x00, 0x00])
    commanderProDevice.set_speed_profile('fan3', [(10, 500), (20, 1000)])

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1

    assert sent[0].data[0] == 0x25
    assert sent[0].data[1] == 0x02
    assert sent[0].data[2] == 0x00

    assert sent[0].data[3] == 0x03
    assert sent[0].data[4] == 0xe8
    assert sent[0].data[15] == 0x01
    assert sent[0].data[16] == 0xf4


def test_set_speed_profile_lighting(lightingNodeProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        lightingNodeProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    lightingNodeProDevice._data.store('temp_sensors_connected', [0x01, 0x00, 0x00, 0x00])
    lightingNodeProDevice._data.store('fan_modes', [0x01, 0x00, 0x01, 0x01, 0x00, 0x00])

    with pytest.raises(NotSupportedByDevice):
        lightingNodeProDevice.set_speed_profile('sync', [(10, 500), (20, 1000)])

    # check the commands sent
    sent = lightingNodeProDevice.device.sent
    assert len(sent) == 0


def test_set_speed_profile_valid_unconfigured(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._data.store('temp_sensors_connected', [0x00, 0x00, 0x00, 0x00])
    commanderProDevice._data.store('fan_modes', [0x01, 0x00, 0x01, 0x01, 0x00, 0x00])

    with pytest.raises(ValueError):
        commanderProDevice.set_speed_profile('fan2', [(10, 500), (20, 1000)])

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0


def test_set_color_hardware_clear(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    effect = {
            'channel': 0x01,
            'start_led': 0x00,
            'num_leds': 0x0f,
            'mode': 0x0a,
            'speed': 0x00,
            'direction': 0x00,
            'random_colors': 0x00,
            'colors': []
        }
    commanderProDevice._data.store('saved_effects', [effect])

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    commanderProDevice.set_color('led1', 'clear', [], )

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is None


def test_set_color_hardware_off(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    effect = {
            'channel': 0x01,
            'start_led': 0x00,
            'num_leds': 0x0f,
            'mode': 0x0a,
            'speed': 0x00,
            'direction': 0x00,
            'random_colors': 0x00,
            'colors': []
        }
    commanderProDevice._data.store('saved_effects', [effect])

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    commanderProDevice.set_color('led1', 'off', [])

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[4] == 0x04

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is None


@pytest.mark.parametrize('directionStr,expected', [
    ('forward', 0x01), ('FORWARD', 0x01), ('fOrWaRd', 0x01),
    ('backward', 0x00), ('BACKWARD', 0x00), ('BaCkWaRd', 0x00)
    ])
def test_set_color_hardware_dirrection(commanderProDevice, directionStr, expected):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors, direction=directionStr)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[6] == expected

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_direction_default(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[6] == 0x01

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_speed_default(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[5] == 0x01

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


@pytest.mark.parametrize('speedStr,expected', [
    ('slow', 0x02), ('SLOW', 0x02), ('SlOw', 0x02),
    ('fast', 0x00), ('FAST', 0x00), ('fAsT', 0x00),
    ('medium', 0x01), ('MEDIUM', 0x01), ('MeDiUm', 0x01)
    ])
def test_set_color_hardware_speed(commanderProDevice, speedStr, expected):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors, speed=speedStr)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[5] == expected

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_default_start_end(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[2] == 0x00  # start led
    assert sent[3].data[3] == 0x01  # num leds

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


@pytest.mark.parametrize('startLED,expected', [
    (1, 0x00), (30, 0x1d), (92, 0x5b)
    ])
def test_set_color_hardware_start_set(commanderProDevice, startLED, expected):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors, start_led=startLED)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[2] == expected  # start led

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


@pytest.mark.parametrize('numLED,expected', [
    (1, 0x01), (30, 0x1e), (96, 0x5f)
    ])
def test_set_color_hardware_num_leds(commanderProDevice, numLED, expected):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors, start_led=1, maximum_leds=numLED)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[3] == expected  # num leds

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_too_many_leds(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors, start_led=50, maximum_leds=50)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[2] == 0x31  # start led
    assert sent[3].data[3] == 0x2e  # num led

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_too_few_leds(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors, start_led=1, maximum_leds=0)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[2] == 0x00  # start led
    assert sent[3].data[3] == 0x01  # num led

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


@pytest.mark.parametrize('channel,expected', [
    ('led1', 0x00), ('led', 0x00), ('LeD1', 0x00),
    ('led2', 0x01), ('LED2', 0x01), ('LeD2', 0x01)
    ])
def test_set_color_hardware_channel(commanderProDevice, channel, expected):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color(channel, 'fixed', colors)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[0].data[1] == expected
    assert sent[1].data[1] == expected
    assert sent[2].data[1] == expected
    assert sent[3].data[0] == 0x35
    assert sent[3].data[1] == expected

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_random_color(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = []
    commanderProDevice.set_color('led1', 'fixed', colors)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[7] == 0x01

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_not_random_color(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]
    commanderProDevice.set_color('led1', 'fixed', colors)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[7] == 0x00

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_too_many_colors(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc], [0x00, 0x11, 0x22], [0x33, 0x44, 0x55]]
    commanderProDevice.set_color('led1', 'fixed', colors)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[7] == 0x00

    assert sent[3].data[9] == 0xaa
    assert sent[3].data[10] == 0xbb
    assert sent[3].data[11] == 0xcc

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_too_few_colors(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    commanderProDevice.set_color('led1', 'fixed', [])

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[7] == 0x01

    assert sent[3].data[9] == 0x00
    assert sent[3].data[10] == 0x00
    assert sent[3].data[11] == 0x00

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


@pytest.mark.parametrize('modeStr,expected', [
    ('rainbow', 0x00), ('color_shift', 0x01), ('color_pulse', 0x02),
    ('color_wave', 0x03), ('fixed', 0x04), ('visor', 0x06), ('marquee', 0x07), ('blink', 0x08),
    ('sequential', 0x09), ('sEqUeNtIaL', 0x09), ('rainbow2', 0x0a)
    ])
def test_set_color_hardware_valid_mode(commanderProDevice, modeStr, expected):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    commanderProDevice.set_color('led1', modeStr, [])

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 5

    assert sent[3].data[0] == 0x35
    assert sent[3].data[4] == expected

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 1


def test_set_color_hardware_invalid_mode(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))
    colors = [[0xaa, 0xbb, 0xcc]]

    with pytest.raises(ValueError):
        commanderProDevice.set_color('led1', 'invalid', colors)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 0

    effects = commanderProDevice._data.load('saved_effects', default=None)
    assert effects is None


def test_set_color_hardware_multipe_commands(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    effect = {
            'channel': 0x01,
            'start_led': 0x00,
            'num_leds': 0x0f,
            'mode': 0x0a,
            'speed': 0x00,
            'direction': 0x00,
            'random_colors': 0x00,
            'colors': [0xaa, 0xbb, 0xcc]
        }
    commanderProDevice._data.store('saved_effects', [effect])

    commanderProDevice.set_color('led1', 'fixed', [[0x00, 0x11, 0x22]], start_led=16, maximum_leds=5)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 6

    assert sent[3].data[0] == 0x35
    assert sent[4].data[0] == 0x35

    effects = commanderProDevice._data.load('saved_effects', default=None)

    assert effects is not None
    assert len(effects) == 2


def test_send_command_valid_data(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._send_command(6, [255, 0, 20, 10, 15])

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1
    assert len(sent[0].data) == 64
    assert sent[0].data[0] == 6
    assert sent[0].data[1] == 255


def test_send_command_no_data(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    commanderProDevice._send_command(6)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1
    assert len(sent[0].data) == 64
    assert sent[0].data[0] == 6
    assert sent[0].data[1] == 0


def test_send_command_data_too_long(commanderProDevice):
    responses = [
        '00000000000000000000000000000000',
        '00000000000000000000000000000000'
    ]

    for d in responses:
        commanderProDevice.device.preload_read(Report(0, bytes.fromhex(d)))

    data = bytearray(100)
    commanderProDevice._send_command(3, data)

    # check the commands sent
    sent = commanderProDevice.device.sent
    assert len(sent) == 1
    assert len(sent[0].data) == 64
    assert sent[0].data[0] == 3
    assert sent[0].data[1] == 0
