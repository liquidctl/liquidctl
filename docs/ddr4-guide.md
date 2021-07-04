# DDR4 DIMMs
_Driver API and source code available in [`liquidctl.driver.ddr4`](../liquidctl/driver/ddr4.py)._

Support for these DIMMs in only available on Linux.  Other requirements must
also be met:

- `i2c-dev` kernel module has been loaded
- r/w permissions to the host SMBus `/dev/i2c-*` device
- specific unsafe features have been opted in
- the host SMBus is supported: currently only i801 (Intel mainstream & HEDT)

Jump to a specific section:

- [DIMMs with a standard temperature sensor][ddr4_temperature]
- [Corsair Vengeance RGB][vengeance_rgb]
- *[Inherent unsafeness of I²C/SMBus]*


## DIMMs with a standard temperature sensor
[ddr4_temperature]: #dimms-with-a-standard-temperature-sensor

Supports modules using TSE2004-compatible SPDD EEPROMs with temperature sensor.

Unsafe features:

- `smbus`: see [Inherent unsafeness of I²C/SMBus]
- `ddr4_temperature`: access standard temperature sensor address

### Initialization

Not required for this device.

### Retrieving the DIMM's temperature

```
# liquidctl status --unsafe=smbus,ddr4_temperature
DDR4 DIMM2
└── Temperature    30.5  °C
```


## Corsair Vengeance RGB
[vengeance_rgb]: #corsair-vengeance-rgb

Unsafe features:

- `smbus`: see [Inherent unsafeness of I²C/SMBus]
- `vengeance_rgb`: access non-advertised temperature sensor and RGB controller
  addresses

### Initialization

Not required for this device.

### Retrieving the DIMM's temperature

```
# liquidctl status --verbose --unsafe=smbus,vengeance_rgb
Corsair Vengeance RGB DIMM2
└── Temperature    30.5  °C
```

### Controlling the LED

Each module features a few *non-addressable* RGB LEDs.  The table bellow
summarizes the available channels, modes and their associated number of
required colors.

| Channel    | Mode        | Colors |
| ---------- | ----------- | -----: |
| `led`      | `off`       |      0 |
| `led`      | `fixed`     |      1 |
| `led`      | `breathing` |    1–7 |
| `led`      | `fading`    |    2–7 |

The LED colors can be specified using any of the
[supported formats](../README.md#supported-color-specification-formats).

The speed of the breathing and fading animations can be adjusted with
`--speed`; the allowed values are `slowest`, `slower`, `normal` (default),
`faster` and `fastest`.

```
# liquidctl set led color breathing ff355e 1ab385 speed=faster --unsafe=smbus,vengeance_rgb
                ^^^       ^^^^^^^^^ ^^^^^^^^^^^^^ ^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
              channel        mode      colors        speed        enable unsafe features

# liquidctl set led color fading "hsv(90,85,70)" "hsv(162,85,70)" --unsafe=smbus,vengeance_rgb
# liquidctl set led color fixed ff355e --unsafe=smbus,vengeance_rgb
# liquidctl set led color off --unsafe=smbus,vengeance_rgb
```


## Inherent unsafeness of I2C and SMBus
[Inherent unsafeness of I²C/SMBus]: #inherent-unsafeness-of-i2c-and-smbus

Reading and writing to System Management (SMBus) and I²C buses is inherently
more risky than dealing with, for example, USB devices.  On typical desktop and
workstation systems many important chips are connected to these buses, and they
may not tolerate writes or reads they do not expect.

While SMBus 2.0 has some limited ability for automatic enumeration of devices
connected to it, unlike simpler I²C buses and SMBus 1.0, this capability is,
effectively, not safely available for us in user space.

It is thus necessary to rely on certain devices being know to use a specific
address, or being documented/specified to do so; but there is always some risk
that another, unexpected, device is using that same address.

The enumeration capability of SMBus 2.0 also brings dynamic address assignment,
so even if a device is know to use a particular address in one machine, that
could be different on other systems.

On top of this, accessing I²C or SMBus buses concurrently, from multiple
threads or processes, may also result in undesirable or unpredictable behavior.

Unsurprisingly, users or programs dealing with I²C/SMBus devices have
occasionally crashed systems and even bricked boards or peripherals.  In some
cases this is reversible, but not always.

For all of these reasons liquidctl requires users to *opt into* accessing
I²C/SMBus devices, which can be done by enabling the `smbus` unsafe feature.
Other unsafe features may also be required for the use of specific devices,
based on other *know* risks specific to a particular device.

Note that a feature not being labeled unsafe, or a device not requiring the use
of additional unsafe features, does in no way assure that it is safe.  This is
especially true when dealing with I²C/SMBus devices.

Finally, liquidctl may list some I²C/SMBus devices even if `smbus` has not been
enabled, but only if it is able to discover them without communicating with the
bus or the devices.

