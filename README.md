# liquidctl – liquid cooler control

An open-source and cross-platform command-line tool to control third generation Kraken X liquid coolers from NZXT and, in the future, more devices.

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

# liquidctl --help
```

<!-- stop here for PyPI -->

For more information, check the following sections:

1. [Getting liquidctl](#getting-liquidctl)
2. [Controlling a NZXT Kraken X](#nzxt-kraken-x-3rd-generation)
3. [Other devices](#other-devices)
4. [License](#license)
5. [Related projects](#related-projects)


## Getting liquidctl

The latest version can be installed from PyPI.

```
# pip install liquidctl
```

Pip can also install the latest HEAD directly from GtiHub.

```
# pip install git+https://github.com/jonasmalacofilho/liquidctl
```

If you plan on contributing to the project, clone the repository manually and install liquidctl in editable mode.

```
$ git clone https://github.com/jonasmalacofilho/liquidctl
$ cd liquidctl
# pip install --editable .
```

Of course, a virtual environment can be used instead of having the package installed globally.

### Additional dependency on Windows: a backend for PyUSB

On Windows a suitable backend for PyUSB will need to be installed, such as libusb.  In the case of libusb, version 1.0.21 is recommended over later ones, as those generate some errors during device release.

In the case of libusb 1.0.21, a very simple way of installing it is to download the appropriate package from [libusb/releases](https://github.com/libusb/libusb/releases) and extract the `.dll` and `.lib` files that match you runtime (e.g. MS64) to your python installation directory (e.g. `%homepath%\Anaconda3\`).


## NZXT Kraken X, 3rd generation
_X42, X52, X62 and X72_
<!-- move to /doc once there are more devices -->

This generation of Kraken X coolers are made by Asetek and house 5th generation pumps, with secondary PCBs designed by NZXT.  They incorporate customizable fan and pump speed control with PWM, a liquid temperature probe at the block and addressable RGB lighting.

### Setting fan and pump speeds

Fan and pump speeds can be set either to fixed PWM duty values or as profiles dependent on liquid temperature.

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

Fan and pump speeds will always be set to 100% for liquid temperatures of 60°C and above.

**Always check that the settings are appropriate for the use case, and that they correctly apply and persist.**

### Configuring the lighting

For lighting, the user can control a total of nine LEDs: one behind the NZXT logo and eight forming the ring that surrounds it.  These are separated into two channels, independently accessed through `logo` and `ring`, or syncronized with `sync`.

```
# liquidctl set sync color fixed af5a2f
# liquidctl set ring color fading 350017 ff2608
# liquidctl set logo color pulse ffffff
# liquidctl set ring color backwards-marquee-5 2f6017 --speed slower
```

Colors are set in hexadecimal RGB, and each animation mode supports different number of colors.  The animation speed can be customized with the `--speed <value>`, and five relative values are accepted by the device: `slowest`, `slower`, `normal`, `faster` and `fastest`.

| Channel | Color mode | Minimum colors | Maximum colors | Notes |
| --- | --- | --- | --- | --- |
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

One of this project's goals is to support multiple devices with the same tool and interface.

The following additional drivers are already planned:

 - EVGA CLC: need a device or someone to collaborate with [**[help!]**][newissue]
 - NZXT Kraken M22: LEDs likely similar to 3rd gen. Kraken X, but need someone to test it [**[help!]**][newissue]
 - NZXT Smart Device from H700i and other i version cases: have it, enqueued

If you would like to see liquidctl handle another device, please [open an issue][newissue].


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

While liquidctl handles each setting separately, for easy configuration of individual aspects of the coolers, krakenx allows a device to be completly configured in a single command.

Feature wise, liquidctl currently extends krakenx with the support for pump and fan speed profiles, and fixes two open issues that seem to manifest with recent firmware versions.  It also further extends the list of supported RGB animations.

A special thank you to all krakenx contributors.  This project was based on it.

### [brkalmar/leviathan](https://github.com/brkalmar/leviathan)

Linux kernel-space driver for 2nd and 3rd generation NZXT Kraken X coolers.

### [audiohacked/OpenCorsairLink](https://github.com/audiohacked/OpenCorsairLink)

Control interface for Corsair all-in-one liquid coolers with USB, and other devices.


<!-- helper links -->
[newissue]: https://github.com/jonasmalacofilho/liquidctl/issues/new
