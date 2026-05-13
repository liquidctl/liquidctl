# Corsair Commander DUO
_Driver API available in [`liquidctl.driver.commander_duo`](../liquidctl/driver/commander_duo.py)._

_New in git._<br>

The Corsair Commander DUO is a USB HID fan, temperature, and ARGB controller
with two PWM fan ports, two temperature-probe ports, and two ARGB lighting
ports.

This driver is for the Commander DUO's PWM fan and standard 5 V ARGB ports. It
does not support Corsair iCUE LINK devices or the iCUE LINK ecosystem.

The currently supported functionality is documented below.

Firmware `0.10.112` or later is required.  Earlier firmware versions were
observed to have unreliable fan and ARGB detection and did not reliably apply
software fan control.

## Initializing the device

The device should be initialized every time it is powered on. Initialization
reports firmware version, fan-port connectivity, temperature-probe connectivity,
and detected ARGB LED counts.

```
# liquidctl initialize
Corsair Commander DUO
├── Firmware version                 0.10.112
├── Fan port 1 connected                  Yes
├── Fan port 2 connected                   No
├── Temperature sensor 1 connected        Yes
├── Temperature sensor 2 connected         No
├── ARGB port 1 LED count                  15
└── ARGB port 2 LED count                   0
```

The Commander DUO requires SATA power before it will enumerate on USB.

## Retrieving fan speeds and temperatures

The Commander DUO can report current fan speeds and connected temperature
probes.

```
# liquidctl status - (connected only)
Corsair Commander DUO
├── Fan speed 1     456  rpm
├── Fan speed 2       0  rpm
└── Temperature 1   29.2  °C
```

Disconnected temperature probes are not reported in status output.

## Programming the fan speeds

### Fixed duty cycle

The connected fans can be set to a fixed duty cycle.

```
# liquidctl set fan1 speed 58
                ^^^^       ^^
               channel    duty
```

Valid channel values are `fan1` and `fan2`.

The Commander DUO intentionally remains in software mode after fixed-speed
commands.  Returning it to hardware mode immediately after a write prevents the
new fan speed from taking effect, so this differs from some other Corsair
Commander drivers.

### Speed curve profiles

Speed curve profiles are not currently implemented for the Commander DUO.

## Controlling the LEDs

The Commander DUO has two ARGB lighting channels, specified as `argb1` and
`argb2`.  The aliases `argb`, `led1`, `led2`, `led`, and `sync` are also
accepted for compatibility with other Corsair controller naming conventions.

Currently supported lighting modes are:

| Mode | Num colors |
| ---- | ---------- |
| `off` | 0 |
| `fixed` | 1 |
| `rainbow` | 0, Device Memory only |

For example:

```
# liquidctl set argb1 color fixed ff0000 --maximum-leds 15
# liquidctl set argb1 color off --maximum-leds 15
```

The `--maximum-leds` option can be used to configure the number of LEDs to send
to a channel, especially when automatic detection reports zero LEDs for a
connected ARGB device.

The fixed and off lighting modes use the controller's software color endpoint.
They are volatile: on tested firmware, a one-shot color write can fall back to
the stored Device Memory lighting after a short idle period.  Re-sending the
same fixed color periodically keeps the software color active.

Passing `--non-volatile` writes the fixed, off, or rainbow mode to the Commander
DUO's Device Memory lighting endpoint instead of streaming a software RGB frame:

```
# liquidctl set argb1 color fixed ff0000 --non-volatile
# liquidctl set argb1 color off --non-volatile
# liquidctl set sync color rainbow --non-volatile
```

The Device Memory write is based on iCUE captures for the DUO's static hardware
lighting profile and must be sent while the controller is awake; the driver then
returns the controller to hardware mode so the stored color becomes active.
Hardware mode stores one global lighting profile for the controller; it does not
support independent persistent colors per ARGB port.  The channel argument is
still validated for consistency with normal color commands.  Fixed/off Device
Memory color writes use a static global color, and rainbow writes use the
captured hardware rainbow effect payload.  Per-LED hardware effects, direction,
speed, two-color palettes, and custom Device Memory profile management are not
currently supported by this driver.

Other advanced RGB effects are not currently supported by this driver.
