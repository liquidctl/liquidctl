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
  --usb-port <no>           Filter devices by USB port
  --serial <no>             Filter devices by serial number

Other options:
  --speed <value>           Animation speed [default: normal]
  -n, --dry-run             Do not apply any settings (implies --verbose)
  -v, --verbose             Output supplemental information to stderr
  --version                 Display the version number
  --help                    Show this message

Examples:
  liquidctl status
  liquidctl set pump speed 90
  liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
  liquidctl set ring color fading 350017 ff2608
  liquidctl set logo color fixed af5a2f

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Copyright (C) 2018  Jonas Malaco
Copyright (C) 2018  each contribution's author

Incorporates work by leaty, KsenijaS, Alexander Tong and Jens
Neumaier, under the terms of the GNU General Public License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import inspect
import itertools

from docopt import docopt

import liquidctl.util
from liquidctl.driver.kraken_two import KrakenTwoDriver
from liquidctl.driver.nzxt_smart_device import NzxtSmartDeviceDriver


DRIVERS = [
    KrakenTwoDriver,
    NzxtSmartDeviceDriver,
    # only append new drivers, keep the behavior of --device stable
]

VERSION = 'liquidctl v1.0.0'


def find_all_supported_devices():
    search_res = map(lambda driver: driver.find_supported_devices(), DRIVERS)
    return list(enumerate(itertools.chain(*search_res)))


def filter_devices(devices, args):
    def selected(attr, arg_name):
        return not args[arg_name] or attr == int(args[arg_name], 0)
    if args['--device']:
        return [devices[int(args['--device'])]]
    sel = []
    for i, dev in devices:
        und = dev.device
        if (selected(und.idVendor, '--vendor') and
            selected(und.idProduct, '--product') and
            selected(und.port_number, '--usb-port') and
            (not args['--serial'] or und.serial_number == args['--serial'])):
            # --serial handled differently to avoid unnecessary root
            sel.append((i, dev))
    return sel


def list_devices(devices):
    for i, dev in devices:
        und = dev.device
        print('Device {}, {}'.format(i, dev.description))
        if liquidctl.util.verbose:
            print('  Vendor: {:#06x}'.format(und.idVendor))
            print('  Product: {:#06x}'.format(und.idProduct))
            print('  Port number: {}'.format(und.port_number))
            try:
                print('  Serial number: {}'.format(und.serial_number or '<empty>'))
            except:
                print('  Serial number: <n/a> (try again as root)')
            hier = [i.__name__ for i in inspect.getmro(type(dev)) if i != object]
            print('  Hierarchy: {}'.format(', '.join(hier)))
            print('')


def device_get_status(dev, num):
    print('Device {}, {}'.format(num, dev.description))
    dev.connect()
    try:
        status = dev.get_status()
        for k, v, u in status:
            print('{:<20}  {:>6}  {:<3}'.format(k, v, u))
    finally:
        dev.disconnect()
    print('')


def device_set_color(dev, args):
    color = map(lambda c: list(parse_color(c)), args['<color>'])
    dev.set_color(args['<channel>'], args['<mode>'], color, args['--speed'])


def device_set_speed(dev, args):
    if len(args['<temperature>']) > 0:
        profile = zip(map(int, args['<temperature>']), map(int, args['<percentage>']))
        dev.set_speed_profile(args['<channel>'], profile)
    else:
        dev.set_fixed_speed(args['<channel>'], int(args['<percentage>'][0]))


def parse_color(color):
    return bytes.fromhex(color)


def main():
    args = docopt(__doc__, version=VERSION)
    liquidctl.util.dryrun = args['--dry-run']
    liquidctl.util.verbose = args['--verbose'] or liquidctl.util.dryrun
    all_devices = find_all_supported_devices()
    selected = filter_devices(all_devices, args)

    if args['list']:
        list_devices(selected)
        return
    if args['status']:
        for i,dev in selected:
            device_get_status(dev, i)
        return

    if len(selected) > 1:
        raise SystemExit('Too many devices, filter or select one (see: liquidctl --help)')
    elif len(selected) == 0:
        raise SystemExit('No devices matches available drivers and selection criteria')
    num, dev = selected[0]

    dev.connect()
    try:
        if args['initialize']:
            dev.initialize()
        elif args['set'] and args['speed']:
            device_set_speed(dev, args)
        elif args['set'] and args['color']:
            device_set_color(dev, args)
        else:
            raise Exception('Not sure what to do')
    finally:
        dev.disconnect()


if __name__ == '__main__':
    main()
