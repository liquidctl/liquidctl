"""liquidctl – monitor and control liquid coolers and other devices.

Usage:
  liquidctl [options] list
  liquidctl [options] initialize [all]
  liquidctl [options] status
  liquidctl [options] set <channel> speed (<temperature> <percentage>) ...
  liquidctl [options] set <channel> speed <percentage>
  liquidctl [options] set <channel> color <mode> [<color>] ...
  liquidctl --help
  liquidctl --version

Device selection options (see: list -v):
  -m, --match <substring>     Filter devices by description substring
  -n, --pick <number>         Pick among many results for a given filter
  --vendor <id>               Filter devices by vendor id
  --product <id>              Filter devices by product id
  --release <number>          Filter devices by release number
  --serial <number>           Filter devices by serial number
  --bus <bus>                 Filter devices by bus
  --address <address>         Filter devices by address in bus
  --usb-port <port>           Filter devices by USB port in bus
  -d, --device <id>           Select device by listing id

Animation options (devices/modes can support zero or more):
  --speed <value>             Abstract animation speed (device/mode specific)
  --time-per-color <value>    Time to wait on each color (seconds)
  --time-off <value>          Time to wait with the LED turned off (seconds)
  --alert-threshold <number>  Threshold temperature for a visual alert (°C)
  --alert-color <color>       Color used by the visual high temperature alert

Other device options:
  --single-12v-ocp            Enable single rail +12V OCP
  --pump-mode <mode>          Set the pump mode (certain Corsair coolers)
  --legacy-690lc              Use Asetek 690LC in legacy mode (old Krakens)
  --unsafe <features>         Comma-separated bleeding-edge features to enable

Other interface options:
  -v, --verbose               Output additional information
  -g, --debug                 Show debug information on stderr
  --version                   Display the version number
  --help                      Show this message

Deprecated:
  --hid <ignored>             Deprecated

Examples:
  liquidctl list --verbose
  liquidctl initialize all
  liquidctl --match kraken set pump speed 90
  liquidctl --product 0x170e set led color fading 350017 ff2608
  liquidctl status

Copyright (C) 2018–2020  Jonas Malaco, CaseySJ, Tom Frey and contributors

liquidctl incorporates work by leaty, Ksenija Stanojevic, Alexander Tong, Jens
Neumaier, Kristóf Jakab, Sean Nelson, Chris Griffith, notaz, realies and Thomas
Pircher.

SPDX-License-Identifier: GPL-3.0-or-later

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.
"""

import datetime
import inspect
import logging
import os
import sys

from docopt import docopt

from liquidctl.driver import *
from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver
from liquidctl.util import color_from_str
from liquidctl.version import __version__


# conversion from CLI arg to internal option; as options as forwarded to bused
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
    '--match': str,
    '--pick': int,

    '--speed': str,
    '--time-per-color': int,
    '--time-off': int,
    '--alert-threshold': int,
    '--alert-color': color_from_str,

    '--single-12v-ocp': bool,
    '--pump-mode': str,
    '--legacy-690lc': bool,
    '--unsafe': lambda x: x.lower().split(','),
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
    # --device generates no option
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


def _list_devices(devices, using_filters=False, device_id=None, verbose=False, debug=False, **opts):
    for i, dev in enumerate(devices):
        warnings = []

        if not using_filters:
            print(f'Device ID {i}: {dev.description}')
        elif device_id is not None:
            print(f'Device ID {device_id}: {dev.description}')
        else:
            print(f'Result #{i}: {dev.description}')
        if not verbose:
            continue

        print(f'├── Vendor ID: {dev.vendor_id:#06x}')
        print(f'├── Product ID: {dev.product_id:#06x}')
        print(f'├── Release number: {dev.release_number:#06x}')
        try:
            if dev.serial_number:
                print(f'├── Serial number: {dev.serial_number}')
        except:
            msg = 'could not read the serial number'
            if sys.platform.startswith('linux') and os.geteuid:
                msg += ' (requires root privileges)'
            elif sys.platform in ['win32', 'cygwin'] and 'Hid' not in type(dev.device).__name__:
                msg += ' (device possibly requires a kernel driver)'
            if debug:
                LOGGER.exception(msg.capitalize())
            else:
                warnings.append(msg)

        print(f'├── Bus: {dev.bus}')
        print(f'├── Address: {dev.address}')
        if dev.port:
            port = '.'.join(map(str, dev.port))
            print(f'├── Port: {port}')

        print(f'└── Driver: {type(dev).__name__} using module {dev.device.api.__name__}')
        if debug:
            driver_hier = [i.__name__ for i in inspect.getmro(type(dev)) if i != object]
            LOGGER.debug('hierarchy: %s; %s', ', '.join(driver_hier[1:]), type(dev.device).__name__)

        for msg in warnings:
            LOGGER.warning(msg)
        print('')

    assert not 'device' in opts or len(devices) <= 1, 'too many results listed with --device'


def _print_dev_status(dev, status):
    if not status:
        return
    print(f'{dev.description}')
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
    if args['--hid']:
        LOGGER.warning('Ignoring --hid %s: deprecated option, API will be selected automatically',
                       args['--hid'])
    opts = {}
    for arg, val in args.items():
        if val is not None and arg in _PARSE_ARG:
            opt = arg.replace('--', '').replace('-', '_')
            opts[opt] = _PARSE_ARG[arg](val)
    return opts


def _gen_version():
    extra = None
    try:
        from liquidctl.extraversion import __extraversion__
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
        LOGGER.debug('running %s', _gen_version())
    elif args['--verbose']:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
        sys.tracebacklimit = 0

    opts = _make_opts(args)
    filter_count = sum(1 for opt in opts if opt in _FILTER_OPTIONS)
    device_id = None

    if not args['--device']:
        selected = list(find_liquidctl_devices(**opts))
    else:
        device_id = int(args['--device'])
        no_filters = {opt: val for opt, val in opts.items() if opt not in _FILTER_OPTIONS}
        compat = list(find_liquidctl_devices(**no_filters))
        if device_id < 0 or device_id >= len(compat):
            raise SystemExit('Error: device ID out of bounds')
        if filter_count:
            # check that --device matches other filter criteria
            matched_devs = [dev.device for dev in find_liquidctl_devices(**opts)]
            if compat[device_id].device not in matched_devs:
                raise SystemExit('Error: device ID does not match remaining selection criteria')
            LOGGER.warning('mixing --device <id> with other filters is not recommended; '
                           'to disambiguate between results prefer --pick <result>')
        selected = [compat[device_id]]

    if args['list']:
        _list_devices(selected, using_filters=bool(filter_count), device_id=device_id, **opts)
        return

    if len(selected) > 1 and not (args['status'] or args['all']):
        raise SystemExit('Error: too many devices, filter or select one (see: liquidctl --help)')
    elif len(selected) == 0:
        raise SystemExit('Error: no devices matches available drivers and selection criteria')

    for dev in selected:
        LOGGER.debug('device: %s', dev.description)
        dev.connect(**opts)
        try:
            if args['initialize']:
                _print_dev_status(dev, dev.initialize(**opts))
            elif args['status']:
                _print_dev_status(dev, dev.get_status(**opts))
            elif args['set'] and args['speed']:
                _device_set_speed(dev, args, **opts)
            elif args['set'] and args['color']:
                _device_set_color(dev, args, **opts)
            else:
                raise Exception('Not sure what to do')
        except NotSupportedByDevice:
            raise SystemExit(f'Error: operation not supported by {dev.description}')
        except NotSupportedByDriver:
            raise SystemExit(f'Error: operation not supported by driver for {dev.description}')
        except:
            LOGGER.exception('Unexpected error with %s', dev.description)
            sys.exit(1)
        finally:
            dev.disconnect(**opts)


def find_all_supported_devices(**opts):
    """Deprecated."""
    LOGGER.warning('deprecated: use liquidctl.driver.find_liquidctl_devices instead')
    return find_liquidctl_devices(**opts)


if __name__ == '__main__':
    main()
