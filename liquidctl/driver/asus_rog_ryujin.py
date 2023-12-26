"""liquidctl driver for the ASUS ROG RYUJIN II 360 liquid cooler.

Copyright Florian Freudiger and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet
from liquidctl.util import clamp, u16le_from, rpadlist

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 65
_PREFIX = 0xEC

# Requests and their response headers
_REQUEST_GET_FIRMWARE = (0x82, 0x02)
_REQUEST_GET_STATUS = (0x99, 0x19)
_REQUEST_GET_SPEED = (0x9A, 0x1A)

# Command headers that don't need a response
_CMD_SET_SPEED = 0x1A

_STATUS_FIRMWARE = "Firmware version"
_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_FAN_SPEED = "Embedded Micro Fan speed"
_STATUS_FAN_DUTY = "Embedded Micro Fan duty"


class RogRyujin(UsbHidDriver):
    """ASUS ROG RYUJIN II 360 liquid cooler."""

    _MATCHES = [
        (0x0B05, 0x1988, "ASUS ROG RYUJIN II 360", {}),
    ]

    def initialize(self, **kwargs):
        msg = self._request(*_REQUEST_GET_FIRMWARE)
        return [(_STATUS_FIRMWARE, "".join(map(chr, msg[3:18])), "")]

    def _get_duty(self) -> (int, int):
        """Get current pump and fan duty in %."""
        msg = self._request(*_REQUEST_GET_SPEED)
        return msg[4], msg[5]

    def get_status(self, **kwargs):
        pump_duty, fan_duty = self._get_duty()
        msg = self._request(*_REQUEST_GET_STATUS)

        return [
            (_STATUS_TEMPERATURE, msg[3] + msg[4] / 10, "°C"),
            (_STATUS_PUMP_SPEED, u16le_from(msg, 5), "rpm"),
            (_STATUS_PUMP_DUTY, pump_duty, "%"),
            (_STATUS_FAN_SPEED, u16le_from(msg, 7), "rpm"),
            (_STATUS_FAN_DUTY, fan_duty, "%"),
        ]

    def set_fixed_speed(self, channel, duty, **kwargs):
        duty = clamp(duty, 0, 100)
        pump_duty, fan_duty = self._get_duty()

        if channel == "pump":
            pump_duty = duty
        elif channel == "fan" or channel == "fan1":
            fan_duty = duty
        else:
            raise ValueError("invalid channel")

        self._write([_PREFIX, _CMD_SET_SPEED, 0x00, pump_duty, fan_duty])

    def _request(self, request_header: int, response_header: int) -> list[int]:
        self.device.clear_enqueued_reports()
        self._write([_PREFIX, request_header])
        return self._read(response_header)

    def _read(self, expected_header=None) -> list[int]:
        msg = self.device.read(_REPORT_LENGTH)

        if msg[0] != _PREFIX:
            raise ExpectationNotMet("Unexpected report prefix")
        if expected_header is not None and msg[1] != expected_header:
            raise ExpectationNotMet("Unexpected report header")

        return msg

    def _write(self, data: list[int]):
        self.device.write(rpadlist(data, _REPORT_LENGTH, 0))
