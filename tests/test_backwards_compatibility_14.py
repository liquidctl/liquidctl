import pytest

from _testutils import MockHidapiDevice

RADICAL_RED = [0xff, 0x35, 0x5e]
MOUNTAIN_MEADOW = [0x1a, 0xb3, 0x85]


def test_find_from_driver_package_still_available():
    from liquidctl.driver import find_liquidctl_devices


def test_kraken2_backwards_modes_are_deprecated(caplog):
    modes = ['backwards-spectrum-wave', 'backwards-marquee-3',
             'backwards-marquee-4', 'backwards-marquee-5',
             'backwards-marquee-6', 'covering-backwards-marquee',
             'backwards-moving-alternating', 'backwards-super-wave']

    from liquidctl.driver.kraken2 import Kraken2

    for mode in modes:
        base_mode = mode.replace('backwards-', '')

        old = Kraken2(MockHidapiDevice(), 'Mock X62',
                      device_type=Kraken2.DEVICE_KRAKENX)
        new = Kraken2(MockHidapiDevice(), 'Mock X62',
                      device_type=Kraken2.DEVICE_KRAKENX)

        colors = [RADICAL_RED, MOUNTAIN_MEADOW]

        old.set_color('ring', mode, colors)
        new.set_color('ring', base_mode, colors, direction='backward')

        assert old.device.sent == new.device.sent, \
               f'{mode} != {base_mode} + direction=backward'

        assert 'deprecated mode' in caplog.text


def test_kraken3_backwards_modes_are_deprecated(caplog):
    modes = ['backwards-spectrum-wave', 'backwards-marquee-3',
             'backwards-marquee-4', 'backwards-marquee-5',
             'backwards-marquee-6', 'backwards-moving-alternating-3',
             'covering-backwards-marquee', 'backwards-moving-alternating-4',
             'backwards-moving-alternating-5', 'backwards-moving-alternating-6',
             'backwards-rainbow-flow', 'backwards-super-rainbow',
             'backwards-rainbow-pulse']

    from liquidctl.driver.kraken3 import KrakenX3
    from liquidctl.driver.kraken3 import _COLOR_CHANNELS_KRAKENX
    from liquidctl.driver.kraken3 import _SPEED_CHANNELS_KRAKENX

    for mode in modes:
        base_mode = mode.replace('backwards-', '')

        old = KrakenX3(MockHidapiDevice(), 'Mock X63',
                       speed_channels=_SPEED_CHANNELS_KRAKENX,
                       color_channels=_COLOR_CHANNELS_KRAKENX)
        new = KrakenX3(MockHidapiDevice(), 'Mock X63',
                       speed_channels=_SPEED_CHANNELS_KRAKENX,
                       color_channels=_COLOR_CHANNELS_KRAKENX)

        colors = [RADICAL_RED, MOUNTAIN_MEADOW]

        old.set_color('ring', mode, colors)
        new.set_color('ring', base_mode, colors, direction='backward')

        assert old.device.sent == new.device.sent, \
               f'{mode} != {base_mode} + direction=backward'

        assert 'deprecated mode' in caplog.text


def test_smart_device_v1_backwards_modes_are_deprecated(caplog):
    modes = ['backwards-spectrum-wave', 'backwards-marquee-3',
             'backwards-marquee-4', 'backwards-marquee-5',
             'backwards-marquee-6', 'covering-backwards-marquee',
             'backwards-moving-alternating', 'backwards-super-wave']

    from liquidctl.driver.smart_device import SmartDevice

    for mode in modes:
        base_mode = mode.replace('backwards-', '')

        old = SmartDevice(MockHidapiDevice(), 'Mock Smart Device',
                          speed_channel_count=3, color_channel_count=1)
        new = SmartDevice(MockHidapiDevice(), 'Mock Smart Device',
                          speed_channel_count=3, color_channel_count=1)

        colors = [RADICAL_RED, MOUNTAIN_MEADOW]

        old.set_color('led', mode, colors)
        new.set_color('led', base_mode, colors, direction='backward')

        assert old.device.sent == new.device.sent, \
               f'{mode} != {base_mode} + direction=backward'

        assert 'deprecated mode' in caplog.text


def test_hue2_backwards_modes_are_deprecated(caplog):
    modes = ['backwards-spectrum-wave', 'backwards-marquee-3',
             'backwards-marquee-4', 'backwards-marquee-5',
             'backwards-marquee-6', 'backwards-moving-alternating-3',
             'covering-backwards-marquee', 'backwards-moving-alternating-4',
             'backwards-moving-alternating-5', 'backwards-moving-alternating-6',
             'backwards-rainbow-flow', 'backwards-super-rainbow',
             'backwards-rainbow-pulse']

    from liquidctl.driver.smart_device import SmartDevice2

    for mode in modes:
        base_mode = mode.replace('backwards-', '')

        old = SmartDevice2(MockHidapiDevice(), 'Mock Smart Device V2',
                           speed_channel_count=3, color_channel_count=2)
        new = SmartDevice2(MockHidapiDevice(), 'Mock Smart Device V2',
                           speed_channel_count=3, color_channel_count=2)

        colors = [RADICAL_RED, MOUNTAIN_MEADOW]

        old.set_color('led1', mode, colors)
        new.set_color('led1', base_mode, colors, direction='backward')

        assert old.device.sent == new.device.sent, \
               f'{mode} != {base_mode} + direction=backward'

        assert 'deprecated mode' in caplog.text
