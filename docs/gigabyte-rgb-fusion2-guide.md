# Gigabyte RGB Fusion 2.0 lighting controllers
_Driver API and source code available in [`liquidctl.driver.rgb_fusion2`](../liquidctl/driver/rgb_fusion2.py)._

RGB Fusion 2.0 is a lighting system that supports 12V non-addressable RGB and
5V addressable ARGB lighting accessories, alongside RGB/ARGB memory modules
and other elements on the motherboard itself.  It is built into motherboards
that contain the RGB Fusion 2.0 logo, typically from Gigabyte.

These motherboards use one of many possible ITE Tech controller chips, which
are connected to the host via SMBus or USB, depending on the motherboard/chip
model.

A couple of USB controllers are currently supported:

- ITE 5702: found in Gigabyte Z490 Vision D
- ITE 8297: found in Gigabyte X570 Aorus Elite

## Initialization

RGB Fusion 2.0 controllers must be initialized after the system boots or
resumes from a suspended state.

```
# liquidctl initialize
Gigabyte RGB Fusion 2.0 5702 Controller
├── Hardware name       IT5702-GIGABYTE V1.0.10.0
└── Firmware version                     1.0.10.0
```

## Lighting

The controllers support six color modes: `off`, `fixed`, `pulse`, `flash`,
`double-flash` and `color-cycle`.

As much as we prefer to use descriptive channel names, currently it is not
practical to do so, since the correspondence between the hardware channels and
the corresponding features on the motherboard is not stable.  Hence, lighting
channels are given generic names: `led1`, `led2`, etc.; at this time, eight are
defined.

In addition to these, it is also possible to use the `sync` pseudo-channel to
apply a setting to all lighting channels.

```
# liquidctl set sync color off
# liquidctl set led1 color fixed 350017
# liquidctl set led2 color pulse ff2608
# liquidctl set led3 color flash 350017
# liquidctl set led4 color double-flash 350017
# liquidctl set led5 color color-cycle --speed slower
```

For color modes `pulse`, `flash`, `double-flash` and `color-cycle`, the
animation speed is governed by the optional `--speed` parameter, with one of
six possible values: `slowest`, `slower`, `normal` (the default), `faster`,
`fastest` or `ludicrous`.

The more elaborate color/animation schemes supported by the motherboard on the
addressable headers are not currently supported.

## Correspondence between lighting channels and physical locations

Each user may need to create a table that associates generic channel names to
specific areas or headers on their motherboard. For example, a map for the
Gigabyte Z490 Vision D might look like:

- led1: the LED next to the IO panel;
- led2: one of two 12V RGB headers;
- led3: the LED on the PCH chip ("Designare" on Vision D);
- led4: an array of LEDs behind the PCI slots on *back side* of motherboard;
- led5: second 12V RGB header;
- led6: one of two 5V addressable RGB headers;
- led7: second 5V addressable RGB header;
- led8: not in use.

## More on resuming from sleep states

On wake-from-sleep, the ITE controller will be reset and all color modes will
revert to fixed blue.

To work around this, the methods used to [automate the configuration at boot
time] should be adapted to also handle resuming from sleep states.

On macOS it is also possible to use the _sleepwatcher_ utility, installed via
Homebrew, along with a script to run on wake that issues the necessary
liquidctl commands and restores desired lighting effects.

[automate the configuration at boot time]: ../README.md#automation-and-running-at-boot
