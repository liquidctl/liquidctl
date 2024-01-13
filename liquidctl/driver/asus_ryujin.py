"""liquidctl driver for the ASUS Ryujin II liquid coolers.

Copyright Florian Freudiger and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
from typing import List

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet, NotSupportedByDriver
from liquidctl.util import clamp, u16le_from, rpadlist, fraction_of_byte

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 65
_PREFIX = 0xEC

# Requests and their response headers
_REQUEST_GET_FIRMWARE = (0x82, 0x02)
_REQUEST_GET_COOLER_STATUS = (0x99, 0x19)
_REQUEST_GET_COOLER_DUTY = (0x9A, 0x1A)
_REQUEST_GET_CONTROLLER_DUTY = (0xA1, 0x21)
_REQUEST_GET_CONTROLLER_SPEED = (0xA0, 0x20)

# Command headers that don't need a response
_CMD_SET_COOLER_SPEED = 0x1A
_CMD_SET_CONTROLLER_SPEED = 0x21

_STATUS_FIRMWARE = "Firmware version"
_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_COOLER_FAN_SPEED = "Pump fan speed"
_STATUS_COOLER_FAN_DUTY = "Pump fan duty"
_STATUS_CONTROLLER_FAN_SPEED = "External fan {} speed"
_STATUS_CONTROLLER_FAN_DUTY = "External fan duty"


class AsusRyujin(UsbHidDriver):
    """ASUS Ryujin II liquid cooler."""

    _MATCHES = [
        (0x0B05, 0x1988, "ASUS Ryujin II 360", {}),
    ]

    def initialize(self, **kwargs):
        msg = self._request(*_REQUEST_GET_FIRMWARE)
        return [(_STATUS_FIRMWARE, "".join(map(chr, msg[3:18])), "")]

    def _get_cooler_duty(self) -> (int, int):
        """Get current pump and embedded fan duty in %."""
        msg = self._request(*_REQUEST_GET_COOLER_DUTY)
        return msg[4], msg[5]

    def _get_cooler_status(self) -> (int, int, int):
        """Get current liquid temperature, pump and embedded fan speed."""
        msg = self._request(*_REQUEST_GET_COOLER_STATUS)
        liquid_temp = msg[3] + msg[4] / 10
        pump_speed = u16le_from(msg, 5)
        fan_speed = u16le_from(msg, 7)
        return liquid_temp, pump_speed, fan_speed

    def _get_controller_speeds(self) -> List[int]:
        """Get AIO controller fan speeds in rpm."""
        msg = self._request(*_REQUEST_GET_CONTROLLER_SPEED)
        speed1 = u16le_from(msg, 5)
        speed2 = u16le_from(msg, 7)
        speed3 = u16le_from(msg, 9)
        speed4 = u16le_from(msg, 3)  # For some reason comes first in msg
        return [speed1, speed2, speed3, speed4]

    def _get_controller_duty(self) -> int:
        """Get AIO controller fan duty in %."""
        msg = self._request(*_REQUEST_GET_CONTROLLER_DUTY)
        return round(msg[4] / 0xFF * 100)

    def get_status(self, **kwargs):
        pump_duty, fan_duty = self._get_cooler_duty()
        liquid_temp, pump_speed, fan_speed = self._get_cooler_status()
        controller_speeds = self._get_controller_speeds()
        controller_duty = self._get_controller_duty()

        status = [
            (_STATUS_TEMPERATURE, liquid_temp, "°C"),
            (_STATUS_PUMP_DUTY, pump_duty, "%"),
            (_STATUS_PUMP_SPEED, pump_speed, "rpm"),
            (_STATUS_COOLER_FAN_DUTY, fan_duty, "%"),
            (_STATUS_COOLER_FAN_SPEED, fan_speed, "rpm"),
            (_STATUS_CONTROLLER_FAN_DUTY, controller_duty, "%"),
        ]

        for i, controller_speed in enumerate(controller_speeds):
            status.append((_STATUS_CONTROLLER_FAN_SPEED.format(i + 1), controller_speed, "rpm"))

        return status

    def _set_cooler_duties(self, pump_duty: int, fan_duty: int):
        self._write([_PREFIX, _CMD_SET_COOLER_SPEED, 0x00, pump_duty, fan_duty])

    def _set_cooler_pump_duty(self, duty: int):
        pump_duty, fan_duty = self._get_cooler_duty()

        if duty == pump_duty:
            return

        self._set_cooler_duties(duty, fan_duty)

    def _set_cooler_fan_duty(self, duty: int):
        pump_duty, fan_duty = self._get_cooler_duty()

        if duty == fan_duty:
            return

        self._set_cooler_duties(pump_duty, duty)

    def _set_controller_duty(self, duty: int):
        # Controller duty is set between 0x00 and 0xFF
        duty = fraction_of_byte(percentage=duty)

        self._write([_PREFIX, _CMD_SET_CONTROLLER_SPEED, 0x00, 0x00, duty])

    def set_fixed_speed(self, channel, duty, **kwargs):
        duty = clamp(duty, 0, 100)
        if channel == "pump":
            self._set_cooler_pump_duty(duty)
        elif channel == "fans":
            self._set_cooler_fan_duty(duty)
            self._set_controller_duty(duty)
        elif channel == "pump-fan":
            self._set_cooler_fan_duty(duty)
        elif channel == "external-fans":
            self._set_controller_duty(duty)
        else:
            raise ValueError("invalid channel")

    def set_screen(self, channel, mode, value, **kwargs):
        # Not yet reverse engineered / implemented
        raise NotSupportedByDriver()

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
