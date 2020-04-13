"""Export monitoring data from liquidctl devices to other software.

Copyright (C) 2020–2020  Jonas Malaco
Copyright (C) 2020–2020  each contribution's author

This file is part of liquidctl.

liquidctl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

liquidctl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import sys
import time

if sys.platform == 'win32':
    import winreg

from collections import namedtuple

import usb


LOGGER = logging.getLogger(__name__)

_HWINFO_SENSOR_TYPES = {
    '°C': 'Temp',
    'rpm': 'Fan',
    'V': 'Volt',
    'A': 'Current',
    'W': 'Power',
    'dB': 'Other'
}
_hwinfo_devinfos = namedtuple('_hwinfo_devinfos', ['dev_key', 'sensor_keys'])

_export_infos = namedtuple('_export_infos', ['dev', 'devinfos'])


def _hwinfo_update_value(sensor_key, value):
    winreg.SetValueEx(sensor_key, 'Value', None, winreg.REG_SZ, str(value))


def _hwinfo_init(dev, **opts):
    _HWINFO_BASE_KEY = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\HWiNFO64\Sensors\Custom')
    dev_key = winreg.CreateKey(_HWINFO_BASE_KEY, f'{dev.description} ({dev.bus}:{dev.address.__hash__()})')
    sensor_keys = {}
    counts = {prefix: 0 for unit, prefix in _HWINFO_SENSOR_TYPES.items()}
    for k, v, u in dev.get_status(**opts):
        hwinfo_type = _HWINFO_SENSOR_TYPES.get(u, None)
        if not hwinfo_type:
            continue
        type_count = counts[hwinfo_type]
        sensor_key = winreg.CreateKey(dev_key, f'{hwinfo_type}{type_count}')
        counts[hwinfo_type] += 1
        winreg.SetValueEx(sensor_key, 'Name', None, winreg.REG_SZ, k)
        winreg.SetValueEx(sensor_key, 'Unit', None, winreg.REG_SZ, u)
        _hwinfo_update_value(sensor_key, v)
        sensor_keys[k] = sensor_key
    return _hwinfo_devinfos(dev_key, sensor_keys)


def _hwinfo_update(dev, devinfos, status):
    for k, v, u in status:
        sensor_key = devinfos.sensor_keys.get(k)
        if not sensor_key:
            continue
        _hwinfo_update_value(sensor_key, v)


def _hwinfo_deinit(dev, devinfos):
    for sensor_key in devinfos.sensor_keys.values():
        winreg.DeleteKey(sensor_key, '')
    winreg.DeleteKey(devinfos.dev_key, '')


def _export_loop(devices, init, update, deinit, update_interval, **opts):
    infos = []
    for dev in devices:
        LOGGER.info('Preparing %s', dev.description)
        dev.connect(**opts)
        devinfos = init(dev, **opts)
        infos.append(_export_infos(dev, devinfos))
    try:
        while True:
            for dev, devinfos in infos:
                try:
                    status = dev.get_status(**opts)
                except usb.core.USBError as err:
                    LOGGER.warning('Failed to read from %s, continuing with stale data',
                                   dev.description)
                    LOGGER.debug(err, exc_info=True)
                update(dev, devinfos, status)
            time.sleep(update_interval)
    except KeyboardInterrupt:
        LOGGER.info('Canceled by user')
    except:
        LOGGER.exception('Unexpected error')
        sys.exit(1)
    finally:
        for dev, devinfos in infos:
            try:
                dev.disconnect(**opts)
                deinit(dev, devinfos)
            except:
                LOGGER.exception('Unexpected error when cleaning up %s', dev.description)


def run(devices, args, **opts):
    update_interval = float(args['--update-interval'] or '2')
    if args['hwinfo']:
        if sys.platform != 'win32':
            raise ValueError('HWiNFO not supported on this platform')
        _export_loop(devices, _hwinfo_init, _hwinfo_update, _hwinfo_deinit, update_interval, **opts)
    else:
        raise Exception('Not sure what to do')