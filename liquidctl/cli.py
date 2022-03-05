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

Animation options (devices/modes can support zero or more):
  --speed <value>                Abstract animation speed (device/mode specific)
  --time-per-color <value>       Time to wait on each color (seconds)
  --time-off <value>             Time to wait with the LED turned off (seconds)
  --alert-threshold <number>     Threshold temperature for a visual alert (°C)
  --alert-color <color>          Color used by the visual high temperature alert
  --direction <string>           If the pattern should move forward or backward.
  --start-led <number>           The first led to start the effect at
  --maximum-leds <number>        The number of LED's the effect should apply to

Other device options:
  --single-12v-ocp               Enable single rail +12V OCP
  --pump-mode <mode>             Set the pump mode (certain Corsair coolers)
  --temperature-sensor <number>  The temperature sensor number for the Commander Pro
  --legacy-690lc                 Use Asetek 690LC in legacy mode (old Krakens)
  --non-volatile                 Store on non-volatile controller memory
  --direct-access                Directly access the device despite kernel drivers
  --unsafe <features>            Comma-separated bleeding-edge features to enable

Other interface options:
  -v, --verbose                  Output additional information
  -g, --debug                    Show debug information on stderr
  --json                         JSON output (list/initialization/status)
  --version                      Display the version number
  --help                         Show this message

Deprecated:
  -d, --device <index>           Select device by listing index
  --hid <ignored>                Ignored

Copyright (C) 2018–2022  Jonas Malaco, Marshall Asch, CaseySJ, Tom Frey, Andrew
Robertson, ParkerMc and contributors

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
import json
import logging
import os
import platform
import re
import sys
from numbers import Number
from traceback import format_exception

import colorlog
from docopt import docopt

from liquidctl import __version__
from liquidctl.driver import *
from liquidctl.error import NotSupportedByDevice, NotSupportedByDriver, UnsafeFeaturesNotEnabled
from liquidctl.util import color_from_str


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

    '--speed': str.lower,
    '--time-per-color': int,
    '--time-off': int,
    '--alert-threshold': int,
    '--alert-color': color_from_str,
    '--temperature-sensor': int,
    '--direction': str.lower,
    '--start-led': int,
    '--maximum-leds': int,

    '--single-12v-ocp': bool,
    '--pump-mode': str.lower,
    '--legacy-690lc': bool,
    '--non-volatile': bool,
    '--direct-access': bool,
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
    '%': '.0f',
    'A': '.2f',
    'V': '.2f',
    'W': '.2f',
    'rpm': '.0f',
    '°C': '.1f',
}

_LOGGER = logging.getLogger(__name__)


def _list_devices_objs(devices):

    def getattr_or(object, name, default=None):
        """Call `getattr` and return `default` on exceptions."""
        try:
            return getattr(object, name, default)
        except Exception:
            return default

    return [
        {
            # replace the experimental suffix with a proper field
            'description': dev.description.replace(' (experimental)', ''),
            'vendor_id': dev.vendor_id,
            'product_id': dev.product_id,
            'release_number': dev.release_number,
            'serial_number': getattr_or(dev, 'serial_number', None),
            'bus': dev.bus,
            'address': dev.address,
            'port': dev.port,
            'driver': type(dev).__name__,
            'experimental': dev.description.endswith('(experimental)'),
        }
        for dev in devices
    ]


def _list_devices_human(devices, *, using_filters, device_id, verbose, debug, **opts):
    for i, dev in enumerate(devices):
        warnings = []

        if not using_filters:
            print(f'Device #{i}: {dev.description}')
        elif device_id is not None:
            print(f'Device #{device_id}: {dev.description}')
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
            driver_hier = (i.__name__ for i in inspect.getmro(type(dev)))
            _LOGGER.debug('MRO: %s', ', '.join(driver_hier))

        for msg in warnings:
            _LOGGER.warning(msg)
        print('')

    assert 'device' not in opts or len(devices) <= 1, 'too many results listed with --device'


def _dev_status_obj(dev, status):
    # don't suppress devices without status data (typically from initialize)
    if not status:
        status = []

    # convert to types that are more suitable to serialization, when that
    # cannot be done later (e.g. because it requires adjusting the `unit`)
    def convert(i):
        key, val, unit = i
        if isinstance(val, datetime.timedelta):
            val = val.total_seconds()
            unit = 's'
        return { 'key': key, 'value': val, 'unit': unit }

    # suppress the experimental suffix, `list` reports it in `.experimental`
    return {
        'bus': dev.bus,
        'address': dev.address,
        'description': dev.description.replace(' (experimental)', ''),
        'status': [convert(x) for x in status]
    }


def _print_dev_status(dev, status):
    if not status:
        return
    print(dev.description)
    tmp = []
    kcols, vcols = 0, 0
    for k, v, u in status:
        if isinstance(v, datetime.timedelta):
            v = str(v)
        elif isinstance(v, bool):
            v = 'Yes' if v else 'No'
        elif v is None:
            v = 'N/A'
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
    dev.set_color(args['<channel>'].lower(), args['<mode>'].lower(), color, **opts)


def _device_set_speed(dev, args, **opts):
    if len(args['<temperature>']) > 0:
        profile = zip(map(int, args['<temperature>']), map(int, args['<percentage>']))
        dev.set_speed_profile(args['<channel>'].lower(), profile, **opts)
    else:
        dev.set_fixed_speed(args['<channel>'].lower(), int(args['<percentage>'][0]), **opts)


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


def _log_requirements():
    _LOGGER.debug('python: %s', sys.version)
    if sys.hexversion >= 0x03080000:
        from importlib.metadata import distribution, version, PackageNotFoundError

        try:
            dist = distribution('liquidctl')
        except PackageNotFoundError:
            _LOGGER.debug('not installed, package metadata not available')
            return

        for req in dist.requires:
            name = re.search('^[a-zA-Z0-9]([a-zA-Z0-9._-]*)', req).group(0)
            try:
                _LOGGER.debug('%s: %s', name, version(name))
            except Exception as err:
                _LOGGER.debug('%s: version n/a (%s)', name, err)
    else:
        _LOGGER.debug('importlib.metadata not available')


class _ErrorAcc:
    __slots__ = ['_errors']

    def __init__(self):
        self._errors = 0

    def log(self, msg, *args, err=None, show_err=False):
        self._errors += 1
        if err:
            # log the err with traceback before reporting it properly, this time
            # without traceback; this puts error messages are at the bottom of the
            # output, where most users first look for them
            _LOGGER.info('detailed error: %s: %r', msg, err, *args, exc_info=True)

        if show_err and err:
            _LOGGER.error('%s: %r', msg, err, *args)
        else:
            _LOGGER.error(msg, *args)

    def exit_code(self):
        return 0 if self.is_empty() else 1

    def is_empty(self):
        return not bool(self._errors)


def main():
    args = docopt(__doc__)

    if args['--version']:
        print(f'liquidctl v{__version__} ({platform.platform()})')
        sys.exit(0)

    if args['--debug']:
        args['--verbose'] = True
        log_fmt = '%(log_color)s[%(levelname)s] (%(module)s) (%(funcName)s): %(message)s'
        log_level = logging.DEBUG
    elif args['--verbose']:
        log_fmt = '%(log_color)s%(levelname)s: %(message)s'
        log_level = logging.INFO
    else:
        log_fmt = '%(log_color)s%(levelname)s: %(message)s'
        log_level = logging.WARNING
        sys.tracebacklimit = 0

    if sys.platform == 'win32':
        log_colors = {
            'DEBUG': f'bold_blue',
            'INFO': f'bold_purple',
            'WARNING': 'yellow,bold',
            'ERROR': 'red,bold',
            'CRITICAL': 'red,bold,bg_white',
        }
    else:
        log_colors = {
            'DEBUG': f'blue',
            'INFO': f'purple',
            'WARNING': 'yellow,bold',
            'ERROR': 'red,bold',
            'CRITICAL': 'red,bold,bg_white',
        }

    log_fmtter = colorlog.TTYColoredFormatter(fmt=log_fmt, stream=sys.stderr,
                                              log_colors=log_colors)

    log_handler = logging.StreamHandler()
    log_handler.setFormatter(log_fmtter)
    logging.basicConfig(level=log_level, handlers=[log_handler])

    _LOGGER.debug('liquidctl: %s', __version__)
    _LOGGER.debug('platform: %s', platform.platform())
    _log_requirements()

    if __name__ == '__main__':
        _LOGGER.warning('python -m liquidctl.cli is deprecated, prefer python -m liquidctl')

    errors = _ErrorAcc()

    # unlike humans, machines want to know everything; imply verbose everywhere
    # other than when setting default logging level and format (which are
    # inherently for human consumption)
    if args['--json']:
        args['--verbose'] = True

    opts = _make_opts(args)
    opts['_internal_called_from_cli'] = True  # FOR INTERNAL USE ONLY, DO NOT REPLICATE ELSEWHERE
    filter_count = sum(1 for opt in opts if opt in _FILTER_OPTIONS)
    device_id = None

    if not args['--device']:
        selected = list(find_liquidctl_devices(**opts))
    else:
        _LOGGER.warning('-d/--device is deprecated, prefer --match or other selection options')
        device_id = int(args['--device'])
        no_filters = {opt: val for opt, val in opts.items() if opt not in _FILTER_OPTIONS}
        compat = list(find_liquidctl_devices(**no_filters))
        if device_id < 0 or device_id >= len(compat):
            errors.log('device index out of bounds')
            return errors.exit_code()
        if filter_count:
            # check that --device matches other filter criteria
            matched_devs = [dev.device for dev in find_liquidctl_devices(**opts)]
            if compat[device_id].device not in matched_devs:
                errors.log('device index does not match remaining selection criteria')
                return errors.exit_code()
            _LOGGER.warning('mixing --device <id> with other filters is not recommended; '
                            'to disambiguate between results prefer --pick <result>')
        selected = [compat[device_id]]

    if args['list']:
        if args['--json']:
            objs = _list_devices_objs(selected)
            print(json.dumps(objs, ensure_ascii=(os.getenv('LANG', None) == 'C')))
        else:
            _list_devices_human(selected, using_filters=bool(filter_count),
                                device_id=device_id, json=json, **opts)
        return

    if len(selected) > 1 and not (args['status'] or args['all']):
        errors.log('too many devices, filter or select one (see: liquidctl --help)')
        return errors.exit_code()
    elif len(selected) == 0:
        errors.log('no device matches available drivers and selection criteria')
        return errors.exit_code()

    # for json
    obj_buf = []

    for dev in selected:
        _LOGGER.debug('device: %s', dev.description)
        try:
            with dev.connect(**opts):
                if args['initialize']:
                    status = dev.initialize(**opts)
                    if args['--json']:
                        obj_buf.append(_dev_status_obj(dev, status))
                    else:
                        _print_dev_status(dev, status)
                elif args['status']:
                    status = dev.get_status(**opts)
                    if args['--json']:
                        obj_buf.append(_dev_status_obj(dev, status))
                    else:
                        _print_dev_status(dev, status)
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
                errors.log(f'insufficient permissions to access {dev.description}', err=err)
            elif err.args == ('open failed', ):
                errors.log(
                    f'could not open {dev.description}, possibly due to insufficient permissions',
                    err=err
                )
            else:
                errors.log(f'unexpected OS error with {dev.description}', err=err, show_err=True)
        except NotSupportedByDevice as err:
            errors.log(f'operation not supported by {dev.description}', err=err)
        except NotSupportedByDriver as err:
            errors.log(f'operation not supported by driver for {dev.description}', err=err)
        except UnsafeFeaturesNotEnabled as err:
            features = ','.join(err.args)
            errors.log(f'missing --unsafe features for {dev.description}: {features!r}', err=err)
        except Exception as err:
            errors.log(f'unexpected error with {dev.description}', err=err, show_err=True)

    if errors.is_empty() and args['--json']:
        # use __str__ for values that cannot be directly serialized to JSON
        # (e.g. enums)
        print(json.dumps(obj_buf, ensure_ascii=(os.getenv('LANG', None) == 'C'),
                         default=lambda x: str(x)))

    return errors.exit_code()


if __name__ == '__main__':
    sys.exit(main())
