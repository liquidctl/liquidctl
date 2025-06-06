"""liquidctl driver for the ASUS Ryuo liquid coolers.

Copyright Bloodhundur and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
from typing import List

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet
from liquidctl.util import clamp, rpadlist

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 65
_PREFIX = 0xEC
_CMD_SET_FAN_SPEED = 0x2A

_REQUEST_GET_FIRMWARE = (0x82, 0x02)
_STATUS_FIRMWARE = "Firmware version"


class AsusRyuo(UsbHidDriver):
    """Driver for ASUS ROG Ryuo I 240 (fan control only)."""

    _MATCHES = [
        (0x0B05, 0x1887, "ASUS ROG Ryuo I 240", {}),
    ]

    def initialize(self, **kwargs):
        msg = self._request(*_REQUEST_GET_FIRMWARE)
        fw_string = bytes(msg[2:]).split(b'\x00')[0].decode('ascii', errors='ignore')
        return [
            (_STATUS_FIRMWARE, fw_string, ''),
        ]

    def get_status(self, **kwargs):
        _LOGGER.info("No status available")

       
    def set_fixed_speed(self, channel, duty, **kwargs):
        if channel not in ("fans", "fan"):
            raise ValueError("Only 'fans' channel is supported")
        duty = clamp(duty, 0, 100)
        _LOGGER.info(f"Setting fan speed to {duty}%")
        self._write([_PREFIX, _CMD_SET_FAN_SPEED, duty])

    def _request(self, request_header: int, response_header: int) -> List[int]:
        self.device.clear_enqueued_reports()
        self._write([_PREFIX, request_header])
        return self._read(response_header)

    def _read(self, expected_header=None) -> List[int]:
        msg = self.device.read(_REPORT_LENGTH)
        if msg[0] != _PREFIX:
            raise ExpectationNotMet("Unexpected report prefix")
        if expected_header is not None and msg[1] != expected_header:
            raise ExpectationNotMet("Unexpected report header")
        return msg

    def _write(self, data: List[int]):
        self.device.write(rpadlist(data, _REPORT_LENGTH, 0))
