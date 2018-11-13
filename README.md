# liquidctl – liquid cooler control

_Cross-platform tool and drivers for liquid coolers and other devices_

[![Join the chat at https://gitter.im/liquidctl/Lobby](https://badges.gitter.im/liquidctl/Lobby.svg)](https://gitter.im/liquidctl/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

```
# liquidctl list
Device 0, NZXT Kraken X (X42, X52, X62 or X72)

# liquidctl initialize

# liquidctl status
Device 0, NZXT Kraken X (X42, X52, X62 or X72)
Liquid temperature          29.4  °C
Fan speed                    639  rpm
Pump speed                  1910  rpm
Firmware version           4.0.2

# liquidctl set pump speed 90
# liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100

# liquidctl set ring color fading 350017 ff2608
# liquidctl set logo color spectrum-wave
```

<!-- stop here for PyPI -->

## Summary

1. [Supported devices](#supported-devices)
2. [Getting liquidctl](#getting-liquidctl)
3. [The command-line interface](#the-command-line-interface)
4. [License](#license)
6. [Related projects](#related-projects)


## Supported devices

| Device vendor and model | Monitoring | Cooling | Lighting | Details |
| --- | --- | --- | --- | --- |
| NZXT Kraken X (X42, X52, X62 or X72) | ✓ | ✓ | ✓ | [(documentation)](docs/nzxt-kraken-x-3rd-generation.md) |
| NZXT Smart Device | ✓ | ✓ | ✓  | [(documentation)](docs/nzxt-smart-device.md) |
| NZXT Grid+ V3 | ✓' | ✓' | | [(documentation)](docs/nzxt-smart-device.md#experimental-support-for-the-grid-v3) |
| NZXT Kraken M22 | | | ✓'  | [(documentation)](docs/nzxt-kraken-x-3rd-generation.md#experimental-support-for-the-kraken-m22) |

✓ &nbsp; _Implemented_  
✓'&nbsp; _Experimental_  
✗ &nbsp; _Missing/locked_  
_ &nbsp; _Not available at the hardware level_


## Getting liquidctl

The easiest way to get liquidctl is to grab a release from PyPI with *pip*.  For currently under development features, pip can also be used to install the latest snapshot of the official repository.

```
# pip install liquidctl
# pip install git+https://github.com/jonasmalacofilho/liquidctl
```

Contributors to the project's code or documentation will want to manually clone the repository and install liquidctl in editable mode.

```
$ git clone https://github.com/jonasmalacofilho/liquidctl
$ cd liquidctl
# pip install --editable .
```

Of course, a virtual environment can always be used instead of installing the package globally.

In all cases, a suitable backend for PyUSB, such as *libusb*, is necessary.  If you use other Python programs that interact with USB devices, one might already be installed.

### Windows and libusb

On Windows, libusb v1.0.21 is recommended over the latest v1.0.22.  A known issue with PyUSB generates some annoying – if probably harmless – errors when trying to release the device.

A simple way of installing it is to download the appropriate package from [libusb/releases](https://github.com/libusb/libusb/releases) and extract the `.dll` and `.lib` files that match you runtime (e.g. MS64) to your python installation directory (e.g. `%homepath%\Anaconda3\`).


## The command-line interface

The complete list of commands and options can be seen with `liquidctl --help`, but a good place to start is to ask liquidctl to list all recognized devices.

```
# liquidctl list
```

In case more than one supported device is found, they can be selected with the `--device <no>` option, according to the output of `list`.  They can also be filtered by `--vendor` id, `--product` id, `--usb-port`, or even `--serial` number.

Devices will usually need to be initialized before they can be used, though each device has its own requirements and limitations.  This and other information specific to a particular device will appear on the documentation linked in the [supported devices](#supported-devices) section.

```
# liquidctl initialize
```

Most devices provide some status information, like fan speeds and liquid temperatures.  This can be queried for all devices or using the filtering methods mentioned before.

```
# liquidctl [options] status
```

Fan and pump speeds can be set to fixed values or, if the device supports them, custom profiles.

```
# liquidctl [options] set <channel> speed (<temperature> <percentage>) ...
# liquidctl [options] set <channel> speed <percentage>
```

Lighting is controlled in a similar fashion and, again, the specific documentation lists the available channels, modes and other details.  The animation speed can be controlled with the `--speed` flag.

```
# liquidctl [options] set <channel> color <mode> [<color>] ...
```

Finally, the `--verbose` option will print some extra information, like automatically made adjustments to the user provided settings.  And if there is a problem, the `--debug` flag will print as much information as possible to help identify its cause; be sure to include it when opening a new issue.


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
