# liquidctl – liquid cooler control

_Cross-platform tool and drivers for liquid coolers and other devices_

[![Build status on Windows](https://ci.appveyor.com/api/projects/status/n5lgebd5m8iomx42/branch/master?svg=true)](https://ci.appveyor.com/project/jonasmalacofilho/liquidctl/branch/master)
[![Join the chat on Gitter](https://badges.gitter.im/liquidctl/Lobby.svg)](https://gitter.im/liquidctl/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)


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
4. [Automation and running at boot](#automation-and-running-at-boot)
5. [License](#license)
6. [Related projects](#related-projects)


## Supported devices

| Device vendor and model | Monitoring | Cooling | Lighting | Details |
| --- | --- | --- | --- | --- |
| NZXT Kraken X (X42, X52, X62 or X72) | ✓ | ✓ | ✓ | [(documentation)](docs/nzxt-kraken-x-3rd-generation.md) |
| NZXT Smart Device | ✓ | ✓ | ✓  | [(documentation)](docs/nzxt-smart-device.md) |
| NZXT Grid+ V3 | ✓' | ✓' | | [(documentation)](docs/nzxt-smart-device.md#experimental-support-for-the-grid-v3) |
| NZXT Kraken M22 | | | ✓ | [(documentation)](docs/nzxt-kraken-x-3rd-generation.md#experimental-support-for-the-kraken-m22) |

✓ &nbsp; _Implemented_  
✓'&nbsp; _Experimental_  
✗ &nbsp; _Missing/locked_  
_ &nbsp; _Not available at the hardware level_


## Getting liquidctl

### The pythonic way

The easiest way to get liquidctl is to grab a [release from PyPI](https://pypi.org/project/liquidctl/#history) with *pip*.  For currently under development features, pip can also be used to install the latest snapshot of the official repository.

```
# pip install liquidctl
# pip install liquidctl==<version>
# pip install git+https://github.com/jonasmalacofilho/liquidctl
```

Contributors to the project's code or documentation will want to manually clone the repository and install liquidctl in editable mode.

```
$ git clone https://github.com/jonasmalacofilho/liquidctl
$ cd liquidctl
# pip install --editable .
```

Of course, a virtual environment can always be used instead of installing the package globally.


### Pre-built packages and executables

Packages for Linux distributions:

 - ArchLinux: [python-liquidctl<sup>AUR</sup>](https://aur.archlinux.org/packages/python-liquidctl/)
 - Fedora (28, 29, Rawhide): [liquidctl, python3-liquidctl](https://pkgs.org/download/liquidctl)

Pre-built binaries for Windows:

 - Releases: check the [Releases](https://github.com/jonasmalacofilho/liquidctl/releases) tab
 - Development builds: select from the [last builds](https://ci.appveyor.com/project/jonasmalacofilho/liquidctl/history) on AppVeyor and check the artifacts tab

### System dependencies

liquidctl uses [PyUSB](https://github.com/pyusb/pyusb) and [cython-hidapi](https://github.com/trezor/cython-hidapi) to communicate with USB devices.  PyUSB requires that a suitable backend for it be available at runtime; hidapi, depending on the platform and how it has been built, might also require one.

Pre-built packages and executables should take of these dependencies automatically.  If you use other user-space programs that interact with USB devices, it is also possible that you already have the required libraries installed.  In all other cases we recommend you install libusb-1.0, which should cover the needs of both PyUSB and cython-hidapi.

On Linux, it is usually available in a libusb-1.0 or similar package.  On Windows, version libusb v1.0.21 is recommended over the latest, because of a known issue with PyUSB that causes errors when releasing the device.  Download the package from [libusb/releases](https://github.com/libusb/libusb/releases/tag/v1.0.21) and extract appropriate (e.g. MS64) `.dll` and `.lib` files to your system or python installation directory (e.g. `C:\Windows\System32` or `C:\Python36`).


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

# Automation and running at boot

In most cases you will want to automatically apply your settings when the system boots.  Generally a simple script or a basic service is enough for, and some specifics about this are given in the following sections.

If you need more control for some really ambitious automation, you can also write a Python program that calls the driver APIs directly.

### Linux

On systems running Linux and Systemd, a service unit can be used to configure liquidctl devices.  A simple example is provided bellow, you can edit it to match your preferences and save the result to `/etc/system.d/system/liquidcfg.service`.

```
[Unit]
Description=AIO startup service

[Service]
Type=oneshot
ExecStart=liquidctl set pump speed 90
ExecStart=liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
ExecStart=liquidctl set ring color fading 350017 ff2608
ExecStart=liquidctl set logo color spectrum-wave

[Install]
WantedBy=default.target
```

The unit can be started manually or set to automatically run during boot using standard Systemd tools:

```
# systemctl start liquidcfg
# systemctl enable liquidcfg
```

A slightly more complex example can be seen at [jonasmalacofilho/dotfiles](https://github.com/jonasmalacofilho/dotfiles/tree/master/liquidctl), that handles multiple devices and uses the LEDs to convey progress or eventual errors.

### Windows

The configuration of devices can be automated by writing a batch file and setting up a new scheduled task for (every) log on.  The batch file can be really simple and just list the various invocations of liquidctl you would otherwise do by hand.

```batchfile
liquidctl set pump speed 90
liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
liquidctl set ring color fading 350017 ff2608
liquidctl set logo color spectrum-wave
```

Make sure that Python and executables from its packages are available in the context where the batch file will run: in short, `python --version` and `liquidctl --version` should work within a _normal_ Command Prompt window.

If necessary, try installing Python with the option to set the PATH variable enabled, or manually add the necessary folders to the PATH. Alternatively, if you're using Anaconda, try adding the following line to the beginning of the file:

```batchfile
call %homepath%\Anaconda3\Scripts\activate.bat
```

A slightly more complex example can be seen in [issue #14](https://github.com/jonasmalacofilho/liquidctl/issues/14#issuecomment-456519098) ("Can I autostart liquidctl on Windows?"), that uses the LEDs to convey progress or eventual errors.

Chris' guide on [Replacing NZXT’s CAM software on Windows for Kraken](https://codecalamity.com/replacing-nzxts-cam-software-on-windows-for-kraken/) goes into a lot more detail and is a good read.


## License

Copyright (C) 2018–2019  Jonas Malaco  
Copyright (C) 2018–2019  each contribution's author

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

### [jonasmalacofilho/liquidctl-linux-drivers](https://github.com/jonasmalacofilho/liquidctl-linux-drivers)

Ongoing work on Linux kernel drivers that implement standard hwmon sysfs
interfaces for (most of) the devices that are supported by liquidctl, allowing
the use of standard monitoring tools (e.g. lm-sensors).

### [brkalmar/leviathan](https://github.com/brkalmar/leviathan)

Linux kernel-space drivers for second and third generation NZXT Kraken X coolers.

### [audiohacked/OpenCorsairLink](https://github.com/audiohacked/OpenCorsairLink)

Command-line tool to control Corsair all-in-one liquid coolers and other devices.

### [KsenijaS/krakenx](https://github.com/KsenijaS/krakenx)

A related cross-plataform interface for controlling third generation NZXT Kraken X coolers.

_A special thanks to all krakenx contributors; this project would not exist were not for it._


<!-- helper links -->
[newissue]: https://github.com/jonasmalacofilho/liquidctl/issues/new
