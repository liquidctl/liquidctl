# Gigabyte RGB Fusion 2.0 lighting controllers
_Driver API and source code available in [`liquidctl.driver.rgb_fusion2`](../liquidctl/driver/rgb_fusion2.py)._

## RGB Fusion 2.0

RGB Fusion 2.0 is a lighting system that supports 12 V non-addressable RGB and
5 V addressable ARGB lighting accessories, along side RGB/ARGB memory modules
and other elements on the motherboard itself.  It is built into motherboards
that contain the RGB Fusion 2.0 logo, typically from Gigabyte.

These motherboards use one of many possible ITE Tech controller chips, which
are connected to the host via SMBus or USB, depending on the motherboard/chip
model; liquidctl supports a few of the USB controllers.

## Initialization

The controlers mus be initialized after the system boots or resumes from a suspend state.

```
# liquidctl initialize
Gigabyte RGB Fusion 2.0 5702 Controller (experimental)
├── Hardware name       IT5702-GIGABYTE V1.0.10.0
├── Firmware version                     1.0.10.0
└── LED channnels                               7
```

## Lighting

The controllers support six color modes: `off`, `fixed`, `pulse`, `flash`,
`double-flash` and `color-cycle`.

As much as we would prefer to use descriptive channel names, currently it is
not practical to do so, since the correspondence between the hardware channels
and the corresponding features on the motherboard is not stable.  Hence,
lighting channels are given generic names: `led1`, `led2`, etc.

At this time, eight lighting channels are defined; a `sync` channel is also
provided, which applies the specified setting to all lighting channels.

```
# liquidctl set sync color off
# liquidctl set led1 color fixed 350017
# liquidctl set led2 color pulse ff2608
# liquidctl set led3 color flash 350017
# liquidctl set led4 color double-flash 350017
# liquidctl set led5 color color-cycle --speed slower
```

For color modes `pulse`, `flash`, `double-flash` and `color-cycle`, the speed
of color change is governed by the optional `--speed` parameter, one of six
possible values: `slowest`, `slower`, `normal` (the default), `faster`,
`fastest` or `ludicrous`.

The more elaborate color/animation schemes supported by the motherboard on the
addressable headers are not currently supported.

## Correspondence between lighting channels and physical locations

Each user may need to create a table that associates generic channel names to
specific areas or headers on their motherboard. For example, a map for the
Gigabyte Z490 Vision D might look like this:

- led1: this is the LED next to the IO panel;
- led2: this is one of two 12V RGB headers;
- led3: this is the LED on the PCH chip ("Designare" on Vision D);
- led4: this is an array of LEDs behind the PCI slots on *back side* of
  motherboard;
- led5: this is second 12V RGB header;
- led6: this is one of two 5V addressable RGB headers;
- led7: this is second 5V addressable RGB header;
- led8: not in use.

## More on resuming from sleep states

On wake-from-sleep, the ITE controller will be reset and all color modes will
revert to fixed blue.

On macOS, the "sleepwatcher" utility can be installed via Homebrew along with a
script to be run on wake that will issue the necessary liquidctl commands to
restore desired lighting effects.

Alternatively or on other operating systems the methods used to [automate the
configration at boot time] can usually be adapted to also handle resuming from
sleep states.

[automate the configuration at boot time]: ../README.md#automation-and-running-at-boot
