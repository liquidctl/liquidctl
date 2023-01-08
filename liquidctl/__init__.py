"""Monitor and control liquid coolers and other devices.

liquidctl provides facilities for monitoring and controlling liquid coolers and
other hardware monitoring or LED controller devices in Python:

    from liquidctl import find_liquidctl_devices

    # Find all connected and supported devices.
    devices = find_liquidctl_devices()

    for dev in devices:

        # Connect to the device. In this example we use a context manager, but
        # the connection can also be manually managed. The context manager
        # automatically calls `disconnect`; when managing the connection
        # manually, `disconnect` must eventually be called, even if an
        # exception is raised.
        with dev.connect():
            print(f'{dev.description} at {dev.bus}:{dev.address}:')

            # Devices should be initialized after every boot. In this example
            # we assume that this has not been done before.
            print('- initialize')
            init_status = dev.initialize()

            # Print all data returned by `initialize`.
            if init_status:
                for key, value, unit in init_status:
                    print(f'- {key}: {value} {unit}')

            # Get regular status information from the device.
            status = dev.get_status()

            # Print all data returned by `get_status`.
            print('- get status')
            for key, value, unit in status:
                print(f'- {key}: {value} {unit}')

            # For a particular device, set the pump LEDs to red.
            if 'Kraken' in dev.description:
                print('- set pump to radical red')
                radical_red = [0xff, 0x35, 0x5e]
                dev.set_color(channel='pump', mode='fixed', colors=[radical_red])

A command-line interface is also available:

    $ python -m liquidctl --help

Once the liquidctl package is installed, a `liquidctl` executable should also
be available:

    $ liquidctl --help

Copyright 2018–2023 Jonas Malaco, Marshall Asch, CaseySJ, Tom Frey, Andrew
Robertson, ParkerMc, Aleksa Savic, Shady Nawara and contributors

Some modules also incorporate or use as reference work by leaty, Ksenija
Stanojevic, Alexander Tong, Jens Neumaier, Kristóf Jakab, Sean Nelson, Chris
Griffith, notaz, realies and Thomas Pircher. This is mentioned in the module
docstring, along with appropriate additional copyright notices.

SPDX-License-Identifier: GPL-3.0-or-later
"""

# uses the psf/black style

from liquidctl.driver import find_liquidctl_devices
from liquidctl.error import *
from liquidctl.version import __version__
