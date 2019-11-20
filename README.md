# liquidctl – liquid cooler control

_Cross-platform tool and drivers for liquid coolers and other devices_

[![Status of the tests](https://github.com/jonasmalacofilho/liquidctl/workflows/tests/badge.svg)](https://github.com/jonasmalacofilho/liquidctl/commits/master)
[![Status of the build for Windows](https://ci.appveyor.com/api/projects/status/n5lgebd5m8iomx42/branch/master?svg=true&passingText=windows%20exe&failingText=failed&pendingText=building)](https://ci.appveyor.com/project/jonasmalacofilho/liquidctl/branch/master)


```
# liquidctl list
Device ID 0: NZXT Smart Device (V1)
Device ID 1: NZXT Kraken X (X42, X52, X62 or X72)

# liquidctl initialize all
# liquidctl --match smart set fan1 speed 50
# liquidctl --match smart set led color fading 350017 ff2608
# liquidctl --match kraken set fan speed  20 30  30 50  34 80  40 90  50 100
# liquidctl --match kraken set sync color spectrum-wave

# liquidctl status
NZXT Smart Device (V1)
├── Fan 1                        PWM  
├── Fan 1 current               0.04  A
├── Fan 1 speed                 1035  rpm
├── Fan 1 voltage              11.91  V
├── Fan 2                          —  
├── Fan 3                          —  
├── Firmware version           1.0.7  
├── LED accessories                2  
├── LED accessory type    HUE+ Strip  
├── LED count (total)             20  
└── Noise level                   60  dB

NZXT Kraken X (X42, X52, X62 or X72)
├── Liquid temperature     28.1  °C
├── Fan speed               851  rpm
├── Pump speed             1953  rpm
└── Firmware version      6.0.2  
```

<!-- stop here for PyPI -->


## Table of contents

1. [Supported devices](#supported-devices)
2. [Pre-built packages and executables](#pre-built-packages-and-executables)
3. [Installing from sources](#installing-from-sources)
    1. [Grabbing releases with pip](#grabbing-releases-with-pip)
    2. [Testing and developing new features](#testing-and-developing-new-features)
    3. [Additional requirements on Linux](#additional-requirements-on-linux)
    4. [Additional requirements on Windows](#additional-requirements-on-windows)
    5. [Additional requirements on Mac OS](#additional-requirements-on-mac-os)
4. [The command-line interface](#introducing-the-command-line-interface)
5. [Automation and running at boot](#automation-and-running-at-boot)
    1. [Set up Linux using systemd](#set-up-linux-using-systemd)
    2. [Set up Windows using Task Scheduler](#set-up-windows-using-task-scheduler)
    3. [Set up Mac OS using launchd](#set-up-mac-os-using-launchd)
6. [License](#license)
7. [Related projects](#related-projects)


## Supported devices

### All-in-one liquid coolers

| Family | Documentation | Notes |
| --- | --- | --- |
| Corsair H80i GT, H100i GTX, H110i GTX | [documentation](docs/asetek-690lc.md) | <sup>_E_</sup> |
| Corsair H80i v2, H100i v2, H115i | [documentation](docs/asetek-690lc.md) | |
| EVGA CLC 120 (CL12), 240, 280, 360 | [documentation](docs/asetek-690lc.md) | |
| NZXT Kraken M22 | [documentation](docs/nzxt-kraken-x-3rd-generation.md) | |
| NZXT Kraken X40, X60 | [documentation](docs/asetek-690lc.md) | <sup>_E, L_</sup> |
| NZXT Kraken X31, X41, X61 | [documentation](docs/asetek-690lc.md) | <sup>_E, L_</sup> |
| NZXT Kraken X42, X52, X62, X72 | [documentation](docs/nzxt-kraken-x-3rd-generation.md) | |

### Other parts

| Family | Documentation | Notes |
| --- | --- | --- |
| Corsair HX750i, HX850i, HX1000i, HX1200i | [documentation](docs/corsair-hxi-rmi.md) | <sup>_E_</sup> |
| Corsair RM650i, RM750i, RM850i, RM1000i | [documentation](docs/corsair-hxi-rmi.md) | <sup>_E_</sup> |
| NZXT E500, E650, E850 | [documentation](docs/seasonic-e-series.md) | <sup>_E_</sup> |
| NZXT Grid+ V3 | [documentation](docs/nzxt-smart-device.md) | |
| NZXT HUE 2, HUE 2 Ambient | [documentation](docs/nzxt-smart-device-v2.md) | <sup>_E_</sup> |
| NZXT Smart Device | [documentation](docs/nzxt-smart-device.md) | |
| NZXT Smart Device V2 | [documentation](docs/nzxt-smart-device-v2.md) | <sup>E</sup> |

<sup>_E_</sup> _Experimental._  
<sup>_L_</sup> _Requires the `--legacy-690lc` flag._  


## Pre-built packages and executables

Packages for Linux distributions:

 - ArchLinux: [python-liquidctl<sup>AUR</sup>](https://aur.archlinux.org/packages/python-liquidctl/), [python-liquidctl-git<sup>AUR</sup>](https://aur.archlinux.org/packages/python-liquidctl-git/)
 - Fedora: [liquidctl, python3-liquidctl](https://pkgs.org/download/liquidctl)
 - Linuxbrew tap: [jonasmalacofilho/homebrew-liquidctl](https://github.com/jonasmalacofilho/homebrew-liquidctl)

Pre-built binaries for Windows:

 - Official releases: check the assets in the [Releases](https://github.com/jonasmalacofilho/liquidctl/releases) tab
 - Development builds: select from the [last builds](https://ci.appveyor.com/project/jonasmalacofilho/liquidctl/history) on AppVeyor and check the artifacts tab
 - _Some devices may require an [additional kernel driver](#additional-requirements-on-windows)_

Homebrew formula for Mac OS:

 - Homebrew tap: [jonasmalacofilho/homebrew-liquidctl](https://github.com/jonasmalacofilho/homebrew-liquidctl)


## Installing from sources

liquidctl runs on [Python](https://www.python.org/) 3.6 or later and uses [libusb](https://github.com/libusb/libusb) and [HIDAPI](https://github.com/libusb/hidapi) to communicate with devices.

The most important Python dependencies are [PyUSB](https://github.com/pyusb/pyusb) and [cython-hidapi](https://github.com/trezor/Cython-hidapI), but a few other libraries (e.g. docopt) are used as well; all of them are listed in `setup.py`.

On Windows some devices might require the installation of a special kernel driver.  HIDAPI's dependencies can also vary depending on the platform.  These and other platform details and quirks are documented bellow, after common installation instructions.

### Grabbing releases with pip

*pip* can be used to grab a [release from PyPI](https://pypi.org/project/liquidctl/#history).  For currently under development features, pip can also be used to install the latest snapshot of the official repository.

```
# pip install liquidctl
# pip install liquidctl==<version>
# pip install git+https://github.com/jonasmalacofilho/liquidctl
```

_Note: a virtual environment can be used to avoid installing the package globally._

### Testing and developing new features

Contributors to the project's code or documentation are encouraged to manually clone the repository.  pip can then be used to install liquidctl in editable/development mode.


```
$ git clone https://github.com/jonasmalacofilho/liquidctl
$ cd liquidctl
# pip install --editable .
```

_Note: a virtual environment can be used to avoid installing the package globally._

### Additional requirements on Linux

Installing cython-hidapi on Linux can require locally building some C extensions (automatically).  Both libusb-1.0 and libudev are needed for this, together with their corresponding development files.  You may also need development files for Python.

| Linux dependency | Arch Linux | Fedora | Ubuntu |
| --- | --- | --- | --- |
| python3 (dev) | python | python3-devel | python3-dev |
| build tools | base-devel | "Development Tools" | build-essential |
| libusb-1.0 (dev) | libusb-1.0 | libusbx-devel | libusb-1.0-0-dev |
| libudev (dev) | (installed) | (installed) | libudev-dev |

### Additional requirements on Windows

Products that cannot use the generic Microsoft HID Driver require another driver that is compatible with libusb.  In most cases Microsoft's WinUSB driver is recommended, which can be easily configured for a device with [Zadig](https://zadig.akeo.ie/).¹

Pre-build liquidctl executables for Windows already include libusb and HIDAPI, but when installing from PyPI or the sources you will need to manually set up the libusb runtime libraries.  You can get the DLLs from [libusb/releases](https://github.com/libusb/libusb/releases) (part of the `libusb-<version>.7z` files) and extract the appropriate (e.g. MS64) `.dll` and `.lib` files to your system or python installation directory (e.g. `C:\Windows\System32` or `C:\Python36`).  Note that there is a [known issue in PyUSB](https://github.com/pyusb/pyusb/pull/227) that causes errors when the devices are released; the solution is to either manually patch PyUSB or stick to libusb 1.0.21.

_¹ See [How to use libusb under Windows](https://github.com/libusb/libusb/wiki/FAQ#how-to-use-libusb-under-windows) for more information._

### Additional requirements on Mac OS

A [homebrew tap](https://github.com/jonasmalacofilho/homebrew-liquidctl) is provided, and installing liquidctl using it is straightforward.

```
$ brew tap jonasmalacofilho/liquidctl
$ brew install liquidctl
```

The formula can be used to install both the stable version or, by passing `--HEAD`, the latest snapshot from this repository.  All dependencies are be automatically resolved.

If a different installation method is required, libsub must be installed first; the recommended way is with `brew install libusb`.


## Introducing the command-line interface

The complete list of commands and options can be seen with `liquidctl --help`, but a good place to start is to ask liquidctl to list all recognized devices.

```
# liquidctl list
```

In case more than one supported device is found, the desired one can be selected with `--match <substring>`, where `<substring>` matches part of the desired device's description using a case insensitive comparison.

More device properties can be show by passing `--verbose` to `liquidctl list`.  Any of these can also be used to select a particular product.  See `liquidctl --help` or the man page for more information.

Finally, devices can also be selected with `--device <ID>`, but these are not guaranteed to remain stable and will vary with hardware changes, liquidctl updates or simply normal enumeration order variance.

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

Lighting is controlled in a similar fashion and, again, the specific documentation for each device will list the available channels, modes and additional options.

```
# liquidctl [options] set <channel> color <mode> [<color>] ...
```

Finally, the `--verbose` option will print some extra information, like automatically made adjustments to the user provided settings.  And if there is a problem, the `--debug` flag will make liquidctl output more information to help identify its cause; be sure to include this when opening a new issue.

_Note: when debugging issues with PyUSB or libusb it can be useful to set the `PYUSB_DEBUG` (`=debug`) or/and `LIBUSB_DEBUG` (`=4`) environment variables._


## Automation and running at boot

In most cases you will want to automatically apply your settings when the system boots.  Generally a simple script or a basic service is enough, and some specifics about this are given in the following sections.

If you need more control for some really ambitious automation, you can also write a Python program that calls the driver APIs directly.

### Set up Linux using systemd

On systems running Linux and Systemd a service unit can be used to configure liquidctl devices.  A simple example is provided bellow, which you can edit to match your preferences and save the result to `/etc/system.d/system/liquidcfg.service`.

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

A slightly more complex example can be seen at [jonasmalacofilho/dotfiles](https://github.com/jonasmalacofilho/dotfiles/tree/master/liquidctl), which handles multiple devices and uses the LEDs to convey progress and alert of errors.

### Set up Windows using Task Scheduler

The configuration of devices can be automated by writing a batch file and setting up a new scheduled task for (every) log on.  The batch file can be really simple and consist of the invocations of liquidctl that would otherwise be done manually.

```batchfile
liquidctl set pump speed 90
liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
liquidctl set ring color fading 350017 ff2608
liquidctl set logo color spectrum-wave
```

Make sure that liquidctl is available in the context where the batch file will run: in short, `liquidctl --version` should work within a _normal_ Command Prompt window.

When not using a pre-built liquidctl executable, try installing Python with the option to set the PATH variable enabled, or manually add the necessary folders to the PATH. Alternatively, if you're using Anaconda, try adding the following line to the beginning of the file:

```batchfile
call %homepath%\Anaconda3\Scripts\activate.bat
```

A slightly more complex example can be seen in [issue #14](https://github.com/jonasmalacofilho/liquidctl/issues/14#issuecomment-456519098) ("Can I autostart liquidctl on Windows?"), that uses the LEDs to convey progress or eventual errors.

Chris' guide on [Replacing NZXT’s CAM software on Windows for Kraken](https://codecalamity.com/replacing-nzxts-cam-software-on-windows-for-kraken/) goes into a lot more detail and is a good read.

### Set up Mac OS using launchd

You can use a shell script and launchd to automatically configure your devices upon logging in.

Create a script in `/usr/local/bin/liquidcfg.sh` and make it executable; it should contain the calls to liquidctl necessary to initialize and configure your devices.

```bash
#!/bin/bash -xe
liquidctl set pump speed 90
liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
liquidctl set ring color fading 350017 ff2608
liquidctl set logo color spectrum-wave
```

Afterwards, create a new global daemon in `/Library/LaunchDaemons/local.liquidcfg.plist` that executes the previous script.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>ProgramArguments</key>
	<array>
		<string>/usr/local/bin/liquidcfg.sh</string>
	</array>
	<key>Label</key>
	<string>local.liquidcfg</string>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<false/>
	<key>EnvironmentVariables</key>
	<dict>
		<key>PATH</key>
		<string>/Library/Frameworks/Python.framework/Versions/?.?/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
	</dict>
</dict>
</plist>
```

It is important to adjust the location of Python 3 framework in the PATH environment variable above.  launchd agents use the system profile and thus will by default only find the Apple-provided Python 2.7 and its packages.

You can enable and disable the agent with `launchctl load|unload ~/Library/LaunchAgents/local.liquidcfg.plist`.  Errors can be found in `system.log` using Console; search for `liquidcfg` or `liquidctl`.

A real world example can be seen in [icedterminal/ga-z270x-ug](https://github.com/icedterminal/ga-z270x-ug/tree/master/post_install/pump_control).


## License

liquidctl – monitor and control liquid coolers and other devices.  
Copyright (C) 2018–2019  Jonas Malaco  
Copyright (C) 2018–2019  each contribution's author  

liquidctl includes contributions by CaseySJ and other authors.

liquidctl incorporates work by leaty, KsenijaS, Alexander Tong, Jens
Neumaier, Kristóf Jakab, Sean Nelson, Chris Griffith, notaz, realies
and Thomas Pircher.

Depending on how it is packaged, it might also bundle copies of
python, hidapi, libusb, cython-hidapi, pyusb and docopt.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but without any warranty; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.


## Related projects

### [jonasmalacofilho/liquidctl-device-data](https://github.com/jonasmalacofilho/liquidctl-device-data)

Device information for developing and maintaining liquidctl, including USB descriptions, traffic captures and protocol analyses.

### [jonasmalacofilho/liquidtux](https://github.com/jonasmalacofilho/liquidtux)

Ongoing work on Linux kernel _hwmon_ drivers for some of the devices supported by liquidctl.  This allows standard monitoring tools (e.g. lm-sensors or tools built on top of it) to read the sensors in these devices.

### [audiohacked/OpenCorsairLink](https://github.com/audiohacked/OpenCorsairLink)

Command-line tool to control Corsair all-in-one liquid coolers and other devices.

### [jaksi/leviathan](https://github.com/jaksi/leviathan) and [brkalmar/leviathan](https://github.com/brkalmar/leviathan)

Linux kernel device drivers for second and third generation NZXT Kraken X coolers.

### [KsenijaS/krakenx](https://github.com/KsenijaS/krakenx)

A related cross-plataform interface for controlling third generation NZXT Kraken X coolers.

_A special thanks to all krakenx contributors; this project would not exist were not for it._
