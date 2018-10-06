# liquidctl – liquid cooler control

```
# liquidctl list
Device 0, NZXT Kraken X (X42, X52, X62 or X72)
Device 1, NZXT Kraken M22 (experimental)
Device 2, NZXT Smart Device
Device 3, NZXT Grid+ V3 (experimental)

# liquidctl --device 0 status
Device 0, NZXT Kraken X (X42, X52, X62 or X72)
Liquid temperature          29.4  °C
Fan speed                    639  rpm
Pump speed                  1910  rpm
Firmware version           4.0.2

# liquidctl --device 2 status
Device 2, NZXT Smart Device
Fan 1                        PWM
Fan 1 current               0.04  A
Fan 1 speed                 1519  rpm
Fan 1 voltage              11.91  V
Fan 2                          —
Fan 3                          —
Firmware version           1.0.7
LED accessories                2
LED accessory type    Hue+ Strip
LED count (total)             20
Noise level                   61  dB

# liquidctl --device 0 set pump speed 90
# liquidctl --device 0 set fan speed  20 30  30 50  34 80  40 90  50 100
# liquidctl --device 0 set ring color fading 350017 ff2608
```

*liquidctl* is an open-source and cross-platform command-line tool and set of drivers to monitor and control liquid coolers and related devices.

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

The complete list of commands and options can be seen with `liquidctl --help`, but a good place to start is to ask liquidctl to list all recognized devices.

```
liquidctl list
```

In case more than one supported device is found, they can be selected with the `--device <no>` option, according to the output of `list`.  They can also be filtered by `--vendor` id, `--product` id, `--usb-port`, or even `--serial` number.

Most devices provide some status information, like fan speeds and liquid temperatures.  This can be queried for all devices or together with the filtering methods mentioned before.

```
liquidctl [options] status
```

Fan and pump speeds can be set to fixed values or, if the device supports them, custom profiles.  The documentation for each driver lists their exact capabilities.

```
liquidctl [options] set <channel> speed (<temperature> <percentage>) ...
liquidctl [options] set <channel> speed <percentage>
```

Lighting is controlled in a similar fashion and, again, the specific documentation lists the available channels, modes and other details.  The animation speed can be controlled with the `--speed` flag.

```
liquidctl [options] set <channel> color <mode> [<color>] ...
```


## Supported devices

The links bellow lead to the documentation for each supported device:

 - [NZXT Kraken X42, X52, X62 and X72 coolers](docs/nzxt-kraken-x-3rd-generation.md)
 - [NZXT Kraken M22 cooler (experimental)](docs/nzxt-kraken-x-3rd-generation.md#experimental-support-for-the-kraken-m22)
 - [NZXT Smart Device and H200i/H400i/H500i/H700i cases](docs/nzxt-smart-device.md)
 - [NZXT Grid+ V3 fan controller (experimental)](docs/nzxt-smart-device.md#experimental-support-for-the-grid-v3)

[Open an issue][newissue] to let us know which other drivers we should implement first, and if/how you can help.


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
