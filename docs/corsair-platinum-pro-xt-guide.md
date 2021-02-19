# Corsair Hydro Platinum and Pro XT all-in-one liquid coolers
_Driver API and source code available in [`liquidctl.driver.hydro_platinum`](../liquidctl/driver/hydro_platinum.py)._

## Initializing the device and setting the pump mode

The device should be initialized every time it is powered on, including when
the system resumes from suspending to memory.

```
# liquidctl initialize
Corsair Hydro H100i Platinum (experimental)
└── Firmware version    1.1.15
```

By default the pump mode will be set to `balanced`, but a different mode can be
specified with `--pump-mode`.  The valid values for this option are `quiet`,
`balanced` and `extreme`.

```
# liquidctl initialize --pump-mode extreme
Corsair Hydro H100i Platinum (experimental)
└── Firmware version    1.1.15
```

Unconfigured fan channels may default to 100% duty, so [reprogramming their
behavior](#programming-the-fan-speeds) is also recommended after running
`initialize` for the first time since the cooler was powered on.  Subsequent
executions of `initialize` should leave the fan speeds unaffected.

## Retrieving the liquid temperature and fan/pump speeds

The cooler reports the liquid temperature and the speeds of all fans and pump.

```
# liquidctl status
Corsair Hydro H100i Platinum (experimental)
├── Liquid temperature    27.0  °C
├── Fan 1 speed           1386  rpm
├── Fan 1 duty              50  %
├── Fan 2 speed           1389  rpm
├── Fan 2 duty              50  %
└── Pump speed            2357  rpm
```

## Programming the fan speeds

Each fan can be set to either a fixed duty cycle, or a profile consisting of up
to seven (temperature, duty) pairs.  Temperatures should be given in Celsius
and duty values in percentage.

Profiles run on the device and are always based on the internal liquid
temperature probe.  The last point should set the fan to 100% duty cycle, or be
omitted; in the latter case the fan will be set to max out at 60°C.

```
# liquidctl set fan1 speed 70
                ^^^^       ^^
               channel    duty

# liquidctl set fan2 speed 20 20 40 70 50 100
                           ^^^^^ ^^^^^ ^^^^^^
                   pairs of temperature (°C) -> duty (%)
```

Valid channel values are `fanN`, where N >= 1 is the fan number, and
`fan`, to simultaneously configure all fans.

As mentioned before, unconfigured fan channels may default to 100% duty.

_Note: pass `--verbose` to see the raw settings being sent to the cooler, after
normalization of the profile and enforcement of the (60°C, 100%) fail-safe._

## Controlling the LEDs

In reality these coolers do not have the concept of different channels or
modes, but liquidctl provides a few for convenience.

The table bellow summarizes the available channels, modes, and their associated
maximum number of colors for each device family.

| Channel  | Mode        | LEDs         | Components   | Platinum | Pro XT | Platinum SE |
| -------- | ----------- | ------------ | ------------ | -------- | ------ | ----------- |
| led      | off         | synchronized | all off      |        0 |      0 |           0 |
| led      | fixed       | synchronized | independent  |        1 |      1 |           1 |
| led      | super-fixed | independent  | independent  |       24 |     16 |          48 |

The `led` channel can be used to address individual LEDs, and supports the
`super-fixed`, `fixed` and `off` modes.

In `super-fixed` mode, each color supplied on the command line is applied to
one individual LED, successively.  LEDs for which no color has been specified
default to off/solid black.  This is closest to how the device works.

In `fixed` mode, all LEDs are set to a single color supplied on the command
line.  The `off` mode is simply an alias for `fixed 000000`.

```
# liquidctl set led color off
# liquidctl set led color fixed ff8000
# liquidctl set led color fixed "hsv(90,85,70)"
# liquidctl set led color super-fixed <up to 24 colors>
                ^^^       ^^^^^^^^^^^ ^
              channel        mode     colors...
```

Each color can be specified using any of the [supported formats](../README.md#supported-color-specification-formats).

Animations are not supported at the hardware level, and require successive
invocations of the commands shown above, or use of the liquidctl APIs.
