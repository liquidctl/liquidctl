"""liquidctl – monitor and control liquid coolers and other devices

Usage:
  liquidctl [options] status
  liquidctl [options] set <channel> speed (<temperature> <percentage>) ...
  liquidctl [options] set <channel> speed <percentage>
  liquidctl [options] set <channel> color <mode> [<color>] ...
  liquidctl [options] initialize
  liquidctl [options] list
  liquidctl --help
  liquidctl --version

Device selection options (see: list -v):
  --vendor <id>               Filter devices by vendor id
  --product <id>              Filter devices by product id
  --release <number>          Filter devices by release number
  --serial <number>           Filter devices by serial number
  --bus <bus>                 Filter devices by bus
  --address <address>         Filter devices by address in bus
  --usb-port <port>           Filter devices by USB port in bus
  --pick <number>             Pick among many results for a given filter
  -d, --device <id>           Select device by listing id

Animation options (devices/modes can support zero or more):
  --speed <value>             Abstract animation speed (device/mode specific)
  --time-per-color <value>    Time to wait on each color (seconds)
  --time-off <value>          Time to wait with the LED turned off (seconds)
  --alert-threshold <number>  Threshold temperature for a visual alert (°C)
  --alert-color <color>       Color used by the visual high temperature alert

Other options:
  -v, --verbose               Output additional information
  -g, --debug                 Show debug information on stderr
  --hid <module>              Override API for USB HIDs: usb, hid or hidraw
  --legacy-690lc              Use Asetek 690LC in legacy mode (old Krakens)
  --single-12v-ocp            Enable single rail +12V OCP
  --version                   Display the version number
  --help                      Show this message

Examples:
  liquidctl status
  liquidctl set pump speed 90
  liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
  liquidctl set ring color fading 350017 ff2608
  liquidctl set logo color fixed af5a2f

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

Copyright (C) 2018–2019  Jonas Malaco
Copyright (C) 2018–2019  each contribution's author

Incorporates work by leaty, KsenijaS, Alexander Tong, Jens Neumaier, Kristóf
Jakab, Sean Nelson, Chris Griffith, notaz and realies, under the terms of the
GNU General Public License.  Depending on how it was packaged, this program
might also bundle copies of hidapi, libusb, cython-hidapi, pyusb, docopt and
appdirs.

You should have received a copy of all applicable licenses along with this
program, in a file called LICENSE.txt.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.
"""

import datetime
import inspect
import itertools
import logging
import sys

from docopt import docopt

from liquidctl.driver import *
from liquidctl.util import color_from_str
from liquidctl.version import __version__


# convertion from CLI arg to internal option; as options as forwarded to bused
# and drivers, they must:
#  - have no default value in the CLI level (not forwarded unless explicitly set);
#  - and avoid unintentional conflicts with target function arguments
_PARSE_ARG = {
    '--vendor': lambda x: int(x, 0),
    '--product': lambda x: int(x, 0),
    '--release': lambda x: int(x, 0),
    '--serial': str,
    '--bus': str,
    '--address': str,
    '--usb-port': lambda x: tuple(map(int, x.split('.'))),
    '--pick': int,
    '--device': int,

    '--speed': str,
    '--time-per-color': int,
    '--time-off': int,
    '--alert-threshold': int,
    '--alert-color': color_from_str,

    '--hid': str,
    '--legacy-690lc': bool,
    '--single-12v-ocp': bool,
    '--verbose': bool,
    '--debug': bool,
}

# options that cause liquidctl.driver.find_liquidctl_devices to ommit devices
_FILTER_OPTIONS = [
    'vendor',
    'product',
    'release',
    'serial',
    'bus',
    'address',
    'usb-port',
    'pick',
    'device'
]

# custom number formats for values of select units
_VALUE_FORMATS = {
    '°C' : '.1f',
    'rpm' : '.0f',
    'V' : '.2f',
    'A' : '.2f',
    'W' : '.2f'
}

LOGGER = logging.getLogger(__name__)


def _list_devices(devices, filtred=False, verbose=False, debug=False, **opts):
    for i, dev in enumerate(devices):
        if not filtred:
            print(f'Device ID {i}: {dev.description}')
        elif 'device' in opts:
            print(f'Device ID {opts["device"]}: {dev.description}')
        else:
            print(f'Result #{i}: {dev.description}')
        if not verbose:
            continue

        print(f'├── Vendor ID: {dev.vendor_id:#06x}')
        print(f'├── Product ID: {dev.product_id:#06x}')
        print(f'├── Release number: {dev.release_number:#06x}')
        if dev.serial_number:
            print(f'├── Serial number: {dev.serial_number}'.format(dev.serial_number))
        if dev.bus:
            print(f'├── Bus: {dev.bus}'.format(dev.bus))
        if dev.address:
            print(f'├── Address: {dev.address}'.format(dev.address))
        if dev.port:
            port = '.'.join(map(str, dev.port))
            print(f'├── Port: {port}')
        print(f'└── Driver: {type(dev).__name__} using module {dev.device.api.__name__}')
        if debug:
            driver_hier = [i.__name__ for i in inspect.getmro(type(dev)) if i != object]
            LOGGER.debug('hierarchy: %s; %s', ', '.join(driver_hier[1:]), type(dev.device).__name__)
        print('')
    assert not 'device' in opts or len(devices) == 1, 'too many results listed with --device'


def _device_get_status(dev, **opts):
    print(dev.description)
    dev.connect(**opts)
    try:
        status = dev.get_status(**opts)
        tmp = []
        kcols, vcols = 0, 0
        for k, v, u in status:
            if isinstance(v, datetime.timedelta):
                v = str(v)
                u = ''
            else:
                valfmt = _VALUE_FORMATS.get(u, '')
                v = f'{v:{valfmt}}'
            kcols = max(kcols, len(k))
            vcols = max(vcols, len(v))
            tmp.append((k, v, u))
        for k, v, u in tmp[:-1]:
            print(f'├── {k:<{kcols}}    {v:>{vcols}}  {u}')
        k, v, u = tmp[-1]
        print(f'└── {k:<{kcols}}    {v:>{vcols}}  {u}')
    except:
        LOGGER.exception('Unexpected error')
        sys.exit(1)
    finally:
        dev.disconnect(**opts)
    print('')


def _device_set_color(dev, args, **opts):
    color = map(color_from_str, args['<color>'])
    dev.set_color(args['<channel>'], args['<mode>'], color, **opts)


def _device_set_speed(dev, args, **opts):
    if len(args['<temperature>']) > 0:
        profile = zip(map(int, args['<temperature>']), map(int, args['<percentage>']))
        dev.set_speed_profile(args['<channel>'], profile, **opts)
    else:
        dev.set_fixed_speed(args['<channel>'], int(args['<percentage>'][0]), **opts)


def _make_opts(args):
    opts = {}
    for arg, val in args.items():
        if not val is None and arg in _PARSE_ARG:
            opt = arg.replace('--', '').replace('-', '_')
            opts[opt] = _PARSE_ARG[arg](val)
    return opts


def _gen_version():
    extra = None
    try:
        from liquidctl.extraversion import __extraversion__
        if not __extraversion__:
            raise ValueError()
        if __extraversion__['editable']:
            extra = ['editable']
        elif __extraversion__['dist_name'] and __extraversion__['dist_package']:
            extra = [__extraversion__['dist_name'], __extraversion__['dist_package']]
        else:
            extra = [__extraversion__['commit'][:12]]
            if __extraversion__['dirty']:
                extra[0] += '-dirty'
    except:
        return 'liquidctl v{}'.format(__version__)
    return 'liquidctl v{} ({})'.format(__version__, '; '.join(extra))


def main():
    args = docopt(__doc__)

    if args['--version']:
        print(_gen_version())
        sys.exit(0)

    if args['--debug']:
        args['--verbose'] = True
        logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s: %(message)s')
        LOGGER.debug(_gen_version())
    elif args['--verbose']:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
        sys.tracebacklimit = 0

    opts = _make_opts(args)

    if not 'device' in opts:
        selected = list(find_liquidctl_devices(**opts))
    else:
        no_filters = {opt: val for opt, val in opts.items() if opt not in _FILTER_OPTIONS}
        compat = list(find_liquidctl_devices(**no_filters))
        selected = [compat[opts['device']]]

    if args['list']:
        filtred = sum(1 for opt in opts if opt in _FILTER_OPTIONS) > 0
        _list_devices(selected, filtred=filtred, **opts)
        return
    if args['status']:
        for dev in selected:
            _device_get_status(dev, **opts)
        return

    if len(selected) > 1:
        raise SystemExit('Too many devices, filter or select one (see: liquidctl --help)')
    elif len(selected) == 0:
        raise SystemExit('No devices matches available drivers and selection criteria')
    dev = selected[0]

    dev.connect(**opts)
    try:
        if args['initialize']:
            dev.initialize(**opts)
        elif args['set'] and args['speed']:
            _device_set_speed(dev, args, **opts)
        elif args['set'] and args['color']:
            _device_set_color(dev, args, **opts)
        else:
            raise Exception('Not sure what to do')
    except:
        LOGGER.exception('Unexpected error')
        sys.exit(1)
    finally:
        dev.disconnect(**opts)


def find_all_supported_devices(**opts):
    """Deprecated."""
    LOGGER.warning('deprecated: use liquidctl.driver.find_liquidctl_devices instead')
    return find_liquidctl_devices(**opts)


if __name__ == '__main__':
    main()

