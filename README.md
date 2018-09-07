# liquidctl – liquid cooler control

```
# liquidctl list
Device 0, NZXT Kraken X (X42, X52, X62 or X72) at bus:address 2:5
Device 1, NZXT Smart Device at bus:address 2:4

# liquidctl status
NZXT Kraken X (X42, X52, X62 or X72), device 0
Liquid temperature      29.3  °C
Fan speed                684  rpm
Pump speed              2133  rpm
Firmware version       4.0.2

NZXT Smart Device, device 1
Fan 1                    PWM
Fan 1 current           0.03  A
Fan 1 speed             1346  rpm
Fan 1 voltage          12.04  V
Fan 2                      —
Fan 3                      —
Firmware version       1.0.7
LED strips                 2
Noise level               55  dB

# liquidctl --device 0 set pump speed 90
# liquidctl --device 0 set fan speed  20 30  30 50  34 80  40 90  50 100
# liquidctl --device 0 set ring color fading 350017 ff2608
```

*liquidctl* is an open-source and cross-platform command-line tool to monitor and control liquid coolers and other devices.

<!-- stop here for PyPI -->

## Summary

1. [Getting liquidctl](#getting-liquidctl)
2. [The command-line interface](#the-command-line-interface)
3. [Supported devices](#supported-devices)
4. [License](#license)
6. [Related projects](#related-projects)


## Getting liquidctl

The easiest way to get liquidctl is to grab a release from PyPI.

```
# pip install liquidctl
```

Pip can also install the latest snapshot directly from GitHub.

```
# pip install git+https://github.com/jonasmalacofilho/liquidctl
```

On the other hand, if you want to work on the source and contribute to the project, you will find more convenient to clone the repository manually and install liquidctl in editable mode.

```
$ git clone https://github.com/jonasmalacofilho/liquidctl
$ cd liquidctl
# pip install --editable .
```

Of course, a virtual environment can always be used instead of installing the package globally.

In all cases, a suitable backend for PyUSB, such as *libusb*, is necessary.  If you use other Python programs that interact with USB devices, one might already be installed.

### Windows and libusb

On Windows, libusb v1.0.21 is recommended; later versions can crash when trying to release the device.

A simple way of installing it is to download the appropriate package from [libusb/releases](https://github.com/libusb/libusb/releases) and extract the `.dll` and `.lib` files that match you runtime (e.g. MS64) to your python installation directory (e.g. `%homepath%\Anaconda3\`).


## The command-line interface

A good place to start is to ask liquidctl to list all recognized devices.

```
liquidctl [options] list
```

In case more than one supported device is found, the desired target for each command can be selected with `--device <no>`, using the device number reported by `list`.

Most devices will provide status information like fan speeds and liquid temperatures.

```
liquidctl [options] status
```

Fan and pump speeds can be set to fixed values or custom profiles, depending on the device.  The documentation for each driver will list the available channels and their capabilities.

```
liquidctl [options] set <channel> speed (<temperature> <percentage>) ...
liquidctl [options] set <channel> speed <percentage>
```

Lighting is controlled in a similar fashion.  Animation speed can be controlled with the `--speed` flag.  The documentation for each device will list the available channels, lighting modes and speed values.

```
liquidctl [options] set <channel> color <mode> [<color>] ...
```

To view all available options and commands, run `liquidctl --help`.


## Supported devices 

The following devices are supported:

 - [NZXT Kraken X42, X52, X62 and X72 coolers](docs/nzxt-kraken-x-3rd-generation.md)
 - [NZXT Smart Device and H200i/H400i/H500i/H700i cases](docs/nzxt-smart-device.md)

We aim to soon add drivers for these coolers as well:

 - EVGA CLC 120/240/280: need to borrow a device or get the protocol specs [**[I can help/I know someone]**][newissue]
 - NZXT Kraken M22: probably easy to add, need a beta tester [**[I can help/I know someone]**][newissue]

If you would like to use liquidctl with another device not listed here, feel free to [open an issue][newissue] and let us know.


## License

Copyright (C) 2018  Jonas Malaco  
Copyright (C) 2018  each contribution's author

Incorporates work by leaty, KsenijaS, Alexander Tong and Jens Neumaier, under
the terms of the GNU General Public License.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

**This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.**  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.


## Related projects

### [KsenijaS/krakenx](https://github.com/KsenijaS/krakenx)

Another cross-plataform interface for controlling third generation NZXT Kraken X coolers.

While liquidctl handles each setting separately, for easy configuration of individual aspects of the coolers, krakenx allows a device to be completely configured in a single command.

Feature wise, liquidctl currently extends krakenx with the support for pump and fan speed profiles, and fixes two open issues that seem to manifest with recent firmware versions.  It also further extends the list of supported RGB animations.

A special thank you to all krakenx contributors.  This project would not exist were not for it.

### [brkalmar/leviathan](https://github.com/brkalmar/leviathan)

Linux kernel-space driver for second and third generation NZXT Kraken X coolers.

### [audiohacked/OpenCorsairLink](https://github.com/audiohacked/OpenCorsairLink)

Command-line tool to control Corsair all-in-one liquid coolers and other devices.


<!-- helper links -->
[newissue]: https://github.com/jonasmalacofilho/liquidctl/issues/new
