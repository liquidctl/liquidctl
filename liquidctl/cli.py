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
  -m, --match <substring>        Filter devices by description substring
  -n, --pick <number>            Pick among many results for a given filter
  --vendor <id>                  Filter devices by hexadecimal vendor ID
  --product <id>                 Filter devices by hexadecimal product ID
  --release <number>             Filter devices by hexadecimal release number
  --serial <number>              Filter devices by serial number
  --bus <bus>                    Filter devices by bus
  --address <address>            Filter devices by address in bus
  --usb-port <port>              Filter devices by USB port in bus
  -d, --device <id>              Select device by listing id

Animation options (devices/modes can support zero or more):
  --speed <value>                Abstract animation speed (device/mode specific)
  --time-per-color <value>       Time to wait on each color (seconds)
  --time-off <value>             Time to wait with the LED turned off (seconds)
  --alert-threshold <number>     Threshold temperature for a visual alert (°C)
  --alert-color <color>          Color used by the visual high temperature alert
  --direction <string>           If the pattern should move forward or backwards. [default: forward]
  --start-led <number>           The first led to start the effect at
  --maximum-leds <number>        The number of LED's the effect should apply to

Other device options:
  --single-12v-ocp               Enable single rail +12V OCP
  --pump-mode <mode>             Set the pump mode (certain Corsair coolers)
  --temperature-sensor <number>  The temperature sensor number for the Commander Pro
  --legacy-690lc                 Use Asetek 690LC in legacy mode (old Krakens)
  --non-volatile                 Store on non-volatile controller memory
  --unsafe <features>            Comma-separated bleeding-edge features to enable

Other interface options:
  -v, --verbose                  Output additional information
  -g, --debug                    Show debug information on stderr
  --version                      Display the version number
  --help                         Show this message

Deprecated:
  --hid <ignored>                Deprecated

Copyright (C) 2018–2021  Jonas Malaco, Marshall Asch, CaseySJ, Tom Frey and
contributors

liquidctl incorporates work by leaty, Ksenija Stanojevic, Alexander Tong, Jens
Neumaier, Kristóf Jakab, Sean Nelson, Chris Griffith, notaz, realies and Thomas
Pircher.

SPDX-License-Identifier: GPL-3.0-or-later

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.
"""

import datetime
import errno
import inspect
import logging
import os
import sys
from traceback import format_exception

from docopt import docopt

from liquidctl.driver import *
from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver, UnsafeFeaturesNotEnabled
from liquidctl.util import color_from_str
from liquidctl.version import __version__


# conversion from CLI arg to internal option; as options as forwarded to bused
# and drivers, they must:
#  - have no default value in the CLI level (not forwarded unless explicitly set);
#  - and avoid unintentional conflicts with target function arguments
_PARSE_ARG = {
    '--vendor': lambda x: int(x, 16),
    '--product': lambda x: int(x, 16),
    '--release': lambda x: int(x, 16),
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
    '--temperature-sensor': int,
    '--direction': str,
    '--start-led': int,
    '--maximum-leds': int,

    '--single-12v-ocp': bool,
    '--pump-mode': str,
    '--legacy-690lc': bool,
    '--non-volatile': bool,
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
    'match',
    'pick',
    # --device generates no option
]

# custom number formats for values of select units
_VALUE_FORMATS = {
    '°C': '.1f',
    'rpm': '.0f',
    'V': '.2f',
    'A': '.2f',
    'W': '.2f'
}

_LOGGER = logging.getLogger(__name__)


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

        if dev.vendor_id:
            print(f'├── Vendor ID: {dev.vendor_id:#06x}')
        if dev.product_id:
            print(f'├── Product ID: {dev.product_id:#06x}')
        if dev.release_number:
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
                _LOGGER.exception(msg.capitalize())
            else:
                warnings.append(msg)

        print(f'├── Bus: {dev.bus}')
        print(f'├── Address: {dev.address}')
        if dev.port:
            port = '.'.join(map(str, dev.port))
            print(f'├── Port: {port}')

        print(f'└── Driver: {type(dev).__name__}')
        if debug:
            driver_hier = [i.__name__ for i in inspect.getmro(type(dev)) if i != object]
            _LOGGER.debug('hierarchy: %s', ', '.join(driver_hier[1:]))

        for msg in warnings:
            _LOGGER.warning(msg)
        print('')

    assert 'device' not in opts or len(devices) <= 1, 'too many results listed with --device'


def _print_dev_status(dev, status):
    if not status:
        return
    print(dev.description)
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
        _LOGGER.warning('ignoring --hid %s: deprecated option, API will be selected automatically',
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
        return f'liquidctl v{__version__}'
    return f'liquidctl v{__version__} ({"; ".join(extra)})'


def main():
    args = docopt(__doc__)

    if args['--version']:
        print(_gen_version())
        sys.exit(0)

    if args['--debug']:
        args['--verbose'] = True
        logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s: %(message)s')
        _LOGGER.debug('running %s', _gen_version())
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
            _LOGGER.warning('mixing --device <id> with other filters is not recommended; '
                            'to disambiguate between results prefer --pick <result>')
        selected = [compat[device_id]]

    if args['list']:
        _list_devices(selected, using_filters=bool(filter_count), device_id=device_id, **opts)
        return

    if len(selected) > 1 and not (args['status'] or args['all']):
        raise SystemExit('Error: too many devices, filter or select one (see: liquidctl --help)')
    elif len(selected) == 0:
        raise SystemExit('Error: no devices matches available drivers and selection criteria')

    errors = 0

    def log_error(err, msg, append_err=False, *args):
        nonlocal errors
        errors += 1
        _LOGGER.info('%s', err, exc_info=True)
        if append_err:
            exception = list(format_exception(Exception, err, None))[-1].rstrip()
            _LOGGER.error(f'{msg}: {exception}', *args)
        else:
            _LOGGER.error(msg, *args)

    for dev in selected:
        _LOGGER.debug('device: %s', dev.description)
        try:
            with dev.connect(**opts):
                if args['initialize']:
                    _print_dev_status(dev, dev.initialize(**opts))
                elif args['status']:
                    _print_dev_status(dev, dev.get_status(**opts))
                elif args['set'] and args['speed']:
                    _device_set_speed(dev, args, **opts)
                elif args['set'] and args['color']:
                    _device_set_color(dev, args, **opts)
                else:
                    assert False, 'unreachable'
        except OSError as err:
            # each backend API returns a different subtype of OSError (OSError,
            # usb.core.USBError or PermissionError) for permission issues
            if err.errno in [errno.EACCES, errno.EPERM]:
                log_error(err, f'Error: insufficient permissions to access {dev.description}')
            elif err.args == ('open failed', ):
                log_error(err, f'Error: could not open {dev.description}, possibly due to insufficient permissions')
            else:
                log_error(err, f'Unexpected OS error with {dev.description}', append_err=True)
        except NotSupportedByDevice as err:
            log_error(err, f'Error: operation not supported by {dev.description}')
        except NotSupportedByDriver as err:
            log_error(err, f'Error: operation not supported by driver for {dev.description}')
        except UnsafeFeaturesNotEnabled as err:
            features = ','.join(err.args)
            log_error(err, f'Error: missing --unsafe features for {dev.description}: {features!r}')
            _LOGGER.error('More information is provided in the corresponding device guide')
        except Exception as err:
            log_error(err, f'Unexpected error with {dev.description}', append_err=True)

    if errors:
        sys.exit(errors)


def find_all_supported_devices(**opts):
    """Deprecated."""
    _LOGGER.warning('deprecated: use liquidctl.driver.find_liquidctl_devices instead')
    return find_liquidctl_devices(**opts)


if __name__ == '__main__':
    main()
