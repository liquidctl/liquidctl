# liquidctl – liquid cooler control

*liquidctl* is an open-source and cross-platform command-line tool to configure and query third generation Kraken X liquid coolers from NZXT and, in the future, more devices.

```
# liquidctl list
Device 0, NZXT Kraken X (X42, X52, X62 or X72) at bus:address 2:3

# liquidctl status
NZXT Kraken X (X42, X52, X62 or X72), device 0
Liquid temperature      28.8  °C
Fan speed                849  rpm
Pump speed              2780  rpm
Firmware version       4.0.2

# liquidctl set pump speed 90
# liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
# liquidctl set ring color fading 350017 ff2608
# liquidctl set logo color fixed af5a2f
```

The embedded `--help` lists all available commands and their syntax.

In the case of multiple devices the intended target can be specified with `--device <number>`.

Check the documentation for more details.

<!-- stop here for PyPI -->

1. [Getting liquidctl](#getting-liquidctl)
2. [Controlling a NZXT Kraken X](#nzxt-kraken-x-3rd-generation)
3. [Other devices](#other-devices)
4. [License](#license)
5. [Related projects](#related-projects)


## Getting liquidctl

The easiest way to get liquidctl is to grab a release from PyPI.

```
# pip install liquidctl
```

Pip can also install the latest snapshot directly from GitHub.

```
# pip install git+https://github.com/jonasmalacofilho/liquidctl
```

And if you want to work on the source and contribute to the project, you will find that it is more convenient to clone the repository manually and install liquidctl in editable mode.

```
$ git clone https://github.com/jonasmalacofilho/liquidctl
$ cd liquidctl
# pip install --editable .
```

Of course, a virtual environment can always be used instead of installing the package globally.

### Additional dependency on Windows: a backend for PyUSB

On Windows a suitable backend for PyUSB is necessary, such as *libusb*.  If you already use Python programs that interact with USB devices, you probably already have it.

If you need to install a backend, libusb v1.0.21 is recommended; later versions can crash when trying to release the device.  A simple way of installing it is to download the appropriate package from [libusb/releases](https://github.com/libusb/libusb/releases) and extract the `.dll` and `.lib` files that match you runtime (e.g. MS64) to your python installation directory (e.g. `%homepath%\Anaconda3\`).


## NZXT Kraken X, 3rd generation
<!-- move to /doc once there are more devices -->

The Kraken X42, X52, X62 and X72 compose the third generation of liquid coolers by NZXT.  These devices are manufactured by Asetek and house fifth generation Asetek pumps and PCBs, plus secondary PCBs specially designed by NZXT for enhanced control and lighting.

They incorporate customizable fan and pump speed control with PWM, a liquid temperature probe in the block and addressable RGB lighting.  The coolers are powered directly by the power supply unit.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The cooler also reports fan and pump speed and liquid temperature via USB; pump speed can also be sent to the motherboard (or other device) via the sense pin of a standard fan connector.

### Setting fan and pump speeds

Fan and pump speeds can be set either to fixed PWM duty values or as profiles dependent on the liquid temperature.

Fixed speed values can be set simply by specifying the desired channel (`fan` or `pump`) and PWM duty.

```
# liquidctl set pump speed 90
```

| Channel | Minimum duty | Maximum duty |
| --- | --- | --- |
| fan | 25% | 100% |
| pump | 60% | 100% |

For profiles, any number of temperature–duty pairs can be specified; liquidctl will normalize and optimize the profile before pushing it to the Kraken.  You can use `--verbose` to inspect the final profile.

```
# liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
```

As a safety measure, fan and pump speeds will always be set to 100% for liquid temperatures of 60°C and above.

**Always check that the settings are appropriate for the use case, and that they correctly apply and persist.**

### Configuring the lighting

For lighting, the user can control a total of nine LEDs: one behind the NZXT logo and eight forming the ring that surrounds it.  These are separated into two channels, independently accessed through `logo` and `ring`, or synchronized with `sync`.

```
# liquidctl set sync color fixed af5a2f
# liquidctl set ring color fading 350017 ff2608
# liquidctl set logo color pulse ffffff
# liquidctl set ring color backwards-marquee-5 2f6017 --speed slower
```

Colors are set in hexadecimal RGB, and each animation mode supports different number of colors.  The animation speed can be customized with the `--speed <value>`, and five relative values are accepted by the device: `slowest`, `slower`, `normal`, `faster` and `fastest`.

| Channel | Color mode | Minimum colors | Maximum colors | Notes |
| --- | --- | --- | --- | --- |
| any | `off` | 0 | 0 ||
| any | `fixed` | 1 | 1 ||
| any | `fading` | 2 | 8 ||
| any | `spectrum-wave` | 0 | 0 ||
| any | `backwards-spectrum-wave` | 0 | 0 ||
| any | `breathing` | 1 | 8 ||
| any | `pulse` | 1 | 8 ||
| `ring` | `marquee-<length>` | 1 | 1 | 3	≤ `length` ≤ 6 |
| `ring` | `backwards-marquee-<length>` | 1 | 1 | 3	≤ `length` ≤ 6 |
| `ring` | `covering-marquee` | 2 | 8 ||
| `ring` | `covering-backwards-marquee` | 2 | 8 ||
| `ring` | `alternating` | 2 | 2 ||
| `ring` | `moving-alternating` | 2 | 2 ||
| `ring` | `tai-chi` | 2 | 2 ||
| `ring` | `water-cooler` | 0 | 0 ||
| `ring` | `loading` | 1 | 1 ||
| `ring` | `wings` | 1 | 1 ||
| any | `super` | 9 | 9 | logo + each ring LED |


## Other devices

We would like to continously support more and more devices.  At the moment, some additional drivers are already planned:

 - EVGA CLC 120/240/280: need to borrow a device or get the protocol specs [**[I can help/I know someone]**][newissue]
 - NZXT Kraken M22: probably easy to add, need a beta tester [**[I can help/I know someone]**][newissue]
 - Smart Device from NZXT's H700i/H500i/H400i/H200i cases: soon (tm)

If you would like to see liquidctl handle another device, [open an issue][newissue] and let us know.


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

Linux kernel-space driver for 2nd and 3rd generation NZXT Kraken X coolers.

### [audiohacked/OpenCorsairLink](https://github.com/audiohacked/OpenCorsairLink)

Control interface for Corsair all-in-one liquid coolers with USB, and other devices.


<!-- helper links -->
[newissue]: https://github.com/jonasmalacofilho/liquidctl/issues/new
