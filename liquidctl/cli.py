"""liquidctl – liquid cooler control

Usage:
  liquidctl [options] status
  liquidctl [options] set <channel> speed (<temperature> <percentage>) ...
  liquidctl [options] set <channel> speed <percentage>
  liquidctl [options] set <channel> color <mode> [<color>] ...
  liquidctl [options] list
  liquidctl --help
  liquidctl --version

Options:
  --device <no>    Select the device
  --speed <value>  Animation speed [default: normal]
  -n, --dry-run    Do not actually set anything (implies --verbose)
  -v, --verbose    Output additional/debug information to stderr
  --help           Show this message

Examples:
  liquidctl status
  liquidctl set pump speed 90
  liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
  liquidctl set ring color fading 350017 ff2608
  liquidctl set logo color fixed af5a2f

Copyright (C) 2018  Jonas Malaco  
Copyright (C) 2018  each contribution's author

Incorporates work by leaty, KsenijaS, Alexander Tong and Jens Neumaier, under
the terms of the GNU General Public License.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

VERSION = 'liquidctl v1.0.0'

import itertools

from docopt import docopt

# from liquidctl.driver.evga_clc import EvgaClcDriver
# from liquidctl.driver.kraken_em import KrakenEmDriver
# from liquidctl.driver.nzxt_smart_device import SmartDeviceDriver
from liquidctl.driver.kraken_two import KrakenTwoDriver
import liquidctl.util


def find_all_supported_devices():
    alldrivers = [KrakenTwoDriver]
    return list(itertools.chain(*map(lambda driver: driver.find_supported_devices(), alldrivers)))


def parse_color(color):
    return bytes.fromhex(color)


def main():
    args = docopt(__doc__, version=VERSION)
    liquidctl.util.dryrun = args['--dry-run']
    liquidctl.util.verbose = args['--verbose'] or liquidctl.util.dryrun

    devices = find_all_supported_devices()
    if args['--device']:
        desired = int(args['--device'])
    elif len(devices) == 1:
        desired = 0
    else:
        desired = None

    if args['list']:
        for i, cooler in enumerate(devices):
            liquidctl.util.debug(cooler.device)
            print('Device {}, {} at bus:address {}:{}'.format(
                i, cooler.description, cooler.device.bus, cooler.device.address))
    elif args['status']:
        for i,dev in enumerate(devices):
            if desired is not None and desired != i:
                continue
            print('{}, device {}'.format(dev.description, i))
            dev.initialize()
            try:
                status = dev.get_status()
                for k,v,u in status:
                    print('{:<20}  {:>6}  {:<3}'.format(k, v, u))
            finally:
                dev.finalize()
            print('')
    elif desired is not None:
        dev = devices[desired]
        dev.initialize()
        try:
            if args['set'] and args['speed']:
                if len(args['<temperature>']) > 0:
                    profile = zip(map(int, args['<temperature>']), map(int, args['<percentage>']))
                    dev.set_speed_profile(args['<channel>'], profile)
                else:
                    dev.set_fixed_speed(args['<channel>'], int(args['<percentage>'][0]))
            elif args['set'] and args['color']:
                color = map(lambda c: list(parse_color(c)), args['<color>'])
                dev.set_color(args['<channel>'], args['<mode>'], color, args['--speed'])
            else:
                raise Exception('Not sure what to do')
        finally:
            dev.finalize()
    else:
        raise SystemExit('Many devices available, specify one with --device <no>\n(try also: liquidctl list)')


if __name__ == '__main__':
    run_cli()

