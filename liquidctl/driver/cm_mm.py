"""
"""

import itertools
import io
import math
import logging
import sys
import time
from pprint import pprint
from inspect import getmembers
from liquidctl.error import NotSupportedByDevice

from PIL import Image, ImageSequence

if sys.platform == "win32":
    from winusbcdc import WinUsbPy

from liquidctl.driver.usb import PyUsbDevice, UsbHidDriver



_USAGE_PAGE = 65280
_REPORT_BYTE_LENGTH = 64


class MM730(UsbHidDriver):
    _MATCHES = [
        (
            0x2516,
            0x0165,
            'Cooler Master MM730',
            {}
        )
    ]
    _LED_MODES = {
        "static":  (0x00, 0x00, [0x00, 0x00, 0x00, 0x00, 0x00]),
        "breath":  (0x01, 0x20, [0x3c, 0x37, 0x31, 0x2c, 0x26]),
        "circle":  (0x02, 0x00, [0x32, 0x2d, 0x28, 0x23, 0x1e]),
        "slide":   (0x04, 0x20, [0x64, 0x63, 0x62, 0x61, 0x60]),
        "trigger": (0x05, 0x20, [0x66, 0x65, 0x64, 0x63, 0x62]),
    }
    _LED_RANDOM_COLOR = 0xa0

    @classmethod
    def probe(cls, handle, **kwargs):
        """Probe `handle` and yield corresponding driver instances.

        These devices have multiple top-level HID usages, and HidapiDevice
        handles matching other usages have to be ignored.
        """
        if (handle.hidinfo['usage_page'] != _USAGE_PAGE):
            return



        yield from super().probe(handle, **kwargs)

    def get_status(self, direct_access=False, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        status = []

        packets = [
            [0x52, 0x28],
            [0x41, 0x80]
        ]
        data = []
        mode_code = None
        for packet in packets:
            padding = [0x0]*(_REPORT_BYTE_LENGTH - len(packet))
            self.device.write(packet + padding)
            data = self.device.read(_REPORT_BYTE_LENGTH)
            if data[0] == 0x52 and data[1] == 0x28:
                mode_code = data[4]

        if mode_code != None:
            mode_codes = {0:"static", 1: "breath", 2: "circle", 4:"slide", 5: "trigger"}
            if mode_code  in mode_codes:
                status.append(("Mode: " + mode_codes[mode_code], "", ""))
        return status


    def set_color(self, channel, mode, colors, brightness = 255, speed=2, **kwargs):
        if mode not in self._LED_MODES:
            raise NotSupportedByDevice()

        mode_code, color_modifier, speeds = self._LED_MODES[mode]

        if channel == "direct":
            colors = iter(colors)
            r, g, b = next(colors)
            speed_code = speeds[int(speed)]
        elif channel == "random":
            r,g,b=[0xff,0xff,0xff]
            color_modifier = self._LED_RANDOM_COLOR
            if mode == "circle":
                color_modifier=0x00
            if brightness > 128:
                brightness = 128
            speed_code = speeds[int(speed)]
        else:
            raise NotSupportedByDevice()

        packets = [
                [0x41, 0x80],
                [0x52],
                [0x41, 0x80],
                [0x51, 0x2b, 0, 0, mode_code, speed_code, color_modifier, 0xff, 0xff, brightness, r, g, b],
                [0x41, 0x80],
                [0x51, 0x28, 0x00, 0x00, mode_code],
                [0x41, 0x01],
                [0x50, 0x55],
                [0x41]
            ]
        for packet in packets:
            padding = [0x0]*(_REPORT_BYTE_LENGTH - len(packet))
            self.device.write(packet + padding)


