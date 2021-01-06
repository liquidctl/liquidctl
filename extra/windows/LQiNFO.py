#!/usr/bin/env python
"""LQiNFO – export monitoring data from liquidctl devices to HWiNFO.

This is a experimental script that exports the status of all available
devices to HWiNFO.

Usage:
  LQiNFO.py [options]
  LQiNFO.py --help
  LQiNFO.py --version

Options:
  --interval <seconds>    Update interval in seconds [default: 2]
  --hid <module>          Override API for USB HIDs: usb, hid or hidraw
  --legacy-690lc          Use Asetek 690LC in legacy mode (old Krakens)
  --vendor <id>           Filter devices by vendor id
  --product <id>          Filter devices by product id
  --release <number>      Filter devices by release number
  --serial <number>       Filter devices by serial number
  --bus <bus>             Filter devices by bus
  --address <address>     Filter devices by address in bus
  --usb-port <port>       Filter devices by USB port in bus
  --pick <number>         Pick among many results for a given filter
  -v, --verbose           Output additional information to stderr
  -g, --debug             Show debug information on stderr
  --version               Display the version number
  --help                  Show this message

Examples:
  python LQiNFO.py
  python LQiNFO.py --product 0xb200
  python LQiNFO.py --interval 0.5

Changelog:
  0.0.2  Fix cleanup of registry keys when exiting.
  0.0.1  First proof-of-concept.

---

LQiNFO – export monitoring data from liquidctl devices to HWiNFO.
Copyright (C) 2019–2020  Jonas Malaco

yoda is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

yoda is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import sys
import time
import winreg

import liquidctl.cli as _borrow
import usb

from docopt import docopt
from liquidctl.driver import *

LOGGER = logging.getLogger(__name__)

if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.2')
    frwd = _borrow._make_opts(args)
    devs = list(find_liquidctl_devices(**frwd))
    update_interval = float(args['--interval'])

    if args['--debug']:
        args['--verbose'] = True
        logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s: %(message)s')
    elif args['--verbose']:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(message)s')
        sys.tracebacklimit = 0

    hwinfo_sensor_types = {
        '°C': 'Temp',
        'V': 'Volt',
        'rpm': 'Fan',
        'A': 'Current',
        'W': 'Power',
        'dB': 'Other'
    }
    hwinfo_custom = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\HWiNFO64\Sensors\Custom')
    infos = []

    try:
        for i, d in enumerate(devs):
            LOGGER.info('Initializing %s', d.description)
            d.connect()

            dev_key = winreg.CreateKey(hwinfo_custom, f'{d.description} (liquidctl#{i})')
            dev_values = []
            for j, (k, v, u) in enumerate(d.get_status()):
                hwinfo_type = hwinfo_sensor_types.get(u, None)
                if not hwinfo_type:
                    dev_values.append(None)
                else:
                    sensor_key = winreg.CreateKey(dev_key, f'{hwinfo_type}{j}')
                    winreg.SetValueEx(sensor_key, 'Name', None, winreg.REG_SZ, k)
                    winreg.SetValueEx(sensor_key, 'Unit', None, winreg.REG_SZ, u)
                    winreg.SetValueEx(sensor_key, 'Value', None, winreg.REG_SZ, str(v))
                    dev_values.append(sensor_key)

            infos.append((dev_key, dev_values))
            # set up dev infos and registry
        status = {}
        while True:
            for i, d in enumerate(devs):
                dev_key, dev_values = infos[i]
                try:
                    for j, (k, v, u) in enumerate(d.get_status()):
                        sensor_key = dev_values[j]
                        if sensor_key:
                            winreg.SetValueEx(sensor_key, 'Value', None, winreg.REG_SZ, str(v))
                except usb.core.USBError as err:
                    LOGGER.warning('Failed to read from the device, possibly serving stale data')
                    LOGGER.debug(err, exc_info=True)
            time.sleep(update_interval)
    except KeyboardInterrupt:
        LOGGER.info('Canceled by user')
    except:
        LOGGER.exception('Unexpected error')
        sys.exit(1)
    finally:
        for d in devs:
            try:
                LOGGER.info('Disconnecting from %s', d.description)
                d.disconnect()
            except:
                LOGGER.exception('Unexpected error when disconnecting')
        for dev_key, dev_values in infos:
            try:
                for sensor_key in dev_values:
                    if sensor_key:
                        winreg.DeleteKey(sensor_key, '')
                winreg.DeleteKey(dev_key, '')
            except:
                LOGGER.exception('Unexpected error when cleaning the registry')
