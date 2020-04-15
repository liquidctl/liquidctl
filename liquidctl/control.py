"""Dynamically monitor and control liquidctl devices.

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
from collections import namedtuple

import usb

import liquidctl.elevate


LOGGER = logging.getLogger(__name__)


class _Feature(object):
    def __init__(self, name):
        self.name = name
    def init_device(self, dev, **opts):
        return None
    def update_device(self, dev, feat_infos, status):
        pass
    def deinit_device(self, dev, feat_infos):
        pass
    def post_init(self):
        pass


class DummyExport(_Feature):
    def init_device(self, dev, **opts):
        LOGGER.info(f'{self.name}: initializing {dev.description}')
        return None
    def update_device(self, dev, feat_infos, status):
        LOGGER.info(f'{self.name}: updating {dev.description} with {status}')
    def deinit_device(self, dev, feat_infos):
        LOGGER.info(f'{self.name}: de-initializing {dev.description}')
    def post_init(self):
        LOGGER.info(f'{self.name}: running post initialization code')


_feat_info = namedtuple('_feat_info', ['feat', 'feat_info'])
_dev_info = namedtuple('_dev_info', ['dev', 'feat_infos'])


def _restart_hwinfo():
    import psutil

    def find_hwinfo_process():
        for p in psutil.process_iter(['name']):
            if p.info['name'].lower().startswith('hwinfo'):
                return p
        return None

    cmdline = r'C:\Program Files\HWiNFO64\HWiNFO64.exe'
    curr = find_hwinfo_process()
    if curr:
        LOGGER.info('HWiNFO already open, restarting')
        cmdline = curr.cmdline()
        curr.terminate()
        curr.wait()
    LOGGER.debug('cmdline: %s', cmdline)
    psutil.Popen(cmdline)


if sys.platform == 'win32':
    import winreg

    _hwinfo_sensor_type = namedtuple('_hwinfo_sensor_type', ['prefix', 'format'])
    _HWINFO_FLOAT = (winreg.REG_SZ, str)
    _HWINFO_INT = (winreg.REG_DWORD, round)
    _HWINFO_SENSOR_TYPES = {
        '°C': _hwinfo_sensor_type('Temp', _HWINFO_FLOAT),
        'rpm': _hwinfo_sensor_type('Fan', _HWINFO_INT),
        'V': _hwinfo_sensor_type('Volt', _HWINFO_FLOAT),
        'A': _hwinfo_sensor_type('Current', _HWINFO_FLOAT),
        'W': _hwinfo_sensor_type('Power', _HWINFO_FLOAT),
        '%': _hwinfo_sensor_type('Usage', _HWINFO_INT),
        'dB': _hwinfo_sensor_type('Other', _HWINFO_INT),
    }

    _hwinfo_sensor = namedtuple('_hwinfo_sensor', ['key', 'format'])
    _hwinfo_device = namedtuple('_hwinfo_device', ['key', 'sensors'])

    def _hwinfo_update_value(sensor, value):
        regtype, regwrite = sensor.format
        winreg.SetValueEx(sensor.key, 'Value', None, regtype, regwrite(value))

    class HWiNFO(_Feature):
        def __init__(self):
            super().__init__('HWiNFO')

        def init_device(self, dev, **opts):
            _HWINFO_BASE_KEY = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\HWiNFO64\Sensors\Custom')
            dev_key = winreg.CreateKey(_HWINFO_BASE_KEY, f'{dev.description} ({dev.bus}:{dev.address.__hash__()})')
            sensors = {}
            counts = {unit: 0 for unit in _HWINFO_SENSOR_TYPES.keys()}
            for k, v, u in dev.get_status(**opts):
                sensor_type = _HWINFO_SENSOR_TYPES.get(u, None)
                if not sensor_type:
                    continue
                type_count = counts[u]
                counts[u] += 1
                sensor_key = winreg.CreateKey(dev_key, f'{sensor_type.prefix}{type_count}')
                winreg.SetValueEx(sensor_key, 'Name', None, winreg.REG_SZ, k)
                winreg.SetValueEx(sensor_key, 'Unit', None, winreg.REG_SZ, u)
                sensor = _hwinfo_sensor(sensor_key, sensor_type.format)
                _hwinfo_update_value(sensor, v)
                sensors[k] = sensor
            return _hwinfo_device(dev_key, sensors)

        def update_device(self, dev, feat_infos, status):
            for k, v, u in status:
                sensor = feat_infos.sensors.get(k)
                if not sensor:
                    continue
                _hwinfo_update_value(sensor, v)

        def deinit_device(self, dev, feat_infos):
            for sensor in feat_infos.sensors.values():
                winreg.DeleteKey(sensor.key, '')
            winreg.DeleteKey(feat_infos.key, '')

        def post_init(self):
            LOGGER.info('Starting HWiNFO')
            liquidctl.elevate.call(_restart_hwinfo, [])

else:
    class HWiNFO(_Feature):
        def __init__(self):
            raise NotImplementedError('HWiNFO not supported on this platform')

def _run_loop(devices, features, update_interval=None, opts=None):
    dev_infos = []
    for dev in devices:
        LOGGER.info('Preparing %s', dev.description)
        dev.connect(**opts)
        feat_infos = []
        for feat in features:
            feat_infos.append(_feat_info(feat, feat.init_device(dev, **opts)))
        dev_infos.append(_dev_info(dev, feat_infos))
    for feat in features:
        feat.post_init()
    try:
        while True:
            for dev, feat_infos in dev_infos:
                try:
                    status = dev.get_status(**opts)
                except usb.core.USBError as err:
                    LOGGER.warning('Failed to read from %s, continuing with stale data',
                                   dev.description)
                    LOGGER.debug(err, exc_info=True)
                for feat, feat_info in feat_infos:
                    feat.update_device(dev, feat_info, status)
            time.sleep(update_interval)
    except KeyboardInterrupt:
        LOGGER.info('Canceled by user')
    except:
        LOGGER.exception('Unexpected error')
        sys.exit(1)
    finally:
        for dev, feat_infos in dev_infos:
            try:
                for feat, feat_info in feat_infos:
                    feat.deinit_device(dev, feat_info)
                dev.disconnect(**opts)
            except:
                LOGGER.exception('Unexpected error when cleaning up %s', dev.description)


def control(devices, features, update_interval, opts):
    if not devices:
        return
    _run_loop(devices, features, update_interval=update_interval, opts=opts)
