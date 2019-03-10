"""liquidctl – liquid cooler control

Usage:
  liquidctl [options] status
  liquidctl [options] set <channel> speed (<temperature> <percentage>) ...
  liquidctl [options] set <channel> speed <percentage>
  liquidctl [options] set <channel> color <mode> [<color>] ...
  liquidctl [options] initialize
  liquidctl [options] list
  liquidctl --help
  liquidctl --version

Device selection options:
  -d, --device <no>         Select device by listing number (see: list)
  --vendor <id>             Filter devices by vendor id
  --product <id>            Filter devices by product id
  --release <no>            Filter devices by release number
  --serial <serial>         Filter devices by serial number
  --bus <bus>               Filter devices by bus
  --address <no>            Filter devices by address
  --usb-port <port>         Filter devices by USB port

Other options:
  --speed <value>           Animation speed
  -v, --verbose             Output additional information
  -g, --debug               Show debug information on stderr
  --hid <module>            Force a specific API for USB HIDs
  --version                 Display the version number
  --help                    Show this message

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

Incorporates work by leaty, KsenijaS, Alexander Tong and Jens Neumaier, under
the terms of the GNU General Public License.  Depending on how it was packaged,
this program might also bundle copies of docopt, libusb-1.0 and pyusb.

You should have received a copy of all applicable licenses along with this
program, in a file called LICENSE.txt.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.
"""

import inspect
import itertools
import logging
import sys

from docopt import docopt

import liquidctl.driver.kraken_two
import liquidctl.driver.nzxt_smart_device
import liquidctl.driver.usb
import liquidctl.util
from liquidctl.version import __version__


DRIVERS = [
    liquidctl.driver.kraken_two.KrakenTwoDriver,
    liquidctl.driver.nzxt_smart_device.NzxtSmartDeviceDriver,
]


LOGGER = logging.getLogger(__name__)


def find_all_supported_devices(**kwargs):
    res = map(lambda driver: driver.find_supported_devices(**kwargs), DRIVERS)
    return itertools.chain(*res)


def _filter_devices(devices, args):
    if args['--device']:
        return [devices[int(args['--device'])]]
    sel = []
    for i, dev in devices:
        if args['--vendor'] and dev.vendor_id != int(args['--vendor'], 0):
            continue
        if args['--product'] and dev.product_id != int(args['--product'], 0):
            continue
        if args['--release'] and dev.release_number != int(args['--release'], 0):
            continue
        if args['--serial'] and dev.serial_number != args['--serial']:
            continue
        if args['--bus'] and dev.bus != args['--bus']:
            continue
        if args['--address'] and dev.address != int(args['--address'], 0):
            continue
        if (args['--usb-port'] and
            dev.port != tuple(map(int, args['--usb-port'].split('.')))):
            continue
        sel.append((i, dev))
    return sel


def _list_devices(devices, args):
    for i, dev in devices:
        print('Device {}, {}'.format(i, dev.description))
        if not args['--verbose']:
            continue

        # always available
        print('  Vendor: {:#06x}'.format(dev.vendor_id))
        print('  Product: {:#06x}'.format(dev.product_id))

        # optionally available
        if dev.release_number:
            print('  Release number: {:#06x}'.format(dev.release_number))
        if dev.serial_number:
            print('  Serial number: {}'.format(dev.serial_number))
        if dev.bus:
            print('  Bus: {}'.format(dev.bus))
        if dev.address:
            print('  Address: {}'.format(dev.address))
        if dev.port:
            print('  Port: {}'.format('.'.join(map(str, dev.port))))

        driver_hier = [i.__name__ for i in inspect.getmro(type(dev)) if i != object]
        # only applicable to devices built on top of liqudictl.drivers.usb:
        dev_hier = '{}={}'.format(type(dev.device).__name__, dev.device.api.__name__)
        print('  Hierarchy: {}; {}'.format(', '.join(driver_hier), dev_hier))
        print('')


def _device_get_status(dev, num, **kwargs):
    print('Device {}, {}'.format(num, dev.description))
    dev.connect(**kwargs)
    try:
        status = dev.get_status(**kwargs)
        for k, v, u in status:
            print('{:<18}    {:>10}  {:<3}'.format(k, v, u))
    finally:
        dev.disconnect(**kwargs)
    print('')


def _device_set_color(dev, args, **kwargs):
    color = map(lambda c: list(_parse_color(c)), args['<color>'])
    dev.set_color(args['<channel>'], args['<mode>'], color, **kwargs)


def _device_set_speed(dev, args, **kwargs):
    if len(args['<temperature>']) > 0:
        profile = zip(map(int, args['<temperature>']), map(int, args['<percentage>']))
        dev.set_speed_profile(args['<channel>'], profile, **kwargs)
    else:
        dev.set_fixed_speed(args['<channel>'], int(args['<percentage>'][0]), **kwargs)


def _parse_color(color):
    return bytes.fromhex(color)


def _get_options_to_forward(args):
    def opt_to_field(opt):
        return opt.replace('--', '').replace('-', '_')
    # options that can be forwarded must:
    #  - have no default value (thus not being forwarded);
    #  - or avoid untintential conflicts with target function arguments
    whitelist = ['--hid', '--speed']
    return {opt_to_field(i): args[i] for i in whitelist if args[i]}


def main():
    args = docopt(__doc__, version='liquidctl v{}'.format(__version__))

    if args['--debug']:
        args['--verbose'] = True
        logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s: %(message)s')
        import usb  # now to set up the 'usb' logger, otherwise setLevel bellow wont work
        logging.getLogger('usb').setLevel(logging.DEBUG)
        import usb._debug
        usb._debug.enable_tracing(True)
    elif args['--verbose']:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(message)s')
        sys.tracebacklimit = 0

    frwd = _get_options_to_forward(args)

    all_devices = list(enumerate(find_all_supported_devices(**frwd)))
    selected = _filter_devices(all_devices, args)

    if args['list']:
        _list_devices(selected, args)
        return
    if args['status']:
        for i,dev in selected:
            _device_get_status(dev, i, **frwd)
        return

    if len(selected) > 1:
        raise SystemExit('Too many devices, filter or select one (see: liquidctl --help)')
    elif len(selected) == 0:
        raise SystemExit('No devices matches available drivers and selection criteria')
    num, dev = selected[0]

    dev.connect(**frwd)
    try:
        if args['initialize']:
            dev.initialize(**frwd)
        elif args['set'] and args['speed']:
            _device_set_speed(dev, args, **frwd)
        elif args['set'] and args['color']:
            _device_set_color(dev, args, **frwd)
        else:
            raise Exception('Not sure what to do')
    finally:
        dev.disconnect(**frwd)


if __name__ == '__main__':
    main()

