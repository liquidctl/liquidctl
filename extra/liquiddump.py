#!/usr/bin/env python3

"""liquiddump – continuously dump monitoring data from liquidctl devices.

This is a experimental script that continuously dumps the status of all
available devices to stdout in newline-delimited JSON.

Usage:
  liquiddump [options]
  liquiddump --help
  liquiddump --version

Options:
  --interval <seconds>    Update interval in seconds [default: 2]
  --legacy-690lc          Use Asetek 690LC in legacy mode (old Krakens)
  --vendor <id>           Filter devices by vendor id
  --product <id>          Filter devices by product id
  --release <number>      Filter devices by release number
  --serial <number>       Filter devices by serial number
  --bus <bus>             Filter devices by bus
  --address <address>     Filter devices by address in bus
  --usb-port <port>       Filter devices by USB port in bus
  --pick <number>         Pick among many results for a given filter
  -v, --verbose           Output additional information
  -g, --debug             Show debug information on stderr
  --version               Display the version number
  --help                  Show this message

Examples:
  liquiddump
  liquiddump --product 0xb200
  liquiddump --interval 0.5
  liquiddump > file.jsonl
  liquiddump | jq -c .

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import json
import logging
import sys
import time

import liquidctl.cli as _borrow
import usb
from docopt import docopt
from liquidctl.driver import *

LOGGER = logging.getLogger(__name__)

if __name__ == "__main__":
    args = docopt(__doc__, version="0.1.1")
    frwd = _borrow._make_opts(args)
    devs = list(find_liquidctl_devices(**frwd))
    update_interval = float(args["--interval"])

    if args["--debug"]:
        args["--verbose"] = True
        logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(name)s: %(message)s")
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(message)s")
        sys.tracebacklimit = 0

    try:
        for d in devs:
            LOGGER.info("initializing %s", d.description)
            d.connect()
        status = {}
        while True:
            for d in devs:
                try:
                    status[d.description] = d.get_status()
                except usb.core.USBError as err:
                    LOGGER.warning("failed to read from the device, possibly serving stale data")
                    LOGGER.debug(err, exc_info=True)
            print(json.dumps(status), flush=True)
            time.sleep(update_interval)
    except KeyboardInterrupt:
        LOGGER.info("canceled by user")
    except:
        LOGGER.exception("unexpected error")
        sys.exit(1)
    finally:
        for d in devs:
            try:
                LOGGER.info("disconnecting from %s", d.description)
                d.disconnect()
            except:
                LOGGER.exception("unexpected error when disconnecting")
