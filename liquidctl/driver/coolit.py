"""liquidctl driver for Corsair Platinum and PRO XT coolers.

Supported devices
-----------------

 - Corsair H110i GT

Supported features
------------------

 - general monitoring
 - pump speed control
 - fan speed control

Copyright Roberto Marques, Serphentas, and other contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import re

from enum import Enum, unique

from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver
from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.util import clamp, fraction_of_byte, u16le_from, normalize_profile


LOGGER = logging.getLogger(__name__)

_REPORT_LENGTH = 64
_PUMP_INDEX = 0x02

_COMMAND_FIRMWARE_ID = 0x01
_COMMAND_TEMP_READ = 0x0E
_COMMAND_FAN_SELECT = 0x10
_COMMAND_FAN_MODE = 0x12
_COMMAND_FAN_FIXED_PWM = 0x13
_COMMAND_FAN_FIXED_RPM = 0x14
_COMMAND_FAN_READ_RPM = 0x16
_COMMAND_FAN_MAX_RPM = 0x17
_COMMAND_FAN_RPM_TABLE = 0x19
_COMMAND_FAN_TEMP_TABLE = 0x1A

_OP_CODE_WRITE_ONE_BYTE = 0x06
_OP_CODE_READ_ONE_BYTE = 0x07
_OP_CODE_WRITE_TWO_BYTES = 0x08
_OP_CODE_READ_TWO_BYTES = 0x09
_OP_CODE_WRITE_THREE_BYTES = 0x0A
_OP_CODE_READ_THREE_BYTES = 0x0B

_PROFILE_LENGTH = 5
_CRITICAL_TEMPERATURE = 60

_PUMP_DEFAULT_QUIET = [0x2E, 0x09]
_PUMP_DEFAULT_EXTREME = [0x86, 0x0B]

_SEQUENCE_MIN = 1
_SEQUENCE_MAX = 255


@unique
class _FanMode(Enum):
    FIXED_DUTY = 0x02
    FIXED_RPM = 0x04
    CUSTOM_PROFILE = 0x0E

    @classmethod
    def _missing_(cls, value):
        LOGGER.debug("falling back to FIXED_DUTY for _FanMode(%s)", value)
        return _FanMode.FIXED_DUTY


@unique
class _PumpMode(Enum):
    QUIET = 0x08
    EXTREME = 0x0C

    @classmethod
    def _missing_(cls, value):
        LOGGER.debug("falling back to QUIET for _PumpMode(%s)", value)
        return _PumpMode.QUIET


def _sequence():
    """Return a generator that produces valid protocol sequence numbers.

    Sequence numbers start from 2 to 31, then rolling over to 1 and up again.
    """
    num = 1
    while True:
        yield (num % 31) + 1
        num += 1


def _prepare_profile(original):
    clamped = ((temp, clamp(duty, 0, 100)) for temp, duty in original)
    normal = normalize_profile(clamped, _CRITICAL_TEMPERATURE)
    missing = _PROFILE_LENGTH - len(normal)
    if missing < 0:
        raise ValueError(f"Too many points in profile (remove {-missing})")
    if missing > 0:
        normal += missing * [(_CRITICAL_TEMPERATURE, 100)]
    return normal


def _quoted(*names):
    return ", ".join(map(repr, names))


class Coolit(UsbHidDriver):
    """liquidctl driver for Corsair H110i GT cooler"""

    _MATCHES = [
        (
            0x1B1C,
            0x0C04,
            "Corsair H110i GT",
            {"has_pump": True, "fan_count": 2, "rgb_fans": False},
        ),
    ]

    def __init__(self, device, description, fan_count, rgb_fans, **kwargs):
        super().__init__(device, description, **kwargs)
        self._component_count = 1 + fan_count * rgb_fans
        self._fan_names = [f"fan{i + 1}" for i in range(fan_count)]

        # the following fields are only initialized in connect()
        self._data = None
        self._sequence = None

    def connect(self, **kwargs):
        """Connect to the device."""
        ret = super().connect(**kwargs)
        ids = f"vid{self.vendor_id:04x}_pid{self.product_id:04x}"
        loc = "loc" + "_".join(re.findall(r"\d+", self.address))
        self._data = RuntimeStorage(key_prefixes=[ids, loc])
        self._sequence = _sequence()
        return ret

    def initialize(self, pump_mode="quiet", **kwargs):
        """Initialize the device and set the pump mode

        The device should be initialized every time it is powered on, including when
        the system resumes from suspending to memory.

        Valid values for `pump_mode` are "quiet" and "extreme".
        Unconfigured fan channels may default to 100% duty.

        Returns a list of `(property, value, unit)` tuples.
        """
        if pump_mode not in ["quiet", "extreme"]:
            LOGGER.warning('pump mode must be either "quiet" or "extreme", falling back to "quiet"')
            pump_mode = "quiet"

        self._data.store("pump_mode", _PumpMode[pump_mode.upper()].value)

        res = self._send_command(
            self._build_data_package(_COMMAND_FIRMWARE_ID, _OP_CODE_READ_TWO_BYTES)
        )

        fw_version = (res[3] >> 4, res[3] & 0xF, res[2])
        return [("Firmware version", "%d.%d.%d" % fw_version, "")]

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        dataPackages = list()

        # temperature
        dataPackages.append(self._build_data_package(_COMMAND_TEMP_READ, _OP_CODE_READ_TWO_BYTES))

        # fan 1
        dataPackages.append(
            self._build_data_package(
                _COMMAND_FAN_SELECT, _OP_CODE_WRITE_ONE_BYTE, params=bytes([0])
            )
        )
        dataPackages.append(
            self._build_data_package(_COMMAND_FAN_READ_RPM, _OP_CODE_READ_TWO_BYTES)
        )

        # fan 2
        dataPackages.append(
            self._build_data_package(
                _COMMAND_FAN_SELECT, _OP_CODE_WRITE_ONE_BYTE, params=bytes([1])
            )
        )
        dataPackages.append(
            self._build_data_package(_COMMAND_FAN_READ_RPM, _OP_CODE_READ_TWO_BYTES)
        )

        # pump
        dataPackages.append(
            self._build_data_package(
                _COMMAND_FAN_SELECT, _OP_CODE_WRITE_ONE_BYTE, params=bytes([2])
            )
        )
        dataPackages.append(
            self._build_data_package(_COMMAND_FAN_READ_RPM, _OP_CODE_READ_TWO_BYTES)
        )

        res = self._send_commands(dataPackages)

        temp = res[3] + res[2] / 255

        return [
            ("Liquid temperature", temp, "°C"),
            ("Fan 1 speed", u16le_from(res, offset=8), "rpm"),
            ("Fan 2 speed", u16le_from(res, offset=14), "rpm"),
            ("Pump speed", u16le_from(res, offset=20), "rpm"),
        ]

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set fan or fans to a fixed speed duty.

        Valid channel values are "fanN", where N >= 1 is the fan number, and
        "fan", to simultaneously configure all fans.  Unconfigured fan channels
        may default to 100% duty.
        """
        for hw_channel in self._get_hw_fan_channels(channel):
            self._data.store(f"{hw_channel}_mode", _FanMode.FIXED_DUTY.value)
            self._data.store(f"{hw_channel}_duty", duty)
            LOGGER.info(f"setting {hw_channel} to duty mode")
        self._send_set_cooling()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set fan or fans to follow a speed duty profile.

        Valid channel values are "fanN", where N >= 1 is the fan number, and
        "fan", to simultaneously configure all fans.  Unconfigured fan channels
        may default to 100% duty.

        Up to seven (temperature, duty) pairs can be supplied in `profile`,
        with temperatures in Celsius and duty values in percentage.  The last
        point should set the fan to 100% duty cycle, or be omitted; in the
        latter case the fan will be set to max out at 60°C.
        """
        profile = list(profile)
        for hw_channel in self._get_hw_fan_channels(channel):
            self._data.store(f"{hw_channel}_mode", _FanMode.CUSTOM_PROFILE.value)
            self._data.store(f"{hw_channel}_profile", profile)
            LOGGER.info(f"setting {hw_channel} to profile mode")
        self._send_set_cooling()

    def set_color(self, channel, mode, colors, **kwargs):
        """Not supported by this driver."""
        raise NotSupportedByDriver()

    def set_screen(self, channel, mode, value, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice()

    def _get_hw_fan_channels(self, channel):
        channel = channel.lower()
        if channel == "fan":
            return self._fan_names
        if channel in self._fan_names:
            return [channel]
        raise ValueError(f"Unknown channel, should be one of: {_quoted('fan', *self._fan_names)}")

    def _build_data_package(self, command, opCode, params=None):
        if params:
            buf = bytearray(3 + len(params))
            buf[3 : 3 + len(params)] = params
        else:
            buf = bytearray(3)

        buf[0] = next(self._sequence)
        buf[1] = opCode
        buf[2] = command

        return buf

    def _send_commands(self, dataPackages):
        buf = bytearray(_REPORT_LENGTH)

        startIndex = 1
        for dataPackage in dataPackages:
            buf[startIndex : startIndex + len(dataPackage)] = dataPackage
            startIndex += len(dataPackage)

        buf[0] = startIndex - 1

        return self._send_buffer(buf)

    def _send_command(self, dataPackage):
        buf = bytearray(_REPORT_LENGTH)

        buf[0] = len(dataPackage)
        buf[1:] = dataPackage

        return self._send_buffer(buf)

    def _send_buffer(self, buf):
        self.device.clear_enqueued_reports()
        self.device.write(buf)
        buf = bytes(self.device.read(_REPORT_LENGTH))
        return buf

    def _send_set_cooling(self):
        for fan in self._fan_names:
            fanIndex = 0 if fan == "fan1" else 1

            mode = _FanMode(self._data.load(f"{fan}_mode", of_type=int))

            if mode is _FanMode.FIXED_DUTY:
                stored = self._data.load(f"{fan}_duty", of_type=int, default=100)
                duty = clamp(stored, 0, 100)
                self._send_command(
                    self._build_data_package(
                        _COMMAND_FAN_SELECT, _OP_CODE_WRITE_ONE_BYTE, params=bytes([fanIndex])
                    )
                )
                self._send_command(
                    self._build_data_package(
                        _COMMAND_FAN_MODE, _OP_CODE_WRITE_ONE_BYTE, params=bytes([mode.value])
                    )
                )
                self._send_command(
                    self._build_data_package(
                        _COMMAND_FAN_FIXED_PWM,
                        _OP_CODE_WRITE_ONE_BYTE,
                        params=bytes([fraction_of_byte(percentage=duty)]),
                    )
                )
                LOGGER.info("setting %s to %d%% duty cycle", fan, duty)

            elif mode is _FanMode.CUSTOM_PROFILE:
                stored = self._data.load(f"{fan}_profile", of_type=list, default=[])
                profile = _prepare_profile(stored)  # ensures correct len(profile)
                pairs = ((temp, fraction_of_byte(percentage=duty)) for temp, duty in profile)

                # "magical" 0x0A in front of curve definition packages
                fanTemperatureData = [0x0A]
                fanDutyData = [0x0A]

                # get max RPM for current fan
                dataPackages = []
                dataPackages.append(
                    self._build_data_package(
                        _COMMAND_FAN_SELECT, _OP_CODE_WRITE_ONE_BYTE, params=bytes([0])
                    )
                )
                dataPackages.append(
                    self._build_data_package(_COMMAND_FAN_MAX_RPM, _OP_CODE_READ_TWO_BYTES)
                )
                max_rpm = u16le_from(self._send_commands(dataPackages), offset=4)

                for temp, duty in profile:
                    fanTemperatureData.append(0x00)
                    fanTemperatureData.append(temp)

                    rpm = duty * max_rpm / 100
                    fanDutyData.append(int(rpm % 255))
                    fanDutyData.append(int(rpm - (rpm % 255)) >> 8)

                # select fan to customize
                self._send_command(
                    self._build_data_package(
                        _COMMAND_FAN_SELECT, _OP_CODE_WRITE_ONE_BYTE, params=bytes([fanIndex])
                    )
                )

                # Change mode to custom Profile
                self._send_command(
                    self._build_data_package(
                        _COMMAND_FAN_MODE, _OP_CODE_WRITE_ONE_BYTE, params=bytes([mode.value])
                    )
                )

                # Send duty cycle Profile
                self._send_command(
                    self._build_data_package(
                        _COMMAND_FAN_RPM_TABLE,
                        _OP_CODE_WRITE_THREE_BYTES,
                        params=bytes(fanDutyData),
                    )
                )

                # Send temperature profile
                self._send_command(
                    self._build_data_package(
                        _COMMAND_FAN_TEMP_TABLE,
                        _OP_CODE_WRITE_THREE_BYTES,
                        params=bytes(fanTemperatureData),
                    )
                )

                LOGGER.info("setting %s to follow profile %r", fan, profile)
            else:
                raise ValueError(f"Unsupported fan {mode}")

        pump_mode = _PumpMode(self._data.load("pump_mode", of_type=int))

        self._send_commands(
            [
                self._build_data_package(
                    _COMMAND_FAN_SELECT, _OP_CODE_WRITE_ONE_BYTE, params=bytes([_PUMP_INDEX])
                ),
                self._build_data_package(
                    _COMMAND_FAN_FIXED_RPM,
                    _OP_CODE_WRITE_TWO_BYTES,
                    params=bytes(
                        _PUMP_DEFAULT_QUIET
                        if pump_mode == _PumpMode.QUIET
                        else _PUMP_DEFAULT_EXTREME
                    ),
                ),
            ]
        )

        LOGGER.info("setting pump mode to %s", pump_mode.name.lower())
