# liquidctl – liquid cooler control

_Cross-platform tool and drivers for liquid coolers and other devices_

[![Status of the tests](https://github.com/liquidctl/liquidctl/workflows/tests/badge.svg)](https://github.com/liquidctl/liquidctl/commits/main)
[![Status of the build for Windows](https://ci.appveyor.com/api/projects/status/n5lgebd5m8iomx42/branch/main?svg=true)](https://ci.appveyor.com/project/jonasmalacofilho/liquidctl/branch/main)
[![Developer's Discord server](https://img.shields.io/discord/780568774964805672)](https://discord.gg/GyCBjQhqCd)


```
# liquidctl list
Device #0: ASUS Strix RTX 2080 Ti OC
Device #1: Corsair Vengeance RGB DIMM2
Device #2: Corsair Vengeance RGB DIMM4
Device #3: NZXT Smart Device (V1)
Device #4: NZXT Kraken X (X42, X52, X62 or X72)

# liquidctl initialize all

# liquidctl status --unsafe=smbus,vengeance_rgb
Corsair Vengeance RGB DIMM2
└── Temperature    33.8  °C

Corsair Vengeance RGB DIMM4
└── Temperature    33.8  °C

NZXT Smart Device (V1)
├── Fan 1 speed                 1473  rpm
├── Fan 1 voltage              11.91  V
├── Fan 1 current               0.01  A
├── Fan 1 control mode           PWM
├── Fan 2 [...]
├── Fan 2 [...]
├── Firmware version           1.0.7
├── LED accessories                2
├── LED accessory type    HUE+ Strip
├── LED count (total)             20
└── Noise level                   65  dB

NZXT Kraken X (X42, X52, X62 or X72)
├── Liquid temperature     31.7  °C
├── Fan speed               801  rpm
├── Pump speed             2239  rpm
└── Firmware version      6.0.2  

# liquidctl --match kraken set fan speed  20 30  30 50  34 80  40 90  50 100
# liquidctl --match kraken set pump speed 70
# liquidctl --match "smart device" set sync speed 50

# liquidctl --match kraken set sync color fixed 0080ff
# liquidctl --match "smart device" set led color moving-alternating "hsv(30,98,100)" "hsv(30,98,10)" --speed slower 
# liquidctl --match "rtx 2080" set led color fixed 2aff00 --unsafe=smbus
# liquidctl --match dimm2 set led color fixed "hsl(5, 100, 34)" --unsafe=smbus,vengeance_rgb
# liquidctl --match dimm4 set led color fixed "hsl(5, 100, 34)" --unsafe=smbus,vengeance_rgb
```

<!-- stop here for PyPI -->


## Table of contents

1. [Supported devices](#supported-devices)
1. [Installing on Linux](#installing-on-linux)
1. [Installing on FreeBSD](#installing-on-freebsd)
1. [Installing on Windows](#installing-on-windows)
1. [Installing on macOS](#installing-on-macos)
1. [The command-line interface](#introducing-the-command-line-interface)
     1. [Listing and selecting devices](#listing-and-selecting-devices)
     1. [Initializing and interacting with devices](#initializing-and-interacting-with-devices)
     1. [Supported color specification formats](#supported-color-specification-formats)
1. [Using liquidctl in other programs and scripts](#using-liquidctl-in-other-programs-and-scripts)
1. [Automation and running at boot](#automation-and-running-at-boot)
     1. [Set up Linux using systemd](#set-up-linux-using-systemd)
     1. [Set up Windows using Task Scheduler](#set-up-windows-using-task-scheduler)
     1. [Set up macOS using launchd](#set-up-macos-using-launchd)
1. [Troubleshooting](#troubleshooting)
1. [Additional documentation](#additional-documentation)
1. [License](#license)
1. [Related projects](#related-projects-2020-edition)


## Supported devices

The following devices are supported by this version of liquidctl.  See each guide for specific usage instructions and other pertinent information.

<!-- the table is manually sorted to keep certain devices (confusing Corsair coolers and NZXT Smart Devices) in chronological order -->
<!-- the notes are sorted alphabetically, major (upper case) notes before minor (lower case) ones -->

| Type | Device/guide | Bus | Notes |
| :-: | :-- | :-: | :-- |
| AIO liquid cooler | [Corsair Hydro H80i GT, H100i GTX, H110i GTX](docs/asetek-690lc-guide.md) | USB | <sup>_Ze_</sup> |
| AIO liquid cooler | [Corsair Hydro H80i v2, H100i v2, H115i](docs/asetek-690lc-guide.md) | USB | <sup>_Z_</sup> |
| AIO liquid cooler | [Corsair Hydro H100i Pro, H115i Pro, H150i Pro](docs/asetek-pro-guide.md) | USB | <sup>_Ze_</sup> |
| AIO liquid cooler | [Corsair Hydro H100i Platinum [SE], H115i Platinum](docs/corsair-platinum-pro-xt-guide.md) | USB HID | <sup>_e_</sup> |
| AIO liquid cooler | [Corsair Hydro H100i Pro XT, H115i Pro XT, H150i Pro XT](docs/corsair-platinum-pro-xt-guide.md) | USB HID | <sup>_e_</sup> |
| AIO liquid cooler | [Corsair iCUE H100i, H115i, H150i Elite Capellix](docs/corsair-commander-core-guide.md) | USB HID | <sup>_ep_</sup> |
| AIO liquid cooler | [EVGA CLC 120 (CL12), 240, 280, 360](docs/asetek-690lc-guide.md) | USB | <sup>_Z_</sup> |
| AIO liquid cooler | [NZXT Kraken M22](docs/kraken-x2-m2-guide.md) | USB HID | |
| AIO liquid cooler | [NZXT Kraken X40, X60](docs/asetek-690lc-guide.md) | USB | <sup>_LZe_</sup> |
| AIO liquid cooler | [NZXT Kraken X31, X41, X61](docs/asetek-690lc-guide.md) | USB | <sup>_LZ_</sup> |
| AIO liquid cooler | [NZXT Kraken X42, X52, X62, X72](docs/kraken-x2-m2-guide.md) | USB HID | |
| AIO liquid cooler | [NZXT Kraken X53, X63, X73](docs/kraken-x3-z3-guide.md) | USB HID | |
| AIO liquid cooler | [NZXT Kraken Z53, Z63, Z73](docs/kraken-x3-z3-guide.md) | USB & USB HID | <sup>_ep_</sup> |
| DDR4 DRAM | [Corsair Vengeance RGB](docs/ddr4-guide.md) | SMBus | <sup>_Uax_</sup> |
| DDR4 DRAM | [DIMMs with a standard temperature sensor](docs/ddr4-guide.md) | SMBus | <sup>_Uax_</sup> |
| Fan/LED controller | [Corsair Commander Pro](docs/corsair-commander-guide.md) | USB HID | |
| Fan/LED controller | [Corsair Commander Core](docs/corsair-commander-core-guide.md) | USB HID | <sup>_ep_</sup> |
| Fan/LED controller | [Corsair Lighting Node Core, Pro](docs/corsair-commander-guide.md) | USB HID | <sup>_e_</sup> |
| Fan/LED controller | [Corsair Obsidian 1000D](docs/corsair-commander-guide.md) | USB HID | <sup>_e_</sup> |
| Fan/LED controller | [NZXT Grid+ V3](docs/nzxt-smart-device-v1-guide.md) | USB HID | |
| Fan/LED controller | [NZXT HUE 2, HUE 2 Ambient](docs/nzxt-hue2-guide.md) | USB HID | |
| Fan/LED controller | [NZXT RGB & Fan Controller](docs/nzxt-hue2-guide.md) | USB HID | |
| Fan/LED controller | [NZXT Smart Device](docs/nzxt-smart-device-v1-guide.md) | USB HID | |
| Fan/LED controller | [NZXT Smart Device V2](docs/nzxt-hue2-guide.md) | USB HID | |
| Graphics card | [ASUS Strix GTX 1070](docs/nvidia-guide.md) | I²C | <sup>_Ux_</sup> |
| Graphics card | [ASUS Strix RTX 2080 Ti OC](docs/nvidia-guide.md) | I²C | <sup>_Ux_</sup> |
| Graphics card | [EVGA GTX 1080 FTW](docs/nvidia-guide.md) | I²C | <sup>_Ux_</sup> |
| Motherboard | [Gigabyte RGB Fusion 2.0 motherboards](docs/gigabyte-rgb-fusion2-guide.md) | USB HID | |
| Power supply | [Corsair HX750i, HX850i, HX1000i, HX1200i](docs/corsair-hxi-rmi-psu-guide.md) | USB HID | |
| Power supply | [Corsair RM650i, RM750i, RM850i, RM1000i](docs/corsair-hxi-rmi-psu-guide.md) | USB HID | |
| Power supply | [NZXT E500, E650, E850](docs/nzxt-e-series-psu-guide.md) | USB HID | <sup>_p_</sup> |

<sup>_L_</sup> _Requires the `--legacy-690lc` flag._  
<sup>_U_</sup> _Requires `--unsafe` features._  
<sup>_Z_</sup> _Requires replacing the device driver [on Windows](#installing-on-windows)._  
<sup>_a_</sup> _Architecture-specific limitations._  
<sup>_e_</sup> _Experimental support._  
<sup>_n_</sup> _New driver, only available on git._  
<sup>_p_</sup> _Only partially supported._  
<sup>_x_</sup> _Only supported on Linux._  


## Installing on Linux

<a href="https://repology.org/project/liquidctl/versions">
    <img src="https://repology.org/badge/vertical-allrepos/liquidctl.svg" alt="Packaging status" align="right">
</a>

Packages are available for some Linux distributions.  On others, or when more control is desired, liquidctl can be installed from PyPI or directly from the source code repository.

The following dependencies are required at runtime (common package names are listed in parenthesis):

- Python 3.6+ _(python3, python)_
- pkg_resources Python package _(python3-setuptools, python3-pkg-resources, python-setuptools)_
- docopt _(python3-docopt, python-docopt)_
- colorlog _(python3-colorlog, python-colorlog)_
- cython-hidapi _(python3-hidapi, python3-hid, python-hidapi)_
- PyUSB _(python3-pyusb, python3-usb, python-pyusb)_
- smbus Python package _(python3-i2c-tools, python3-smbus, i2c-tools)_
- LibUSB 1.0 _(libusb-1.0, libusb-1.0-0, libusbx)_

To locally test and manually install, a few more dependencies are needed:

- setuptools Python package _(python3-setuptools, python-setuptools)_
- pip (optional) _(python3-pip, python-pip)_
- pytest (optional) _(python3-pytest, pytest, python-pytest)_

Finally, if cython-hidapi will be installed from source or directly from PyPI, then some additional build tools and development headers may also be required:

- Python development headers _(python3-dev, python3-devel)_
- LibUSB 1.0 development headers _(libusb-1.0-0-dev, libusbx-devel)_
- libudev developemnt headers _(libudev-dev, libudev-devel)_

Once all necessary dependencies are installed, *pip* can be used to install a release from PyPI:

```
# pip install liquidctl
# pip install liquidctl==<version>
```

For the latest changes and to contribute back to the project, it is best to clone the source code repository.  You can directly execute the code, or install it from that local copy.

```
$ git clone https://github.com/liquidctl/liquidctl
$ cd liquidctl
$ pytest  # optional step
$ python -m liquidctl.cli <args>...
# pip install .
```

_Note: in systems that default to Python 2, use `pip3`, `python3` and `pytest-3`._  

Optional steps:

- install man pages
```
# cp liquidctl.8 /usr/local/share/man/man8/
# mandb
```
- install [udev rules] for unprivileged access to devices
- install [bash completions] for liquidctl

[udev rules]: extra/linux/71-liquidctl.rules
[bash completions]: extra/completions/liquidctl.bash


## Installing on FreeBSD

liquidctl is maintained in the FreeBSD Ports Collection, and it is available as a pre-built binary package.

- port: `sysutils/py-liquidctl`
- binary: `pkg install py37-liquidctl`
- dependencies: `devel/py-docopt`, `comms/py-hidapi`, `devel/py-pyusb`

By default, root privileges (`doas` or `sudo`) are required to run liquidctl.

To gain full access as a normal user without `doas` or `sudo`, see devd(8). Also, you might consider manually changing the permission of the file of the USB device for an individual session with `chown`, e.g. `sudo chown [user] /dev/ugen[#.#]`.

### DragonFly BSD

The port is also available in DragonFly Ports.


## Installing on Windows

A pre-built executable for the last stable version is available in [liquidctl-1.7.0-bin-windows-x86_64.zip](https://github.com/liquidctl/liquidctl/releases/download/v1.7.0/liquidctl-1.7.0-bin-windows-x86_64.zip).

Executables for previous releases can be found in the assets of the [Releases](https://github.com/liquidctl/liquidctl/releases) tab, and development builds can be found in the artifacts on the [AppVeyor runs](https://ci.appveyor.com/project/jonasmalacofilho/liquidctl/history).

Products that are not Human Interface Devices (HIDs), or that do not use the Microsoft HID Driver, require a libusb-compatible driver, see notes in [Supported devices](#supported-devices)).  In most cases Microsoft WinUSB is recommended, which can easily be set up for a device with [Zadig](https://zadig.akeo.ie/):¹ open the application, click `Options`, `List All Devices`, then select your device from the dropdown list, and click "Replace Driver".  Note that replacing the driver for devices that do not require it will likely cause them to disapear from liquidctl.

The pre-built executables can be directly used from a Windows Command Prompt, Power Shell or other available terminal emulator.  Even so, most users will want to place the executable in a directory listed in [the `PATH` environment variable](https://en.wikipedia.org/wiki/PATH_(variable)), or change the variable so that is true; this allows omitting the full path and `.exe` extension when calling `liquidctl`.

_Alternatively to the pre-built executable,_ it is possible to install liquidctl from PyPI or directly from the source code repository.  This is useful to contribute fixes or improvements to liquidctl, or to use advanced features like the liquidctl API.

Since HWiNFO 6.10 it is possible for other programs to send additional sensor data in through a Windows Registry API, and [`LQiNFO.py`](extra/windows/LQiNFO.py) is an experimental program that uses the liquidctl API to take advantage of this feature.

Pre-build liquidctl executables for Windows already include Python and libusb, but when installing from PyPI or the sources both of these will need to be manually set up.  The libusb DLLs can be found in [libusb/releases](https://github.com/libusb/libusb/releases) (part of the `libusb-<version>.7z` files) and the appropriate (e.g. MS64) `.dll` and `.lib` files should be extracted to the system or python installation directory (e.g. `C:\Windows\System32` or `C:\Python36`).

To install any release from PyPI, *pip* should be used:

```
> pip install liquidctl
> pip install liquidctl==<version>
```

For the latest changes and to contribute back to the project, it is best to clone the source code repository.  You can directly execute the code, or install it from that local copy.

```
> git clone https://github.com/liquidctl/liquidctl
> cd liquidctl
> python -m liquidctl.cli <args>...
> pip install .
```

_¹ See [How to use libusb under Windows](https://github.com/libusb/libusb/wiki/FAQ#how-to-use-libusb-under-windows) for more information._


## Installing on macOS

liquidctl is available on Homebrew, and that is the preferred method of installing it.

```
$ brew install liquidctl
$ brew install liquidctl --HEAD
```

By default the last stable version will be installed, but by passing `--HEAD` this can be changed to the last snapshot from this repository.  All dependencies are automatically resolved.

Another possibility is to install liquidctl from PyPI or directly from the source code repository, but in these cases Python 3 and libsub must be installed first; the recommended way is with `brew install python libusb`.

To install any release from PyPI, *pip* should be used:

```
$ pip3 install liquidctl
$ pip3 install liquidctl==<version>
```

For the latest changes and to contribute back to the project, it is best to clone the source code repository.  You can directly execute the code, or install it from that local copy.

```
$ git clone https://github.com/liquidctl/liquidctl
$ cd liquidctl
$ python3 -m liquidctl.cli <args>...
$ pip3 install .
```

_Note: installation into a virtual environment is recommended to avoid conflicts with Python modules installed with Homebrew.  The use of virtual environments is outside the scope of this document.  Their use will also restrict the availability of the liquidctl command to that virtual environment._


## Introducing the command-line interface

The complete list of commands and options can be found in `liquidctl --help` and in the man page, but the following topics cover the most common operations.

Brackets `[ ]`, parenthesis `( )`, less than/greater than `< >` and ellipsis `...` are used to describe, respectively, optional, required, positional and repeating elements.  Example commands are prefixed with a number sign `#`, which also serves to indicate that on Linux root permissions (or suitable udev rules) may be required.

The `--verbose` option will print some extra information, like automatically made adjustments to user-provided settings.  And if there is a problem, the `--debug` flag will make liquidctl output more information to help identify its cause; be sure to include this when opening a new issue.

_Note: when debugging issues with PyUSB or libusb it can be useful to set the `PYUSB_DEBUG=debug` or/and `LIBUSB_DEBUG=4` environment variables._

### Listing and selecting devices

A good place to start is to ask liquidctl to list all recognized devices.

```
# liquidctl list
Device #0: NZXT Smart Device (V1)
Device #1: NZXT Kraken X (X42, X52, X62 or X72)
```

In case more than one supported device is found, one them can be selected with `--match <substring>`, where `<substring>` matches part of the desired device's description using a case insensitive comparison.

```
# liquidctl --match kraken list
Result #0: NZXT Kraken X (X42, X52, X62 or X72)
```

More device properties can be show by passing `--verbose` to `liquidctl list`.  Any of those can also be used to select a particular product.

```
# liquidcl --bus hid --address /dev/hidraw4 list
Result #0: NZXT Smart Device (V1)

# liquidctl --serial 1234567890 list
Result #0: NZXT Kraken X (X42, X52, X62 or X72)
```

Ambiguities for any given filter can be solved with `--pick <number>`.

### Initializing and interacting with devices

Devices will usually need to be initialized before they can be used, though each device has its own requirements and limitations.  This and other information specific to a particular device will appear on the documentation linked from the [supported devices](#supported-devices) section.

Devices can be initialized individually or all at once.

```
# liquidctl [options] initialize [all]
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

Lighting is controlled in a similar fashion.  The specific documentation for each device will list the available channels, modes and additional options.

```
# liquidctl [options] set <channel> color <mode> [<color>] ...
```

### Supported color specification formats

When configuring lighting effects, colors can be specified in different representations and formats:

 - as an implicit hexadecimal RGB triple, either with or without the `0x` prefix: e.g. `ff7f3f`
 - as an explicit RGB triple: e.g. `rgb(255, 127, 63)`
 - as a HSV (hue‑saturation‑value) triple: e.g. `hsv(20, 75, 100)`
    * hue ∊ [0, 360] (degrees); saturation, value ∊ [0, 100] (percent)
    * note: this is sometimes called HSB (hue‑saturation‑brightness)
  - as a HSL (hue‑saturation‑lightness) triple: e.g. `hsl(20, 100, 62)`
    * hue ∊ [0, 360] (degrees); saturation, lightness ∊ [0, 100] (percent)

Color arguments containing spaces, parenthesis or commas need to be quoted, as these characters can have special meaning on the command-line; the easiest way to do this on all supported platforms is with double quotes.

```
# liquidctl --match kraken set ring color fading "hsv(0,80,100)" "hsv(180,80,100)"
```

On Linux it is also possible to use single-quotes and `\(`, `\)`, `\ ` escape sequences.


## Using liquidctl in other programs and scripts

The liquidctl driver APIs can be used to build Python programs that monitor or
control the devices, and offer features beyond the ones provided by the CLI.

The APIs are documented, and this documentation can be accessed through
`pydoc`, or directly read from the source files.

```python
from liquidctl import find_liquidctl_devices

first = True

# find all connected and supported devices
devices = find_liquidctl_devices()

for dev in devices:

    # connect to the device (here a context manager is used, but the
    # connection can also be manually managed)
    with dev.connect():
        print(f'{dev.description} at {dev.bus}:{dev.address}:')

        # devices should be initialized after every boot (here we assume
        # this has not been done before)
        init_status = dev.initialize()

        # print all data returned by initialize()
        if init_status:
            for key, value, unit in init_status:
                print(f'{key}: {value} {unit}')

        # get regular status information from the device
        status = dev.get_status()

        # print all data returned by get_status()
        for key, value, unit in status:
            print(f'{key}: {value} {unit}')

        # for a particular device, set the pump LEDs to red
        if 'Kraken' in dev.description:
            print('setting pump to radical red')
            radical_red = [0xff, 0x35, 0x5e]
            dev.set_color(channel='pump', mode='fixed', colors=[radical_red])

    # the context manager took care of automatically calling disconnect();
    # when manually managing the connection, disconnect() must be called at
    # some point even if an exception is raised

    if first:
        first = False
        print()  # add a blank line between each device
```

More examples can be found in the scripts in [`extra/`](extra/).

In addition to the APIs, the `liquidctl` CLI is friendly to scripting: errors
cause it to exit with non-zero codes and only functional output goes to
`stdout`, everything else (error messages, warnings and other auxiliary
information) going to `stderr`.

The `list`, `initialize` and `status` commands also support a `--json` flag to
switch the output to JSON, a more convenient format for machines and scripts.
In `--json` mode, setting `LANG=C` on the environment causes non-ASCII
characters to be escaped.

```
# liquidctl --match kraken list --json | jq
[
  {
    "description": "NZXT Kraken X (X42, X52, X62 or X72)",
    "vendor_id": 7793,
    "product_id": 5902,
    "release_number": 512,
    "serial_number": "49874481333",
    "bus": "hid",
    "address": "/dev/hidraw3",
    "port": null,
    "driver": "Kraken2",
    "experimental": false
  },
  ...
]

# liquidctl --match kraken status --json | jq
[
  {
    "bus": "hid",
    "address": "/dev/hidraw3",
    "description": "NZXT Kraken X (X42, X52, X62 or X72)",
    "status": [
      {
        "key": "Liquid temperature",
        "value": 30.1,
        "unit": "°C"
      },
      {
        "key": "Fan speed",
        "value": 1014,
        "unit": "rpm"
      },
      ...
    ]
  },
  ...
]
```

Note that the examples above pipe the output to [jq], as the original output
has no line breaks or indentation.  An alternative to jq is to use [`python -m
json.tool`][json.tool], which is already included in standard Python
distributions.

Finally, the stability of both the APIs and the CLI commands is documented in
our [stability guarantee].  In particular, the specific keys, values and units
returned by the commands above, as well as their API equivalents, _are subject
to changes._  Consumers should verify that the returned data matches their
expectations, and react accordingly.

[jq]: https://stedolan.github.io/jq/
[json.tool]: https://docs.python.org/3/library/json.html#module-json.tool
[stability guarantee]: docs/developer/process.md#stability-and-backward-compatibility


## Automation and running at boot

In most cases you will want to automatically apply your settings when the system boots.  Generally a simple script or a basic service is enough, and some specifics about this are given in the following sections.

For even more flexibility, you can also write a Python program that calls the driver APIs directly.

### Set up Linux using systemd

On systems running Linux and systemd a service unit can be used to configure liquidctl devices.  A simple example is provided bellow, which you can edit to match your preferences.  Save it to `/etc/systemd/system/liquidcfg.service`.

```
[Unit]
Description=AIO startup service

[Service]
Type=oneshot
ExecStart=liquidctl initialize all
ExecStart=liquidctl --match kraken set pump speed 90
ExecStart=liquidctl --match kraken set fan speed  20 30  30 50  34 80  40 90  50 100
ExecStart=liquidctl --match "smart device" set sync speed 55
ExecStart=liquidctl --match kraken set sync color fading 350017 ff2608

[Install]
WantedBy=default.target
```

After reloading the configuration, the new unit can be started manually or set to automatically run during boot using standard systemd tools.

```
# systemctl daemon-reload
# systemctl start liquidcfg
# systemctl enable liquidcfg
```

A slightly more complex example can be seen at [jonasmalacofilho/dotfiles](https://github.com/jonasmalacofilho/dotfiles/tree/master/liquidctl), which includes dynamic adjustments of the lighting depending on the time of day.

If necessary, it is also possible to have the service unit explicitly wait for the device to be available: see [making systemd units wait for devices](docs/linux/making-systemd-units-wait-for-devices.md).

### Set up Windows using Task Scheduler

The configuration of devices can be automated by writing a batch file and setting up a new task for (every) login using Windows Task Scheduler.  The batch file can be really simple and only needs to contain the invocations of liquidctl that would otherwise be done manually.

```batchfile
liquidctl initialize all
liquidctl --match kraken set pump speed 90
liquidctl --match kraken set fan speed  20 30  30 50  34 80  40 90  50 100
liquidctl --match "smart device" set sync speed 55
liquidctl --match kraken set sync color fading 350017 ff2608
```

Make sure that liquidctl is available in the context where the batch file will run: in short, `liquidctl --version` should work within a _normal_ Command Prompt window.

When not using a pre-built liquidctl executable, try installing Python with the option to set the PATH variable enabled, or manually add the necessary folders to the PATH.

A slightly more complex example can be seen in [issue #14](https://github.com/liquidctl/liquidctl/issues/14#issuecomment-456519098) ("Can I autostart liquidctl on Windows?"), that uses the LEDs to convey progress or eventual errors.  Chris' guide on [Replacing NZXT’s CAM software on Windows for Kraken](https://codecalamity.com/replacing-nzxts-cam-software-on-windows-for-kraken/) is also a good read.

As an alternative to using Task Scheduler, the batch file can simply be placed in the startup folder; you can run `shell:startup` to [find out where that is](https://support.microsoft.com/en-us/help/4026268/windows-10-change-startup-apps).

### Set up macOS using launchd

You can use a shell script and launchd to automatically configure your devices during login or after waking from sleep.  A [detailed guide](https://www.tonymacx86.com/threads/gigabyte-z490-vision-d-thunderbolt-3-i5-10400-amd-rx-580.298642/page-24#post-2138475) is available on tonymacx86.


## Troubleshooting

### Device not listed (Windows)

This is likely caused by having replaced the standard driver of a USB HID.  If the device in question is not marked in [Supported devices](#supported-devices) as requiring a special driver, try uninstalling the custom driver.

### Device not listed (Linux)

This is usually caused by having an unexpected kernel driver bound to a USB HID.  In most cases this is the result of having used a program that accessed the device (directly or indirectly) via libusb-1.0, but failed to reattach the original driver before terminating.

This can be temporarily solved by manually rebinding the device to the kernel `usbhid` driver. Replace `<bus>` and `<port>` with the correct values from `lsusb -vt` (also assumes there is only HID interface, adjust if necessary):

```
echo '<bus>-<port>:1.0' | sudo tee /sys/bus/usb/drivers/usbhid/bind
```

A more permanent solution is to politely ask the authors of the program that is responsible for leaving the kernel driver detached to use `libusb_attach_kernel_driver` or `libusb_set_auto_detach_kernel_driver`.

### Access denied or open failed (Linux)

These errors are usually caused by a lack of permission to access the device.  On Linux distros that normally requires root privileges.

Alternatively to running liquidctl as root (or with `sudo`), you can install the udev rules provided in [`extra/linux/71-liquidctl.rules`](extra/linux/71-liquidctl.rules) to allow unprivileged access to the devices supported by liquidctl.

### Other problems

If your problem is not listed here, try searching the [issues](https://github.com/liquidctl/liquidctl/issues).  If no issue matches your problem, you still need help, or you have found a bug, please open one.

When commenting on an issue, please describe the problem in as much detail as possible.  List your operating system and the specific devices you own.

Also include the arguments and output of all relevant/failing liquidctl commands, using the `--debug` option to enable additional debug information.


## Additional documentation

Be sure to browse [`docs/`](docs/) for additional documentation, and [`extra/`](extra/) for some example scripts and other possibly useful things.

You are also encouraged to contribute to the documentation and to these examples, including adding new files that cover your specific use cases or solutions.


## License

liquidctl – monitor and control liquid coolers and other devices.  
Copyright (C) 2018–2021  Jonas Malaco, Marshall Asch, CaseySJ, Tom Frey, Andrew
Robertson  and contributors

liquidctl incorporates work by leaty, Ksenija Stanojevic, Alexander Tong, Jens
Neumaier, Kristóf Jakab, Sean Nelson, Chris Griffith, notaz, realies and Thomas
Pircher.

Depending on how it is packaged, it might also bundle copies of python, hidapi,
libusb, cython-hidapi, pyusb, docopt, colorlog and colorama.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but without any
warranty; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

This project uses [short SPDX License List identifiers][SPDX-Short-Identifiers]
to concisely and unambiguously indicate the applicable license in each source
file.

[SPDX-Short-Identifiers]: https://spdx.github.io/spdx-spec/appendix-V-using-SPDX-short-identifiers-in-source-files/


## Related projects

### [liquidctl/liquidtux](https://github.com/liquidctl/liquidtux)

Sibling project of Linux kernel _hwmon_ drivers for devices supported by
liquidctl.

### [CalcProgrammer1/OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB)

Graphical interface to control many different types of RGB devices.

### [leinardi/GKraken](https://gitlab.com/leinardi/gkraken)

Graphical interface for NZXT Kraken X and Z coolers, using the liquidctl APIs.

### [audiohacked/OpenCorsairLink](https://github.com/audiohacked/OpenCorsairLink)

Retired in 2020, but a great source of information on how Corsair devices work.
There are ongoing efforts to port the last drivers to liquidctl, and joining
them is a great way to get involved.

### [liquidctl/collected-device-data](https://github.com/liquidctl/collected-device-data)

Device information collected for developing and maintaining liquidctl.
