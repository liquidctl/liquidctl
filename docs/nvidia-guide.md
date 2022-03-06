# NVIDIA graphics cards
_Driver API and source code available in [`liquidctl.driver.nvidia`](../liquidctl/driver/nvidia.py)._

Support for these cards in only available on Linux.  Other requirements must
also be met:

- `i2c-dev` kernel module has been loaded
- r/w permissions to card-specific `/dev/i2c-*` devices
- specific unsafe features have been opted in

Jump to the appropriate section for a supported card:

* _Series 10/Pascal:_
    - [ASUS Strix GTX 1050 OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1050 Ti OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1060 6GB][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1060 OC 6GB][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1070 OC][asus-gtx-rtx]
    - [ASUS Strix GTX 1070 Ti Advanced][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1070 Ti][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1070][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1080 Advanced][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1080 OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1080 Ti OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1080 Ti][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1080][asus-gtx-rtx] _(experimental)_
    - [EVGA GTX 1070 FTW DT Gaming][evga-gp104] _(experimental)_
    - [EVGA GTX 1070 FTW Hybrid][evga-gp104] _(experimental)_
    - [EVGA GTX 1070 FTW][evga-gp104] _(experimental)_
    - [EVGA GTX 1070 Ti FTW2][evga-gp104] _(experimental)_
    - [EVGA GTX 1080 FTW][evga-gp104]
* _Series 16/Turing:_
    - [ASUS Strix GTX 1650 Super OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1660 Super OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix GTX 1660 Ti OC][asus-gtx-rtx] _(experimental)_
* _Series 20/Turing:_
    - [ASUS Strix RTX 2060 Evo OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2060 Evo][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2060 OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2060 Super Advanced][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2060 Super Evo Advanced][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2060 Super OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2060 Super][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2070 Advanced][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2070 OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2070 Super Advanced][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2070 Super OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2070][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2080 OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2080 Super Advanced][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2080 Super OC][asus-gtx-rtx] _(experimental)_
    - [ASUS Strix RTX 2080 Ti OC][asus-gtx-rtx]
    - [ASUS Strix RTX 2080 Ti][asus-gtx-rtx] _(experimental)_
* _Series 30/Ampere:_
    - [ASUS TUF RTX 3060 Ti OC][asus-gtx-rtx] _(experimental)_
* _[Inherent unsafeness of I²C]_


## EVGA GTX 1070, 1070 Ti and 1080
[evga-gp104]: #evga-gtx-1070-1070-ti-and-1080

Only RGB lighting supported.

Unsafe features:

- `smbus`: see [Inherent unsafeness of I²C]
- `experimental_evga_gpu`: enable new/experimental devices

### Initialization

Not required for this device.

### Retrieving the current RGB lighting mode and color

In verbose mode `status` reports the current RGB lighting settings.

```
# liquidctl status --verbose --unsafe=smbus
EVGA GTX 1080 FTW
├── Mode      Fixed  
└── Color    2aff00  
```

### Controlling the LED

This GPU only has one led that can be set.  The table bellow summarizes the
available channels, modes and their associated number of required colors.

| Channel    | Mode        | Colors |
| ---------- | ----------- | -----: |
| `led`      | `off`       |      0 |
| `led`      | `fixed`     |      1 |
| `led`      | `breathing` |      1 |
| `led`      | `rainbow`   |      0 |

```
# liquidctl set led color off --unsafe=smbus
# liquidctl set led color rainbow --unsafe=smbus
# liquidctl set led color fixed ff8000 --unsafe=smbus
# liquidctl set led color breathing "hsv(90,85,70)" --unsafe=smbus
                ^^^       ^^^^^^^^^  ^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^
              channel        mode        color     unsafe features
```

The LED color can be specified using any of the
[supported formats](../README.md#supported-color-specification-formats).

The settings configured on the device are normally volatile, and are cleared
whenever the graphics card is powered down (OS and UEFI power saving settings
can affect when this happens).

It is possible to store them in non-volatile controller memory by
passing `--non-volatile`.  But as this memory has some unknown yet
limited maximum number of write cycles, volatile settings are
preferable, if the use case allows for them.

```
# liquidctl set led color fixed 00ff00 --non-volatile --unsafe=smbus
```

## ASUS Strix GTX and RTX
[asus-gtx-rtx]: #asus-strix-gtx-and-rtx

Only RGB lighting supported.

Unsafe features:

- `smbus`: see [Inherent unsafeness of I²C]
- `experimental_asus_gpu`: enable new/experimental devices

### Initialization

Not required for this device.

### Retrieving the current color mode and LED color

In verbose mode `status` reports the current RGB lighting settings.

```
# liquidctl status --verbose --unsafe=smbus
ASUS Strix RTX 2080 Ti OC
├── Mode      Fixed  
└── Color    ff0000  
```

### Controlling the LED

This GPU only has one led that can be set.  The table bellow summarizes the
available channels, modes, and their associated maximum number of colors for
each device family.

| Channel    | Mode          | Colors |
| ---------- | ------------- | -----: |
| `led`      | `off`         |      0 |
| `led`      | `fixed`       |      1 |
| `led`      | `flash`       |      1 |
| `led`      | `breathing`   |      1 |
| `led`      | `rainbow`     |      0 |

```
# liquidctl set led color off --unsafe=smbus
# liquidctl set led color rainbow --unsafe=smbus
# liquidctl set led color fixed ff8000 --unsafe=smbus
# liquidctl set led color flash ff8000 --unsafe=smbus
# liquidctl set led color breathing "hsv(90,85,70)" --unsafe=smbus
                ^^^       ^^^^^^^^^  ^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^
              channel        mode        color     unsafe features
```

The LED color can be specified using any of the
[supported formats](../README.md#supported-color-specification-formats).

The settings configured on the device are normally volatile, and are cleared
whenever the graphics card is powered down (OS and UEFI power saving settings
can affect when this happens).

It is possible to store them in non-volatile controller memory by passing
`--non-volatile`.  But as this memory has some unknown yet limited maximum
number of write cycles, volatile settings are preferable, if the use case
allows for them.

```
# liquidctl set led color fixed 00ff00 --non-volatile --unsafe=smbus
```

Note: The `off` mode is simply an alias for `fixed 000000`.


## Inherent unsafeness of I2C
[Inherent unsafeness of I²C]: #inherent-unsafeness-of-i2c

Reading and writing to I²C buses is inherently more risky than dealing with,
for example, USB devices.  On typical desktop and workstation systems many
important chips are connected to these buses, and they may not tolerate writes
or reads they do not expect.

It is necessary to rely on certain devices being know to use a specific
address, or being documented/specified to do so; but there is always some risk
that another, unexpected, device is using that same address.

On top of this, accessing I²C buses concurrently, from multiple threads or
processes, may also result in undesirable or unpredictable behavior.

Unsurprisingly, users or programs dealing with I²C devices have occasionally
crashed systems and even bricked boards or peripherals.  In some cases this is
reversible, but not always.

For all of these reasons liquidctl requires users to *opt into* accessing I²C
and SMBus devices, both of which can be done by enabling the `smbus` unsafe
feature.  Other unsafe features may also be required for the use of specific
devices, based on other *know* risks specific to a particular device.

Note that a feature not being labeled unsafe, or a device not requiring the use
of additional unsafe features, does in no way assure that it is safe.  This is
especially true when dealing with I²C/SMBus devices.

Finally, liquidctl may list some I²C/SMBus devices even if `smbus` has not been
enabled, but only if it is able to discover them without communicating with the
bus or the devices.
