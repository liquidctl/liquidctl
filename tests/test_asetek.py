import pytest
from _testutils import MockPyusbDevice, MockRuntimeStorage

from collections import deque

from liquidctl.driver.asetek import Modern690Lc, Legacy690Lc, Hydro690Lc


@pytest.fixture
def mockModern690LcDevice():
    device = MockPyusbDevice()
    dev = Modern690Lc(device, 'Mock Modern 690LC')

    dev.connect()
    return dev


@pytest.fixture
def mockLegacy690LcDevice():
    device = MockPyusbDevice(vendor_id=0xffff, product_id=0xb200, bus=1, port=(1,))
    dev = Legacy690Lc(device, 'Mock Legacy 690LC')

    runtime_storage = MockRuntimeStorage(key_prefixes=['testing'])
    runtime_storage.store('leds_enabled', 0)

    dev.connect(runtime_storage=runtime_storage)
    return dev


def test_modern690Lc_device_not_totally_broken(mockModern690LcDevice):
    """A few reasonable example calls do not raise exceptions."""
    dev = mockModern690LcDevice

    dev.initialize()
    dev.get_status()
    dev.set_color(channel='led', mode='blinking', colors=iter([[3, 2, 1]]),
                  time_per_color=3, time_off=1, alert_threshold=42,
                  alert_color=[90, 80, 10])
    dev.set_color(channel='led', mode='rainbow', colors=[], speed=5)
    dev.set_speed_profile(channel='fan',
                          profile=iter([(20, 20), (30, 50), (40, 100)]))
    dev.set_fixed_speed(channel='pump', duty=50)


def test_modern690Lc_device_connect(mockModern690LcDevice):
    def mock_open():
        nonlocal opened
        opened = True
    mockModern690LcDevice.device.open = mock_open
    opened = False

    with mockModern690LcDevice.connect() as cm:
        assert cm == mockModern690LcDevice
        assert opened


def test_modern690Lc_device_begin_transaction(mockModern690LcDevice):
    mockModern690LcDevice.device._reset_sent()

    mockModern690LcDevice.get_status()

    (begin, _) = mockModern690LcDevice.device._sent_xfers
    xfer_type, bmRequestType, bRequest, wValue, wIndex, datalen = begin
    assert xfer_type == 'ctrl_transfer'
    assert bRequest == 2
    assert bmRequestType == 0x40
    assert wValue == 1
    assert wIndex == 0
    assert datalen is None


def test_modern690Lc_initialize_can_persist_settings(mockModern690LcDevice):
    dev = mockModern690LcDevice
    dev.device._reset_sent()

    dev.initialize(non_volatile=True)

    _begin, (cmd_msgtype, cmd_ep, cmd_data) = dev.device._sent_xfers[-2:]
    assert cmd_msgtype == 'write'
    assert cmd_ep == 2
    assert cmd_data == [0x21]


def test_modern690Lc_set_color_can_persist_settings(mockModern690LcDevice):
    dev = mockModern690LcDevice
    dev.device._reset_sent()

    dev.set_color(channel='led', mode='rainbow', colors=[], non_volatile=True)

    _begin, (cmd_msgtype, cmd_ep, cmd_data) = dev.device._sent_xfers[-2:]
    assert cmd_msgtype == 'write'
    assert cmd_ep == 2
    assert cmd_data == [0x21]


def test_modern690Lc_set_speed_profile_can_persist_settings(mockModern690LcDevice):
    dev = mockModern690LcDevice
    dev.device._reset_sent()

    dev.set_speed_profile(channel='fan', profile=[(20, 20), (30, 50), (40, 100)],
                          non_volatile=True)

    _begin, (cmd_msgtype, cmd_ep, cmd_data) = dev.device._sent_xfers[-2:]
    assert cmd_msgtype == 'write'
    assert cmd_ep == 2
    assert cmd_data == [0x21]


def test_modern690Lc_set_fixed_speed_can_persist_settings(mockModern690LcDevice):
    dev = mockModern690LcDevice
    dev.device._reset_sent()

    dev.set_fixed_speed(channel='pump', duty=50, non_volatile=True)

    _begin, (cmd_msgtype, cmd_ep, cmd_data) = dev.device._sent_xfers[-2:]
    assert cmd_msgtype == 'write'
    assert cmd_ep == 2
    assert cmd_data == [0x21]


def test_legacy690Lc_device_not_totally_broken(mockLegacy690LcDevice):
    """A few reasonable example calls do not raise exceptions."""
    dev = mockLegacy690LcDevice

    dev.initialize()
    status = dev.get_status()
    dev.set_color(channel='led', mode='blinking', colors=iter([[3, 2, 1]]),
                  time_per_color=3, time_off=1, alert_threshold=42,
                  alert_color=[90, 80, 10])
    dev.set_fixed_speed(channel='fan', duty=80)
    dev.set_fixed_speed(channel='pump', duty=50)


def test_legacy690Lc_device_matches_leviathan_updates(mockLegacy690LcDevice):
    dev = mockLegacy690LcDevice

    dev.initialize()
    dev.set_fixed_speed(channel='pump', duty=50)

    dev.device._reset_sent()
    dev.set_color(channel='led', mode='fading', colors=[[0, 0, 255], [0, 255, 0]],
                  time_per_color=1, alert_threshold=60, alert_color=[0, 0, 0])
    _begin, (color_msgtype, color_ep, color_data) = dev.device._sent_xfers
    assert color_msgtype == 'write'
    assert color_ep == 2
    assert color_data[0:12] == [0x10, 0, 0, 255, 0, 255, 0, 0, 0, 0, 0x3c, 1]

    dev.device._reset_sent()
    dev.set_fixed_speed(channel='fan', duty=50)
    _begin, pump_message, fan_message = dev.device._sent_xfers
    assert pump_message == ('write', 2, [0x13, 50])
    assert fan_message == ('write', 2, [0x12, 50])


def test_legacy690Lc_device_initialize_warns_on_non_volatile(mockLegacy690LcDevice, caplog):
    mockLegacy690LcDevice.initialize(non_volatile=True)

    assert 'device does not support non-volatile' in caplog.text


def test_legacy690Lc_device_set_color_warns_on_non_volatile(mockLegacy690LcDevice, caplog):
    mockLegacy690LcDevice.set_color(channel='led', mode='blinking',
                                    colors=iter([[3, 2, 1]]), non_volatile=True)

    assert 'device does not support non-volatile' in caplog.text


def test_legacy690Lc_device_set_fixed_speed_warns_on_non_volatile(mockLegacy690LcDevice, caplog):
    mockLegacy690LcDevice.set_fixed_speed(channel='fan', duty=80, non_volatile=True)

    assert 'device does not support non-volatile' in caplog.text
