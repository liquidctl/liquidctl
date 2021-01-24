"""liquidctl driver for Gigabyte RGB Fusion 2.0 USB controllers.

Supported controllers:

- ITE 5702: found in Gigabyte Z490 Vision D
- ITE 8297: found in Gigabyte X570 Aorus Elite

Copyright (C) 2020–2021  CaseySJ, Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections import namedtuple
import logging
import sys

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_USAGE_PAGE = 0xff89
_RGB_CONTROL_USAGE = 0xcc
_OTHER_USAGE = 0x10
_REPORT_ID = 0xcc
_REPORT_BYTE_LENGTH = 63
_INIT_CMD = 0x60

_COLOR_CHANNELS = {
    'led1': (0x20, 0x01),
    'led2': (0x21, 0x02),
    'led3': (0x22, 0x04),
    'led4': (0x23, 0x08),
    'led5': (0x24, 0x10),
    'led6': (0x25, 0x20),
    'led7': (0x26, 0x40),
    'led8': (0x27, 0x80),
}

_PULSE_SPEEDS = {
    'slowest':                          (0x40, 0x06, 0x40, 0x06, 0x20, 0x03),
    'slower':                           (0x78, 0x05, 0x78, 0x05, 0xbc, 0x02),
    'normal':                           (0xb0, 0x04, 0xb0, 0x04, 0xf4, 0x01),
    'faster':                           (0xe8, 0x03, 0xe8, 0x03, 0xf4, 0x01),
    'fastest':                          (0x84, 0x03, 0x84, 0x03, 0xc2, 0x01),
    'ludicrous':                        (0x20, 0x03, 0x20, 0x03, 0x90, 0x01),
}

_FLASH_SPEEDS = {
    'slowest':                          (0x64, 0x00, 0x64, 0x00, 0x60, 0x09),
    'slower':                           (0x64, 0x00, 0x64, 0x00, 0x90, 0x08),
    'normal':                           (0x64, 0x00, 0x64, 0x00, 0xd0, 0x07),
    'faster':                           (0x64, 0x00, 0x64, 0x00, 0x08, 0x07),
    'fastest':                          (0x64, 0x00, 0x64, 0x00, 0x40, 0x06),
    'ludicrous':                        (0x64, 0x00, 0x64, 0x00, 0x78, 0x05),
}

_DOUBLE_FLASH_SPEEDS = {
    'slowest':                          (0x64, 0x00, 0x64, 0x00, 0x28, 0x0a),
    'slower ':                          (0x64, 0x00, 0x64, 0x00, 0x60, 0x09),
    'normal':                           (0x64, 0x00, 0x64, 0x00, 0x90, 0x08),
    'faster':                           (0x64, 0x00, 0x64, 0x00, 0xd0, 0x07),
    'fastest':                          (0x64, 0x00, 0x64, 0x00, 0x08, 0x07),
    'ludicrous':                        (0x64, 0x00, 0x64, 0x00, 0x40, 0x06),
}

_COLOR_CYCLE_SPEEDS = {
    'slowest':                          (0x78, 0x05, 0xb0, 0x04, 0x00, 0x00),
    'slower':                           (0x7e, 0x04, 0x1a, 0x04, 0x00, 0x00),
    'normal':                           (0x52, 0x03, 0xee, 0x02, 0x00, 0x00),
    'faster':                           (0xf8, 0x02, 0x94, 0x02, 0x00, 0x00),
    'fastest':                          (0x26, 0x02, 0xc2, 0x01, 0x00, 0x00),
    'ludicrous':                        (0xcc, 0x01, 0x68, 0x01, 0x00, 0x00),
}

_ColorMode = namedtuple('_ColorMode', ['name', 'value', 'pulses', 'flash_count',
                                       'cycle_count', 'max_brightness', 'takes_color',
                                       'speed_values'])

_COLOR_MODES = {
    mode.name: mode
    for mode in [
        _ColorMode('off', 0x01, pulses=False, flash_count=0, cycle_count=0,
                   max_brightness=0, takes_color=False, speed_values=None),
        _ColorMode('fixed', 0x01, pulses=False, flash_count=0, cycle_count=0,
                   max_brightness=90, takes_color=True, speed_values=None),
        _ColorMode('pulse', 0x02, pulses=True, flash_count=0, cycle_count=0,
                   max_brightness=90, takes_color=True, speed_values=_PULSE_SPEEDS),
        _ColorMode('flash', 0x03, pulses=True, flash_count=1, cycle_count=0,
                   max_brightness=100, takes_color=True, speed_values=_FLASH_SPEEDS),
        _ColorMode('double-flash', 0x03, pulses=True, flash_count=2, cycle_count=0,
                   max_brightness=100, takes_color=True, speed_values=_DOUBLE_FLASH_SPEEDS),
        _ColorMode('color-cycle', 0x04, pulses=False, flash_count=0, cycle_count=7,
                   max_brightness=100, takes_color=False, speed_values=_COLOR_CYCLE_SPEEDS),
    ]
}


class RgbFusion2(UsbHidDriver):
    """liquidctl driver for Gigabyte RGB Fusion 2.0 USB controllers."""

    SUPPORTED_DEVICES = [
        (0x048d, 0x5702, None, 'Gigabyte RGB Fusion 2.0 5702 Controller', {}),
        (0x048d, 0x8297, None, 'Gigabyte RGB Fusion 2.0 8297 Controller', {}),
    ]

    @classmethod
    def probe(cls, handle, **kwargs):
        """Probe `handle` and yield corresponding driver instances.

        These devices have multiple top-level HID usages, and HidapiDevice
        handles matching other usages have to be ignored.
        """

        # if usage_page/usage are not available due to hidapi limitations
        # (version, platform or backend), they are unfortunately left
        # uninitialized; because of this, we explicitly exclude the undesired
        # usage_page/usage pair, and assume in all other cases that we either
        # have the desired usage page/usage pair, or that on that system a
        # single handle is returned for that device interface (see: 259)

        if (handle.hidinfo['usage_page'] == _USAGE_PAGE and
                handle.hidinfo['usage'] == _OTHER_USAGE):
            return

        yield from super().probe(handle, **kwargs)

    def initialize(self, **kwargs):
        """Initialize the device.

        Returns a list of `(property, value, unit)` tuples, containing the
        firmware version and other useful information provided by the hardware.
        """

        self._send_feature_report([_REPORT_ID, _INIT_CMD])
        data = self._get_feature_report(_REPORT_ID)
        # be tolerant: 8297 controllers support report IDs yet return 0 in the
        # first byte, which is out of spec
        assert data[0] in (_REPORT_ID, 0) and data[1] == 0x01

        null = data.index(0, 12)
        dev_name = str(bytes(data[12:null]), 'ascii', errors='replace')
        fw_version = tuple(data[4:8])
        return [
            ('Hardware name', dev_name, ''),
            ('Firmware version', '{}.{}.{}.{}'.format(*fw_version), ''),
        ]

    def get_status(self, **kwargs):
        """Get a status report.

        Currently returns an empty list, but this behavior is not guaranteed as
        in the future the device may start to report useful information.  A
        non-empty list would contain `(property, value, unit)` tuples.
        """

        _LOGGER.info('status reports not available from %s', self.description)
        return []

    def set_color(self, channel, mode, colors, speed='normal', **kwargs):
        """Set the color mode for a specific channel.

        Up to eight individual channels are available, named 'led1' through
        'led8'.  In addition to these, the 'sync' channel can be used to apply
        the same settings to all channels.

        The table bellow summarizes the available channels.

        | Mode         | Colors required | Speed is customizable |
        | ------------ | --------------- | --------------------- |
        | off          |            zero |                    no |
        | fixed        |             one |                    no |
        | pulse        |             one |                   yes |
        | flash        |             one |                   yes |
        | double-flash |             one |                   yes |
        | color-cycle  |            zero |                   yes |

        `colors` should be an iterable of zero or one `[red, blue, green]`
        triples, where each red/blue/green component is a value in the range
        0–255.

        `speed`, when supported by the `mode`, can be one of: `slowest`,
        `slower`, `normal` (default), `faster`, `fastest` or `ludicrous`.
        """

        mode = _COLOR_MODES[mode.lower()]
        colors = iter(colors)
        channel = channel.lower()
        speed = speed.lower()

        if mode.takes_color:
            try:
                r, g, b = next(colors)
                single_color = (b, g, r)
            except StopIteration:
                raise ValueError(f'one color required for mode={mode.name}') from None
        else:
            single_color = (0, 0, 0)
        remaining = sum(1 for _ in colors)
        if remaining:
            _LOGGER.warning('too many colors for mode=%s, dropping %d', mode.name, remaining)

        brightness = clamp(100, 0, mode.max_brightness)  # hardcode this for now
        data = [_REPORT_ID, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, mode.value, brightness, 0x00]
        data += single_color
        data += [0x00, 0x00, 0x00, 0x00, 0x00]
        if mode.speed_values:
            data += mode.speed_values[speed]
        else:
            data += [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        data += [0x00, 0x00, mode.cycle_count, int(mode.pulses), mode.flash_count]

        if channel == 'sync':
            selected_channels = _COLOR_CHANNELS.values()
        else:
            selected_channels = (_COLOR_CHANNELS[channel],)
        for addr1, addr2 in selected_channels:
            data[1:3] = addr1, addr2
            self._send_feature_report(data)
        self._execute_report()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def reset_all_channels(self):
        """Reset all LED channels."""
        for addr1, _ in _COLOR_CHANNELS.values():
            self._send_feature_report([_REPORT_ID, addr1, 0])
        self._execute_report()

    def _get_feature_report(self, report_id):
        return self.device.get_feature_report(report_id, _REPORT_BYTE_LENGTH + 1)

    def _send_feature_report(self, data):
        padding = [0x0]*(_REPORT_BYTE_LENGTH + 1 - len(data))
        self.device.send_feature_report(data + padding)

    def _execute_report(self):
        """Request for the previously sent lighting settings to be applied."""
        self._send_feature_report([_REPORT_ID, 0x28, 0xff])


# Acknowledgments:
#
# Thanks to SgtSixPack for capturing USB traffic on 0x8297 and testing the driver on Windows.
