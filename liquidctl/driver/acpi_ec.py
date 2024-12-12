"""liquidctl drivers for ACPI EC based laptops.

Supported devices:

- 14K2EMS1 (MSI Stealth 14 AI Studio A1VFG)

Copyright Kyoken and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import os
import re

from liquidctl.driver.base import BaseBus, BaseDriver, find_all_subclasses
from liquidctl.error import NotSupportedByDevice

_LOGGER = logging.getLogger(__name__)

EC_IO_FILE = '/dev/ec'
LED_TYPES = ('tail', 'mic')


class MsiConfig:
    """
    Base ACPI EC config for MSI devices.

    Config is compatible with ISW (Ice-Sealed Wyvern) project.
    Have some common defaults from MSI_ADDRESS_DEFAULT preset.
    """

    # could be found in: $ sudo hexdump -C /dev/ec
    serial_number = None
    # could be found in: $ sudo dmidecode
    notebook_model = None

    cpu_fan_speed_max = 150
    cpu_fan_speed_min = 0
    gpu_fan_speed_max = 150
    gpu_fan_speed_min = 0

    fan_mode_address = 0xf4
    cooler_boost_address = 0x98
    usb_backlight_address = 0xf7
    battery_charging_threshold_address = 0xef

    # CPU
    cpu_temp_address_0 = 0x6a
    cpu_temp_address_1 = 0x6b
    cpu_temp_address_2 = 0x6c
    cpu_temp_address_3 = 0x6d
    cpu_temp_address_4 = 0x6e
    cpu_temp_address_5 = 0x6f
    cpu_fan_speed_address_0 = 0x72
    cpu_fan_speed_address_1 = 0x73
    cpu_fan_speed_address_2 = 0x74
    cpu_fan_speed_address_3 = 0x75
    cpu_fan_speed_address_4 = 0x76
    cpu_fan_speed_address_5 = 0x77
    cpu_fan_speed_address_6 = 0x78
    realtime_cpu_temp_address = 0x68
    realtime_cpu_fan_speed_address = 0x71
    realtime_cpu_fan_rpm_address = 0xcc

    # GPU
    gpu_temp_address_0 = 0x82
    gpu_temp_address_1 = 0x83
    gpu_temp_address_2 = 0x84
    gpu_temp_address_3 = 0x85
    gpu_temp_address_4 = 0x86
    gpu_temp_address_5 = 0x87
    gpu_fan_speed_address_0 = 0x8a
    gpu_fan_speed_address_1 = 0x8b
    gpu_fan_speed_address_2 = 0x8c
    gpu_fan_speed_address_3 = 0x8d
    gpu_fan_speed_address_4 = 0x8e
    gpu_fan_speed_address_5 = 0x8f
    gpu_fan_speed_address_6 = 0x90
    realtime_gpu_temp_address = 0x80
    realtime_gpu_fan_speed_address = 0x89
    realtime_gpu_fan_rpm_address = 0xca


class MSI_14K2EMS1(MsiConfig):
    serial_number = '14K2EMS1'
    notebook_model = 'MSI Stealth 14 AI Studio A1VFG'

    profile_address = 0xd2
    profile_balanced = 0xc1
    profile_performance = 0xc4

    fan_mode_address = 0xd4
    fan_mode_auto = 0x0d
    fan_mode_basic = 0x1d
    fan_mode_advanced = 0x8d

    mux_switch_address = 0x2e
    mux_mshybrid = 0x0b
    mux_discrete = 0x4b

    cooler_boost_address = 152
    cooler_boost_off = 0
    cooler_boost_on = 128

    tail_light_address = 0x2c
    tail_light_mask = 0x10

    mic_light_address = 0x2c
    mic_light_mask = 0x02

    cpu_fan_speed_address_0 = 0x72
    cpu_fan_speed_address_1 = 0x73
    cpu_fan_speed_address_2 = 0x74
    cpu_fan_speed_address_3 = 0x75
    cpu_fan_speed_address_4 = 0x76
    cpu_fan_speed_address_5 = 0x77
    cpu_fan_speed_address_6 = None

    realtime_cpu_temp_address = 0x68
    realtime_cpu_fan_rpm_address = 0xc8

    gpu_fan_speed_address_0 = 0x8a
    gpu_fan_speed_address_1 = 0x8b
    gpu_fan_speed_address_2 = 0x8c
    gpu_fan_speed_address_3 = 0x8d
    gpu_fan_speed_address_4 = 0x8e
    gpu_fan_speed_address_5 = 0x8f
    gpu_fan_speed_address_6 = None

    realtime_gpu_temp_address = 0x9e
    realtime_gpu_fan_rpm_address = 0xca


class AcpiEcDriver(BaseDriver):
    """Base driver class for ACPI EC devices."""

    vendor_id = 0
    product_id = 0
    bus = 'ACPI EC'
    port = None

    def __init__(self, device_path) -> None:
        self._device_path = device_path

    def connect(self, **kwargs):
        return self

    def disconnect(self, **kwargs):
        pass

    def initialize(self, **kwargs):
        pass

    def _write(self, address: int, value: int) -> bytes:
        with open(self._device_path, 'r+b') as f:
            f.seek(address)
            f.write(bytes((value,)))

    def _read(self, address: int, size: int = 1) -> bytes:
        with open(self._device_path, 'r+b') as f:
            f.seek(address)
            return f.read(size)

    def _sync(self) -> None:
        pass


class CachedAcpiEcDriver(AcpiEcDriver):
    def __init__(self, device_path) -> None:
        super().__init__(device_path)
        self._sync()

    def _sync(self) -> None:
        self._data = None

    def _read(self, address: int, size: int = 1) -> bytes:
        if self._data is None:
            with open(self._device_path, 'r+b') as f:
                self._data = f.read()

        return self._data[address:address + size]

    def _write(self, address: int, value: int) -> bytes:
        if self._read(address)[0] == value:
            return

        if self._data is not None:
            data = list(self._data)
            data[address] = value
            self._data = bytes(data)

        super()._write(address, value)


class MsiAcpiEc(CachedAcpiEcDriver):
    """Driver class for ACPI EC compatible MSI devices."""

    def __init__(self, device_path) -> None:
        super().__init__(device_path)

        self._config = MsiConfig
        sn = self.serial_number
        configs = sorted(find_all_subclasses(self._config), key=lambda x: x.__name__)
        for config in configs:
            if sn == config.serial_number:
                self._config = config

    def _get_option_address(self, name) -> int:
        if not hasattr(self._config, name):
            raise NotSupportedByDevice

        address = getattr(self._config, name)
        if address is None:
            raise NotSupportedByDevice

        return address

    def _get_option(self, name: str, size: int = 1) -> bytes:
        return self._read(self._get_option_address(name), size=size)

    def _set_option(self, name: str, value: int) -> None:
        self._write(self._get_option_address(name), value)

    def _set_duty(self, name: str, duty: int) -> None:
        pu, *_ = name.split('_')
        duty_percent = duty / 100
        duty_min = getattr(self._config, f'{pu}_fan_speed_min')
        duty_max = getattr(self._config, f'{pu}_fan_speed_max')
        duty_raw = int(duty_min * (1 - duty_percent) + duty_max * duty_percent)
        self._set_option(name, duty_raw)

    @classmethod
    def probe(cls, device_path):
        with open(device_path, 'r+b') as f:
            f.seek(0xa0 + 5)
            value = f.read(3).decode()
            if value == 'MS1':
                yield cls(device_path)

    @property
    def serial_number(self) -> str:
        return self._read(0xa0, 8).decode()

    @property
    def release_number(self) -> str:
        return int(self._read(0xa0 + 9, 3).decode())

    @property
    def description(self):
        return self._config.notebook_model

    @property
    def address(self):
        return self._device_path

    def _get_temp(self, pu: str) -> int:
        return self._get_option(f'realtime_{pu}_temp_address')[0]

    def _get_fan_speed(self, pu: str) -> int:
        value = int(self._get_option(f'realtime_{pu}_fan_rpm_address', 2).hex(), 16)
        if value:
            return 478000 // value
        return value

    def _get_fan_duty(self, pu: str, index: int) -> int:
        value = self._get_option(f'{pu}_fan_speed_address_{index}')[0]
        duty_min = getattr(self._config, f'{pu}_fan_speed_min')
        duty_max = getattr(self._config, f'{pu}_fan_speed_max')
        duty_range = duty_max - duty_min
        return int((value - duty_min) / duty_range * 100)

    def _get_color(self, channel: str) -> int:
        value = self._get_option(f'{channel}_light_address')[0]
        mask = getattr(self._config, f'{channel}_light_mask')
        if value & mask == mask:
            return 'on'
        else:
            return 'off'

    def set_fixed_speed(self, channel, duty, **kwargs):
        if (m := re.match(r'^(?P<pu>(cpu|gpu)) fan( duty)$', channel.lower())):
            # set flat profile, same value for the all steps
            pu = m.group('pu')
            step = 0
            while True:
                try:
                    self._set_duty(f'{pu}_fan_speed_address_{step}', duty)
                except NotSupportedByDevice:
                    break
                step += 1

        elif (m := re.match(r'^(?P<pu>(cpu|gpu)) fan( duty)? step (?P<step>\d)$', channel.lower())):
            # set single step value
            pu = m.group('pu')
            step = int(m.group('step')) - 1
            self._set_duty(f'{pu}_fan_speed_address_{step}', duty)

    def set_speed_profile(self, channel, profile, **kwargs):
        pu, *_ = channel.lower().split(' ')

        for step, (temp, duty) in enumerate(profile):
            try:
                self._set_duty(f'{pu}_fan_speed_address_{step}', duty)
            except NotSupportedByDevice:
                break

    def set_color(self, channel, mode, *args, **kwargs):
        led, *_ = channel.lower().split(' ')
        value = self._get_option(f'{led}_light_address')[0]
        mask = getattr(self._config, f'{led}_light_mask')
        if mode == 'on':
            value |= mask
        elif mode == 'off':
            value ^= mask
        self._set_option(f'{led}_light_address', value)

    def get_status(self, **kwargs):
        ret = []

        for led in LED_TYPES:
            try:
                ret.append((f'{led} light', self._get_color(led), ''))
            except NotSupportedByDevice:
                pass

        for pu in ('cpu', 'gpu'):
            ret += [
                (f'{pu} temp', self._get_temp(pu.lower()), '°C'),
                (f'{pu} fan speed', self._get_fan_speed(pu.lower()), 'rpm'),
                (f'{pu} fan duty', self._get_fan_duty(pu.lower(), 0), '%'),
            ]

            step = 0
            while True:
                try:
                    ret += [
                        (f'{pu} fan duty step {step + 1}', self._get_fan_duty(pu.lower(), step), '%'),
                    ]
                except NotSupportedByDevice:
                    break
                step += 1

        self._sync()
        return ret


class AcpiEcBus(BaseBus):
    """ACPI EC bus API."""

    def find_devices(self, **kwargs):
        """Find compatible devices and yield corresponding driver instances."""
        drivers = sorted(find_all_subclasses(AcpiEcDriver), key=lambda x: x.__name__)
        for device_path in (EC_IO_FILE,):
            if os.path.exists(device_path):
                for driver in drivers:
                    if hasattr(driver, 'probe'):
                        yield from driver.probe(device_path)
