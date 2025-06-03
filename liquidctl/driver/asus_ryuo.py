import logging
from typing import List

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.error import ExpectationNotMet
from liquidctl.util import clamp, rpadlist

_LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 65
_PREFIX = 0xEC
_CMD_SET_FAN_SPEED = 0x2A  # from your reverse engineering

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

class AsusRyuoTest(UsbHidDriver):
    """Driver for ASUS ROG Ryuo I 240 (fan control only)."""

    _MATCHES = [
        (0x0B05, 0x1887, "ASUS ROG Ryuo I 240 (Test Driver)", {}),
    ]

    feature_set_fixed_speed = True

    def initialize(self, **kwargs):
        _LOGGER.info("No initialization required for AsusRyuoTest")

    def get_status(self, **kwargs):
        msg = self._request(*_REQUEST_GET_FIRMWARE)
        return [(_STATUS_FIRMWARE, "".join(map(chr, msg[3:18])), "")]

    def set_fixed_speed(self, channel, duty, **kwargs):
        if channel != "fans":
            raise ValueError("Only 'fans' channel is supported")
        duty = clamp(duty, 0, 100)
        #self._set_fan_speed(duty)
        self._write([_PREFIX, _CMD_SET_FAN_SPEED, duty])

    def _set_fan_speed(self, duty: int):
        _LOGGER.info(f"Setting fan speed to {duty}%")
        self._write([_PREFIX, _CMD_SET_FAN_SPEED, duty])

    def _write(self, data: List[int]):
        self.device.write(rpadlist(data, _REPORT_LENGTH, 0))

