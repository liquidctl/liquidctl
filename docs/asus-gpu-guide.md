# ASUS Strix RTX 2080 Ti OC GPU driver
_Driver API and source code available in [`liquidctl.driver.asus_rog`](../liquidctl/driver/asus_rog.py)._

## Initializing the device and setting the pump mode

The device does not need to be initialized before use.

## Retrieving the current color mode and LED color


Currently there is no way to get the current fan speed of the GPU.
The status command get get the current mode and RGB value

_Note: the verbose flag is needed to get the color information_

```
# liquidctl status -v --unsafe=smbus,rog_turing

ASUS Strix RTX 2080 Ti OC (experimental)
├── Mode       Fixed
└── Color    ff0000
```

## Programming the fan speeds

This is currently not supported by the driver.

## Controlling the LEDs

This GPU only has one led that can be set.


The table bellow summarizes the available channels, modes, and their associated
maximum number of colors for each device family.

| Channel  | Mode        | colors  |
| -------- | ----------- | ------- |
| led      | off         | 0       |
| led      | fixed       | 1       |
| led      | flash       | 1       |
| led      | breathing   | 1       |
| led      | rainbow     | 0       |

The `off` mode is simply an alias for `fixed 000000`.

```
# liquidctl set led color off
# liquidctl set led color fixed ff8000
# liquidctl set led color fixed "hsv(90,85,70)"
# liquidctl set led color fixed <1  color>
                ^^^       ^^^^^   ^^^
              channel      mode   color
```

Each color can be specified using any of the [supported formats](../README.md#supported-color-specification-formats).


Note: control of device is experimental and requires the
`--unsafe=smbus,rog_turing` flags to be supplied on the command line for all commands.
