import pytest
from _testutils import MockPyusbDevice

from collections import deque

from liquidctl.driver.asetek_pro import HydroPro


@pytest.fixture
def emulate():
    usb_dev = MockPyusbDevice()
    cooler = HydroPro(usb_dev, 'Emulated Asetek Pro cooler', fan_count=2)
    return (usb_dev, cooler)


def test_not_totally_broken(emulate):
    _, cooler = emulate

    with cooler.connect():
        cooler.initialize()

        cooler.get_status()

        cooler.set_color(channel='logo', mode='blinking', colors=iter([[3, 2, 1]]))
        cooler.set_color(channel='logo', mode='pulse', colors=[[3, 2, 1]], speed='normal')

        cooler.set_speed_profile(channel='fan',
                                      profile=iter([(20, 20), (30, 50), (40, 100)]))
        cooler.set_speed_profile(channel='fan1',
                                      profile=iter([(20, 20), (30, 50), (40, 100)]))

        cooler.set_fixed_speed(channel='fan', duty=50)


def test_initialize_with_pump_mode(emulate):
    usb_dev, cooler = emulate

    with cooler.connect():
        cooler.initialize(pump_mode='balanced')

        _begin, set_pump = usb_dev._sent_xfers
        assert set_pump == ('write', 1, [0x32, 0x01])


def test_set_profile_of_all_fans(emulate):
    usb_dev, cooler = emulate

    # When setting the speed of all fans the driver first gets the speed of all
    # fans to work out how many fans are present. Set 2 valid responses to
    # simulate a setup with 2 fans present.  The first response is for the pump
    # setup in the initialize function.

    with cooler.connect():
        cooler.initialize()

        cooler.set_speed_profile(channel='fan', profile=[(0, 10), (25, 50), (40, 100)])

        _begin, _pump, fan1, fan2 = usb_dev._sent_xfers
        assert fan1 == ('write', 1, [0x40, 0x00, 0x00, 0x19, 0x28, 0x3c, 0x3c, 0x3c,
                                          0x3c, 0x0a, 0x32, 0x64, 0x64, 0x64, 0x64, 0x64])
        assert fan2 == ('write', 1, [0x40, 0x01, 0x00, 0x19, 0x28, 0x3c, 0x3c, 0x3c,
                                          0x3c, 0x0a, 0x32, 0x64, 0x64, 0x64, 0x64, 0x64])


def test_setting_speed_on_single_fan_2(emulate):
    usb_dev, cooler = emulate

    with cooler.connect():
        cooler.initialize()

        cooler.set_fixed_speed('fan2', 100)

        _begin, _pump, fan2 = usb_dev._sent_xfers
        assert fan2 == ('write', 1, [0x42, 0x01, 0x64])


def test_set_pump_to_fixed_color(emulate):
    usb_dev, cooler = emulate

    with cooler.connect():
        cooler.initialize()

        cooler.set_color(channel='logo', mode='fixed', colors=iter([[0xff, 0x88, 0x44]]))

        _begin, _pump, color_change, color_end = usb_dev._sent_xfers
        assert color_change == ('write', 1, [0x56, 0x02, 0xff, 0x88,
                                             0x44, 0xff, 0x88, 0x44])
        assert color_end == ('write', 1, [0x55, 0x01])


def test_set_pump_to_blinking_mode(emulate):
    usb_dev, cooler = emulate

    with cooler.connect():
        cooler.initialize()

        cooler.set_color(channel='logo', mode='blinking', speed='normal',
            colors=iter([[0xff, 0x88, 0x44], [0xff, 0xff, 0xff], [0x00, 0x00, 0x00]]))

        _begin, _pump, color_change, color_mode, color_end = usb_dev._sent_xfers
        assert color_change == ('write', 1, [0x56, 0x03, 0xff, 0x88, 0x44, 0xff,
                                             0xff, 0xff, 0x00, 0x00, 0x00])
        assert color_mode == ('write', 1, [0x53, 0x0A])
        assert color_end == ('write', 1, [0x58, 0x01])
