# liquidctl – liquid cooler control

_Cross-platform tool and drivers for liquid coolers and other devices_

[![Status of the tests](https://github.com/liquidctl/liquidctl/workflows/tests/badge.svg)](https://github.com/liquidctl/liquidctl/commits/main)
[![Developer's Discord server](https://img.shields.io/discord/780568774964805672)](https://discord.gg/GyCBjQhqCd)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4949/badge)](https://bestpractices.coreinfrastructure.org/projects/4949)

---

Notice: please check out our [open invitation for new team members](https://github.com/liquidctl/liquidctl/issues/569).

---

```
$ liquidctl list
Device #0: Corsair Vengeance RGB DIMM2
Device #1: Corsair Vengeance RGB DIMM4
Device #2: NZXT Smart Device (V1)
Device #3: NZXT Kraken X (X42, X52, X62 or X72)

# liquidctl initialize all
NZXT Smart Device (V1)
├── Firmware version             1.7
├── LED accessories                2
├── LED accessory type    HUE+ Strip
└── LED count (total)             20

NZXT Kraken X (X42, X52, X62 or X72)
└── Firmware version    6.2

# liquidctl status
NZXT Smart Device (V1)
├── Fan 1 speed            1499  rpm
├── Fan 1 voltage         11.91  V
├── Fan 1 current          0.05  A
├── Fan 1 control mode      PWM
├── Fan 2 [...]
├── Fan 3 [...]
└── Noise level              61  dB

NZXT Kraken X (X42, X52, X62 or X72)
├── Liquid temperature    34.7  °C
├── Fan speed              798  rpm
└── Pump speed            2268  rpm

# liquidctl status --match vengeance --unsafe=smbus,vengeance_rgb
Corsair Vengeance RGB DIMM2
└── Temperature    37.5  °C

Corsair Vengeance RGB DIMM4
└── Temperature    37.8  °C

# liquidctl --match kraken set fan speed  20 30  30 50  34 80  40 90  50 100
# liquidctl --match kraken set pump speed 70
# liquidctl --match kraken set sync color fixed 0080ff
# liquidctl --match "smart device" set led color moving-alternating "hsv(30,98,100)" "hsv(30,98,10)" --speed slower
```


## Contents
[Contents]: #contents

1. [Supported devices]
1. [Installation]
    1. [Linux distributions]
    1. [macOS Homebrew]
    2. [FreeBSD and DragonFly BSD Ports]
    1. [Manual installation]
        1. [Linux dependencies]
        1. [macOS system dependencies]
        1. [Windows system dependencies]
        1. [Creating a virtual environment]
        1. [Installing from PyPI or GitHub]
        1. [Allowing access to the devices]
        1. [Additional files]
    1. [Working locally]
1. [The command-line interface]
    1. [Listing and selecting devices]
    1. [Initializing and interacting with devices]
    1. [Supported color specification formats]
1. [Using liquidctl in other programs and scripts]
1. [Automation and running at boot]
    1. [Set up Linux using systemd]
    1. [Set up Windows using Task Scheduler]
    1. [Set up macOS using various methods]
1. [Troubleshooting]
1. [Additional documentation]
1. [License]
1. [Related projects]


## Supported devices
[Supported devices]: #supported-devices

The following devices are supported by liquidctl.  In the table, MRLV stands
for the _minimum recommended liquidctl version._  The linked documents contain
specific usage instructions and other useful information.

<!--

The table is manually sorted to keep certain device families, like confusing
generations of Corsair coolers and NZXT Smart Devices, in chronological order.

Common prefixes or suffixes are deduplicated and brought before device
differentiators: for example, "Platinum H100i, H100i SE, H115i" instead of
"H100i Platinum, H100i Platinum SE, H115i Platinum".

Newly supported devices are added with the `n` note.  If they are members of an
already supported family, the family is temporarily split between old and new
devices until the next release.

Within a category, the notes are sorted alphabetically, major (upper case)
notes before minor (lower case) ones.  Categories are sorted in a somewhat
subjective "from more to less liquid control-ly" order.

-->

| Type               | Device family and specific documentation | Notes | MRLV |
| :--                | :-- | --: | :-: |
| AIO liquid cooler  | [Corsair Hydro H80i GT, H100i GTX, H110i GTX](docs/asetek-690lc-guide.md) | <sup>_Ze_</sup> | 1.9.1 |
| AIO liquid cooler  | [Corsair Hydro H80i v2, H100i v2, H115i](docs/asetek-690lc-guide.md) | <sup>_Z_</sup> | 1.9.1 |
| AIO liquid cooler  | [Corsair Hydro Pro H100i, H115i, H150i](docs/asetek-pro-guide.md) | <sup>_Z_</sup> | 1.9.1 |
| AIO liquid cooler  | [Corsair Hydro Platinum H100i, H100i SE, H115i](docs/corsair-platinum-pro-xt-guide.md) | | 1.8.1 |
| AIO liquid cooler  | [Corsair Hydro Pro XT H60i, H100i, H115i, H150i](docs/corsair-platinum-pro-xt-guide.md) | | 1.8.1 |
| AIO liquid cooler  | [Corsair iCUE Elite Capellix H100i, H115i, H150i](docs/corsair-commander-core-guide.md) | <sup>_ep_</sup> | 1.11.1 |
| AIO liquid cooler  | [Corsair iCUE Elite RGB H100i](docs/corsair-platinum-pro-xt-guide.md) | <sup>_e_</sup> | git |
| AIO liquid cooler  | [EVGA CLC 120 (CL12), 240, 280, 360](docs/asetek-690lc-guide.md) | <sup>_Z_</sup> | 1.9.1 |
| AIO liquid cooler  | [NZXT Kraken M22](docs/kraken-x2-m2-guide.md) | | 1.10.0 |
| AIO liquid cooler  | [NZXT Kraken X40, X60](docs/asetek-690lc-guide.md) | <sup>_LZe_</sup> | 1.9.1 |
| AIO liquid cooler  | [NZXT Kraken X31, X41, X61](docs/asetek-690lc-guide.md) | <sup>_LZ_</sup> | 1.9.1 |
| AIO liquid cooler  | [NZXT Kraken X42, X52, X62, X72](docs/kraken-x2-m2-guide.md) | <sup>_h_</sup> | 1.11.1 |
| AIO liquid cooler  | [NZXT Kraken X53, X63, X73](docs/kraken-x3-z3-guide.md) | <sup>_h_</sup> | 1.11.1 |
| AIO liquid cooler  | [NZXT Kraken Z53, Z63, Z73](docs/kraken-x3-z3-guide.md) | <sup>_he_</sup> | 1.11.1 |
| Pump controller    | [Aquacomputer D5 Next](docs/aquacomputer-d5next-guide.md) | <sup>_ehp_</sup> | 1.11.1 |
| Fan/LED controller | [Aquacomputer Octo](docs/aquacomputer-octo-guide.md) | <sup>_ehp_</sup> | 1.11.1 |
| Fan/LED controller | [Aquacomputer Quadro](docs/aquacomputer-quadro-guide.md) | <sup>_ehp_</sup> | 1.11.1 |
| Fan/LED controller | [Corsair Commander Pro](docs/corsair-commander-guide.md) | <sup>_h_</sup> | 1.11.1 |
| Fan/LED controller | [Corsair Commander Core, Core XT](docs/corsair-commander-core-guide.md) | <sup>_ep_</sup> | 1.11.1 |
| Fan/LED controller | [Corsair Commander ST](docs/corsair-commander-core-guide.md) | <sup>_ep_</sup> | 1.12.1 |
| Fan/LED controller | [Corsair Lighting Node Core, Pro](docs/corsair-commander-guide.md) | | 1.8.1 |
| Fan/LED controller | [Corsair Obsidian 1000D](docs/corsair-commander-guide.md) | | 1.9.1 |
| Fan/LED controller | [NZXT Grid+ V3](docs/nzxt-smart-device-v1-guide.md) | <sup>_h_</sup> | 1.11.1 |
| Fan/LED controller | [NZXT HUE 2, HUE 2 Ambient](docs/nzxt-hue2-guide.md) | | 1.7.2 |
| Fan/LED controller | [NZXT RGB & Fan Controller](docs/nzxt-hue2-guide.md) | <sup>_h_</sup> | 1.11.1 |
| Fan/LED controller | [NZXT RGB & Fan Controller (3+6 channels)](docs/nzxt-hue2-guide.md) | <sup>_ehp_</sup> | 1.12.1 |
| Fan/LED controller | [NZXT Smart Device](docs/nzxt-smart-device-v1-guide.md) | <sup>_h_</sup> | 1.11.1 |
| Fan/LED controller | [NZXT Smart Device V2](docs/nzxt-hue2-guide.md) | <sup>_h_</sup> | 1.11.1 |
| Fan/LED controller | [NZXT H1 V2](docs/nzxt-hue2-guide.md) | <sup>_e_</sup> | 1.10.0 |
| DDR4 memory        | [Corsair Vengeance RGB](docs/ddr4-guide.md) | <sup>_Uax_</sup> | 1.7.2 |
| DDR4 memory        | [Generic DDR4 temperature sensor](docs/ddr4-guide.md) | <sup>_Uax_</sup> | 1.8.1 |
| Power supply       | [Corsair HX750i, HX850i, HX1000i, HX1200i](docs/corsair-hxi-rmi-psu-guide.md) | <sup>_h_</sup> | 1.12.1 |
| Power supply       | [Corsair HX1000i (2022), HX1500i](docs/corsair-hxi-rmi-psu-guide.md) | <sup>_eh_</sup> | git |
| Power supply       | [Corsair RM650i, RM750i, RM850i, RM1000i](docs/corsair-hxi-rmi-psu-guide.md) | <sup>_h_</sup> | 1.12.1 |
| Power supply       | [NZXT E500, E650, E850](docs/nzxt-e-series-psu-guide.md) | <sup>_p_</sup> | 1.7.2 |
| LED controller     | [Aquacomputer Farbwerk 360](docs/aquacomputer-farbwerk360-guide.md) | <sup>_ehp_</sup> | 1.11.1 |
| Graphics card RGB  | [Select ASUS GTX and RTX cards](docs/nvidia-guide.md) | <sup>_Ux_</sup> | 1.9.1 |
| Graphics card RGB  | [Select EVGA GTX 1070, 1070 Ti and 1080 cards](docs/nvidia-guide.md) | <sup>_Ux_</sup> | 1.9.1 |
| Motherboard RGB    | [ASUS Aura LED motherboards](docs/asus-aura-led-guide.md) | <sup>_e_</sup> | 1.10.0 |
| Motherboard RGB    | [Gigabyte RGB Fusion 2.0 motherboards](docs/gigabyte-rgb-fusion2-guide.md) | | 1.5.2 |

<sup>_L_</sup> _Requires the `--legacy-690lc` flag._<br>
<sup>_U_</sup> _Requires `--unsafe` features._<br>
<sup>_Z_</sup> _Requires replacing the device driver [on Windows][Windows system dependencies]._<br>
<sup>_a_</sup> _Architecture-specific limitations._<br>
<sup>_e_</sup> _Experimental support._<br>
<sup>_h_</sup> _Can leverage hwmon driver._<br>
<sup>_p_</sup> _Only partially supported._<br>
<sup>_x_</sup> _Only supported on Linux._<br>


## Installation
[Installation]: #installation

The following sections cover the various methods to set up liquidctl.

### Linux distributions
[Linux distributions]: #linux-distributions

A considerable number of Linux distributions already package liquidctl,
generally at fairly recent versions.

```bash
# Alpine
sudo apk add liquidctl

# Arch/Artix/[Manjaro]/Parabola
sudo pacman -S liquidctl

# Fedora
sudo dnf install liquidctl

# Manjaro
sudo pamac install liquidctl

# Nix
nix-env -iA nixos.liquidctl
```

liquidctl is also available in some non-official/community-based repositories,
as well as, at older versions, for more distributions.  [Repology] shows more
information about the packaging status in various distributions.

[Repology]: https://repology.org/project/liquidctl/versions

### macOS Homebrew
[macOS Homebrew]: #macos-homebrew

For macOS, liquidctl is available on Homebrew, generally at the most recent
version.  It is also easy to install the latest development snapshot from the
official source code repository.

```bash
# latest stable version
brew install liquidctl

# or latest development snapshot from the official source code repository
brew install liquidctl --HEAD
```

### FreeBSD and DragonFly BSD Ports
[FreeBSD and DragonFly BSD Ports]: #freebsd-and-dragonfly-bsd-ports

On FreeBSD and DragonFly BSD, liquidctl is maintained in the Ports Collections,
and is available as a pre-built binary package.

```
pkg install py37-liquidctl
```

### Manual installation
[Manual installation]: #manual-installation

_Warning: on systems that still default to Python 2, replace `python`
with `python3`._

_Changed in 1.9.0: liquidctl now uses a PEP 517 build system._<br>

liquidctl can be manually installed from the Python Package Index (PyPI), or
directly from the source code repository.

In order to manually install it, certain system-level dependencies must be
satisfied first.  In some cases it may also be preferable to use the Python
libraries already provided by the operating system.

#### Linux dependencies
[Linux dependencies]: #linux-dependencies

On Linux, the following dependencies are required at runtime (common package
names are listed in parenthesis):

- Python 3.7 or later _(python3, python)_
- pkg\_resources Python package _(python3-setuptools, python3-pkg-resources, python-setuptools)_
- PyUSB _(python3-pyusb, python3-usb, python-pyusb)_
- colorlog _(python3-colorlog, python-colorlog)_
- crcmod 1.7 _(python3-crcmod, python-crcmod)_
- cython-hidapi _(python3-hidapi, python3-hid, python-hidapi)_
- docopt _(python3-docopt, python-docopt)_
- pillow _(python-pillow, python3-pil)_
- smbus Python package _(python3-i2c-tools, python3-smbus, i2c-tools)_
- LibUSB 1.0 _(libusb-1.0, libusb-1.0-0, libusbx)_

Additionally, to build, install and test liquidctl, the following are also
needed:

- setuptools\_scm Python package _(python3-setuptools-scm, python3-setuptools_scm, python-setuptools-scm)_
- pip (optional) _(python3-pip, python-pip)_
- pytest (optional) _(python3-pytest, pytest, python-pytest)_

#### macOS system-level dependencies
[macOS system dependencies]: #macos-system-level-dependencies

On macOS, Python (3.7 or later) and LibUSB 1.0 must be installed beforehand.

```
brew install python libusb
```

#### Windows system-level dependencies
[Windows system dependencies]: #windows-system-level-dependencies

On Windows, Python (3.7 or later) must be installed beforehand, which can be
done from the [official website][python.org].  It is recommended to select the
option to add `python` and other tools to the `PATH`.

A LibUSB 1.0 DLL is also necessary, but it will generally be provided
automatically by liquidctl. In case that's not possible, and a USB "No backend
available" error is shown, the suitable DLL from an official [LibUSB release]
should be copied into `C:\Windows\System32\`. The DLL must match your Python
installation: in most cases it will be latest VS build for x64 in the archive
from LibUSB (e.g. `VS2015-x64/dll/libusb-1.0.dll`).

Additionally, products that are not Human Interface Devices (HIDs), or that do
not use the Microsoft HID Driver, require a libusb-compatible driver (these are
listed in [Supported devices] with a `Z` note).  In most cases of these cases
the Microsoft WinUSB driver is recommended, and it can easily be set up for a
device using [Zadig]: open Zadig, select your device from the dropdown list
and, finally, click "Replace Driver".

_Warning: replacing the driver for a device where that is not necessary will
likely cause it to become inaccessible from liquidctl._<br>

_Changed in 1.9.0: a LibUSB 1.0 DLL is now provided by libusb-package, provided
there are suitable wheels available at the time of installation._<br>

[python.org]: https://www.python.org/
[LibUSB release]: https://github.com/libusb/libusb/releases
[Zadig]: https://zadig.akeo.ie/

#### Creating a virtual environment
[Creating a virtual environment]: #creating-a-virtual-environment

Setting up a virtual environment is an optional step.  Even so, installing
Python packages directly in the global environment is not generally advised.

Instead, it is usual to first set up a [virtual environment]:

```bash
# create virtual enviroment at <path>
python -m venv <path>
```

Once set up, the virtual environment can be activated on the current shell
(more information in the [official documentation][virtual environment]).
Alternatively, the virtual environment can also be used directly, without
activation, by prefixing all `python` invocations with the environment's bin
directory.

```bash
# Linux/macOS/BSDs (POSIX)
<path>/bin/python [arguments]

# Windows
<path>\Scripts\python [arguments]
```

[virtual environment]: https://docs.python.org/3/library/venv.html

#### Installing from PyPI or GitHub
[Installing from PyPI or GitHub]: #installing-from-pypi-or-github

[pip] can be used to install liquidctl from the Python Package Index (PyPI).
This will also install the necessary Python libraries.


```bash
# the latest stable version
python -m pip install liquidctl

# a specific version (e.g. 1.12.1)
python -m pip install liquidctl==1.12.1
```

If [git] is installed, pip can also install the latest snapshot of the official
liquidctl source code repository on GitHub.

```bash
# the latest snapshot of the official source code repository (requires git)
python -m pip install git+https://github.com/liquidctl/liquidctl#egg=liquidctl
```

[git]: https://git-scm.com/
[pip]: https://pip.pypa.io/en/stable/

#### Allowing access to the devices
[Allowing access to the devices]: #allowing-access-to-the-devices

Access permissions are not a concern on platforms like macOS or Windows, where
unprivileged access is already allowed by default.  However, devices are not
generally accessible by unprivileged users on Linux, FreeBSD or DragonFly BSD.

For Linux, we provide a set of udev rules in [`71-liquidctl.rules`] that can be
used to allow unprivileged read and write access to all devices supported by
liquidctl.  These rules are generally already included in downstream Linux
packages of liquidctl.

Alternatively, `sudo`, `doas` and similar mechanisms can be used to invoke
`liquidctl` as the super user, on both Linux and BSDs.

[`71-liquidctl.rules`]: extra/linux/71-liquidctl.rules

#### Additional files
[Additional files]: #additional-files

Other files and tools are included in the source tree, which may be of use in
certain scenarios:

- [liquidctl(8) man page][liquidctl.8];
- [completions for the liquidctl CLI in Bash][liquidctl.bash];
- [host-based automatic fan/pump speed control][yoda];
- [send liquidctl data to HWiNFO][LQiNFO.py];
- [and more...][extra/].

[LQiNFO.py]: extra/windows/LQiNFO.py
[extra/]: extra/
[liquidctl.8]: liquidctl.8
[liquidctl.bash]: extra/completions/liquidctl.bash
[yoda]: extra/yoda

### Working locally
[Working locally]: #working-locally

_Changed in 1.9.0: liquidctl now uses a PEP 517 build system._<br>

When working on the project itself, it is sometimes useful to set up a local
development environment, making it possible to directly run the CLI and the
test suite, without first building and installing a local package.

For this, start by installing [git] and any system-level dependencies mentioned
in [Manual installation].  Then, clone the repository and change into the
created directory:

```
git clone https://github.com/liquidctl/liquidctl
cd liquidctl
```

Optionally, set up a [virtual environment][Creating a virtual environment].

Finally, if the necessary Python build, test and runtime libraries are not
already installed on the environment (virtual or global), manually install
them:

```
python -m pip install --upgrade pip setuptools setuptools_scm wheel
python -m pip install --upgrade colorlog crcmod==1.7 docopt hidapi pillow pytest pyusb
python -m pip install --upgrade "libusb-package; sys_platform == 'win32' or sys_platform == 'cygwin'"
python -m pip install --upgrade "smbus; sys_platform == 'linux'"
python -m pip install --upgrade "winusbcdc>=1.5; sys_platform == 'win32'"
```

At this point, the environment is set up.  To run the test suite, execute:

```
python -m pytest
```

To run the CLI directly, without building and installing a local package,
execute:

```
python -m liquidctl [arguments]
```

And to install `liquidctl` into the environment:

```
python -m pip install .
```

## Introducing the command-line interface
[The command-line interface]: #introducing-the-command-line-interface

The complete list of commands and options can be found in `liquidctl --help` and in the man page, but the following topics cover the most common operations.

Brackets `[ ]`, parenthesis `( )`, less than/greater than `< >` and ellipsis `...` are used to describe, respectively, optional, required, positional and repeating elements.  Example commands are prefixed with a number sign `#`, which also serves to indicate that on Linux root permissions (or suitable udev rules) may be required.

The `--verbose` option will print some extra information, like automatically made adjustments to user-provided settings.  And if there is a problem, the `--debug` flag will make liquidctl output more information to help identify its cause; be sure to include this when opening a new issue.

_Note: in addition to `--debug`, setting the `PYUSB_DEBUG=debug` and `LIBUSB_DEBUG=4` environment variables can be helpful with problems suspected to relate to PyUSB or LibUSB._

### Listing and selecting devices
[Listing and selecting devices]: #listing-and-selecting-devices

A good place to start is to ask liquidctl to list all recognized devices.

```
$ liquidctl list
Device #0: NZXT Smart Device (V1)
Device #1: NZXT Kraken X (X42, X52, X62 or X72)
```

In case more than one supported device is found, one them can be selected with `--match <substring>`, where `<substring>` matches part of the desired device's description using a case insensitive comparison.

```
$ liquidctl --match kraken list
Result #0: NZXT Kraken X (X42, X52, X62 or X72)
```

More device properties can be show by passing `--verbose` to `liquidctl list`.  Any of those can also be used to select a particular product.

```
$ liquidctl --bus hid --address /dev/hidraw4 list
Result #0: NZXT Smart Device (V1)

$ liquidctl --serial 1234567890 list
Result #0: NZXT Kraken X (X42, X52, X62 or X72)
```

Ambiguities for any given filter can be solved with `--pick <number>`.

### Initializing and interacting with devices
[Initializing and interacting with devices]: #initializing-and-interacting-with-devices

Devices will usually need to be initialized before they can be used, though each device has its own requirements and limitations.  This and other information specific to a particular device will appear on the documentation linked from the [Supported devices] section.

Devices can be initialized individually or all at once.

```
# liquidctl [options] initialize [all]
```

Most devices provide some status information, like fan speeds and liquid temperatures.  This can be queried for all devices or using the filtering methods mentioned before.

```
# liquidctl [options] status
```

Fan and pump speeds can be set to fixed values or, if the device supports them, custom profiles.  The specific documentation for each device will list the available modes, as well as which sensor is used for custom profiles.  In general, liquid coolers only support custom profiles that are based on the internal liquid temperature probe.

```
# liquidctl [options] set <channel> speed (<temperature> <percentage>) ...
# liquidctl [options] set <channel> speed <percentage>
```

Lighting is controlled in a similar fashion.  The specific documentation for each device will list the available channels, modes and additional options.

```
# liquidctl [options] set <channel> color <mode> [<color>] ...
```

### Supported color specification formats
[Supported color specification formats]: #supported-color-specification-formats

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
[Using liquidctl in other programs and scripts]: #using-liquidctl-in-other-programs-and-scripts

The liquidctl driver APIs can be used to build Python programs that monitor or
control the devices, and offer features beyond the ones provided by the CLI.

The APIs are documented, and this documentation can be accessed through
`pydoc`, or directly read from the source files.

```python
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
[Automation and running at boot]: #automation-and-running-at-boot

In most cases you will want to automatically apply your settings when the system boots.  Generally a simple script or a basic service is enough, and some specifics about this are given in the following sections.

For even more flexibility, you can also write a Python program that calls the driver APIs directly.

### Set up Linux using systemd
[Set up Linux using systemd]: #set-up-linux-using-systemd

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
[Set up Windows using Task Scheduler]: #set-up-windows-using-task-scheduler

The configuration of devices can be automated by writing a batch file and setting up a new task for (every) login using Windows Task Scheduler.  The batch file can be really simple and only needs to contain the invocations of liquidctl that would otherwise be done manually.

```batchfile
liquidctl initialize all
liquidctl --match kraken set pump speed 90
liquidctl --match kraken set fan speed  20 30  30 50  34 80  40 90  50 100
liquidctl --match "smart device" set sync speed 55
liquidctl --match kraken set sync color fading 350017 ff2608
```

Make sure that liquidctl is available in the context where the batch file will run: in short, `liquidctl --version` should work within a _normal_ Command Prompt window.

You may need to install Python with the option to set the PATH variable enabled, or manually add the necessary folders to the PATH.

A slightly more complex example can be seen in [issue #14](https://github.com/liquidctl/liquidctl/issues/14#issuecomment-456519098) ("Can I autostart liquidctl on Windows?"), that uses the LEDs to convey progress or eventual errors.  Chris' guide on [Replacing NZXT’s CAM software on Windows for Kraken](https://codecalamity.com/replacing-nzxts-cam-software-on-windows-for-kraken/) is also a good read.

As an alternative to using Task Scheduler, the batch file can simply be placed in the startup folder; you can run `shell:startup` to [find out where that is](https://support.microsoft.com/en-us/help/4026268/windows-10-change-startup-apps).

### Set up macOS using various methods
[Set up macOS using various methods]: #set-up-macos-using-various-methods

You can follow either or both of the guides below to automatically configure your devices during login or after waking from sleep. The guides are hosted on tonymacx86:

- [This guide](https://www.tonymacx86.com/threads/gigabyte-z490-vision-d-thunderbolt-3-i5-10400-amd-rx-580.298642/post-2138475) is for controllers that lose their state during sleep (e.g. Gigabyte RGB Fusion 2.0) and need to be reinitialized after wake-from-sleep. This guide uses _Automator_ to initialize supported devices at login, and _sleepwatcher_ to initialize supported devices after wake-from-sleep.
- [This guide](https://www.tonymacx86.com/threads/asus-z690-proart-creator-wifi-thunderbolt-4-i7-12700k-amd-rx-6800-xt.318311/post-2306524) is for controllers that do not lose their state during sleep (e.g. ASUS Aura LED). This driver uses the _launchctl_ method to initialize supported devices at login.


## Troubleshooting
[Troubleshooting]: #troubleshooting

### Device not listed (Windows)

This is likely caused by having replaced the standard driver of a USB HID.  If the device in question is not marked in [Supported devices] as requiring a special driver, try uninstalling the custom driver.

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
[Additional documentation]: #additional-documentation

Be sure to browse [`docs/`](docs/) for additional documentation, and [`extra/`](extra/) for some example scripts and other possibly useful things.

You are also encouraged to contribute to the documentation and to these examples, including adding new files that cover your specific use cases or solutions.


## License
[License]: #license

Copyright 2018–2023 Jonas Malaco, Marshall Asch, CaseySJ, Tom Frey, Andrew
Robertson, ParkerMc, Aleksa Savic, Shady Nawara and contributors

Some modules also incorporate or use as reference work by leaty, Ksenija
Stanojevic, Alexander Tong, Jens Neumaier, Kristóf Jakab, Sean Nelson, Chris
Griffith, notaz, realies and Thomas Pircher. This is mentioned in the module
docstring, along with appropriate additional copyright notices.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but without any
warranty; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.


## Related projects
[Related projects]: #related-projects

### [liquidctl/liquidtux](https://github.com/liquidctl/liquidtux)

Sibling project of Linux kernel _hwmon_ drivers for devices supported by
liquidctl.

### [coolercontrol/coolercontrol](https://gitlab.com/coolercontrol/coolercontrol)

Graphical interface to monitor and control cooling devices supported by
liquidctl.

### [CalcProgrammer1/OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB)

Graphical interface to control many different types of RGB devices.
