# Corsair Platinum and PRO XT all-in-one liquid coolers

## Initializing the device and setting the pump mode

The device should be initialized every time it is powered on, including when
the system resumes from suspending to memory.

```
# liquidctl initialize
Corsair H100i Platinum (experimental)
└── Firmware version    1.1.15  
```

By default the pump mode will be set to `balanced`, but a different mode can be
specified with `--pump-mode`.  The valid values for this option are `quiet`,
`balanced` and `extreme`.

```
# liquidctl initialize --pump-mode extreme
Corsair H100i Platinum (experimental)
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
Corsair H100i Platinum (experimental)
├── Liquid temperature    27.0  °C
├── Pump speed            2357  rpm
├── Fan 1 speed           1386  rpm
└── Fan 2 speed           1389  rpm
```

## Programming the fan speeds

Each fan channel can be set to either a fixed duty cycle, or a profile
consisting of up to seven (temperature, duty) pairs.  Temperatures should be
given Celsius and duty values in percentage.

Profiles run on the device are only always based on the internal liquid
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

Coolers with two fans allow each to be controlled individually.  Valid channel
values for these devices are `fanN`, where N >= 1 is the fan number, and `fan`,
to simultaneously configure all fans.

The H150i PRO XT differs from this scheme and only has a single fan _channel._
Thus it is more sensible to use `fan`, even though `fan1` is accepted as well.

As mentioned before, unconfigured fan channels may default to 100% duty.

_Note: pass `--verbose` to see the raw settings being sent to the cooler, after
normalization of the profile and enforcement of the (60°C, 100%) fail-safe._

## Controlling the LEDs

In reality these coolers do not have the concept of different channels or
modes, but liquidctl provides a few for convenience.

The table bellow summarizes the available channels, modes, and their associated
maximum number of colors.

| Channel  | Mode        | LEDs         | Components   | Platinum | PRO XT |
| -------- | ----------- | ------------ | ------------ | -------- | ------ |
| sync/led | off         | all off      | all off      |        0 |      0 |
| sync     | fixed       | synchronized | independent  |        3 |      1 |
| sync     | super-fixed | independent  | synchronized |        8 |      8 |
| led      | super-fixed | independent  | independent  |       24 |      8 |

The `led` channel can be used to address individual LEDs.  The only supported
mode for this channel is `super-fixed`, and each color supplied on the command
line is applied to one individual LED, successively.  This is closest to how
the device works.

The `sync` channel considers that the individual LEDs are associated with
components, and provides two distinct convenience modes: `fixed` allows each
component to be set to a different color, which is applied to all LEDs on that
component; very differently, `super-fixed` allows each individual LED to have a
different color, but all components are made to repeat the same pattern.

Both channels additionally support an `off` mode, which is equivalent to
setting all LEDs to off/solid black.

```
# liquidctl set led color off
# liquidctl set sync color off

# liquidctl set sync color fixed ff8000 00ff80 8000ff
# liquidctl set sync color super-fixed "hsv(0,85,70)" "hsv(45,85,70)" "hsv(90,85,70)" "hsv(135,85,70)" "hsv(180,85,70)" "hsv(225,85,70)" "hsv(270,85,70)" "hsv(315,85,70)"
# liquidctl set led color super-fixed <up to 24 colors>
                ^^^       ^^^^^^^^^^^ ^
              channel        mode     colors...
```

Colors can be specified using any of the [supported
formats](../README.md#supported-color-specification-formats).  LEDs for which
no color has been specified will default to off/solid black.

Animations are not supported at the hardware level, and require successive
invocations of the commands shown above, or use of the liquidctl APIs.
