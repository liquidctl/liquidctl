# DDR4 DIMMs
_Driver API and source code available in [`liquidctl.driver.ddr4`](../liquidctl/driver/ddr4.py)._

Support for these DIMMs in only available on Linux.  Other requirements must
also be met:

- optional Python dependency `smbus` is available
- `i2c-dev` kernel module has been loaded
- r/w permissions to the host SMBus `/dev/i2c-*` device
- specific unsafe features have been opted in
- the host SMBus is supported: currently only i801 (Intel mainstream & HEDT)

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

---

Jump to a specific DIMM model:

- [Generic support for standard SPD EEPROM with temperature sensor][ddr4_temperature]
- [Corsair Vengeance RGB][vengeance_rgb]


## Generic support for standard SPD EEPROM with temperature sensor
[ddr4_temperature]: #generic-support-for-standard-spd-eeprom-with-temperature-sensor

Experimental.

Unsafe features:

- `smbus`: see [Inherent unsafeness of I²C/SMBus]
- `ddr4_temperature`: access standard temperature sensor address

### Initialization

Not required for this device.

### Retrieving the DIMM's temperature

```
# liquidctl status --unsafe=smbus,ddr4_temperature
DDR4 DIMM2 (experimental)
└── Temperature    30.5  °C
```


## Corsair Vengeance RGB
[vengeance_rgb]: #corsair-vengeance-rgb

Experimental. Only temperature monitoring supported.

Unsafe features:

- `smbus`: see [Inherent unsafeness of I²C/SMBus]
- `vengeance_rgb`: access non-advertised temperature sensor address

### Initialization

Not required for this device.

### Retrieving the DIMM's temperature

```
# liquidctl status --verbose --unsafe=smbus,vengeance_rgb
Corsair Vengeance RGB DIMM2 (experimental)
└── Temperature    30.5  °C
```

### Controlling the LED

Not implemented yet.
