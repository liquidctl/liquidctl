# NVIDIA graphics cards
_Driver API and source code available in [`liquidctl.driver.nvidia`](../liquidctl/driver/nvidia.py)._

Support for these cards in only available on Linux.

Additional requirements must also be met:

- optional Python dependency `smbus` is available
- `i2c-dev` kernel module has been loaded
- specific unsafe features have been opted in
- r/w permissions to card-specific `/dev/i2c-*` devices

---

Jump to a specific card:

* _Series 10/Pascal:_
    - [EVGA GTX 1080 FTW](#evga-gtx-1080-ftw)
* _Series 20/Turing:_
    - [ASUS Strix RTX 2080 Ti OC](#asus-strix-rtx-2080-ti-oc)


## EVGA GTX 1080 FTW

Experimental.  Only RGB lighting supported.

Unsafe features:

- `smbus`: enable SMBus support; SMBus devices may not tolerate writes or reads
  they do not expect
- `evga_pascal`: enable access to the specific graphics cards

### Initialization

Not required for this device.

### Retrieving the current RGB lighting mode and color

In verbose mode `status` reports the current RGB lighting settings.

```
# liquidctl status --verbose --unsafe=smbus,evga_pascal
EVGA GTX 1080 FTW (experimental)
├── Mode      Fixed  
└── Color    2aff00  
```

### Controlling the LED

This GPU only has one led that can be set.  The table bellow summarizes the
available channels, modes and their associated number of required colors.

| Channel    | Mode        | Required colors |
| ---------- | ----------- | --------------- |
| `led`      | `off`       |               0 |
| `led`      | `fixed`     |               1 |
| `led`      | `breathing` |               1 |
| `led`      | `rainbow`   |               0 |

```
# liquidctl set led color off --unsafe=smbus,evga_pascal
# liquidctl set led color rainbow --unsafe=smbus,evga_pascal
# liquidctl set led color fixed ff8000 --unsafe=smbus,evga_pascal
# liquidctl set led color breathing "hsv(90,85,70)" --unsafe=smbus,evga_pascal
                ^^^       ^^^^^^^^^  ^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^
              channel        mode        color        enable unsafe features
```

The LED color can be specified using any of the
[supported formats](../README.md#supported-color-specification-formats).

The settings configured on the device are normally volatile, and are
cleared whenever the graphics card is powered down.

It is possible to store them in non-volatile controller memory by
passing `--non-volatile`.  But as this memory has some unknown yet
limited maximum number of write cycles, volatile settings are
preferable, if the use case allows for them.

```
# liquidctl set led color fixed 00ff00 --non-volatile --unsafe=smbus,evga_pascal
```


## ASUS Strix RTX 2080 Ti OC

Experimental. Only RGB lighting supported.

Unsafe features:

- `smbus`: enable SMBus support; SMBus devices may not tolerate writes or reads
  they do not expect
- `rog_turing`: enable access to the specific graphics cars

### Initialization

Not required for this device.

### Retrieving the current color mode and LED color

In verbose mode `status` reports the current RGB lighting settings.

```
# liquidctl status -v --unsafe=smbus,rog_turing
ASUS Strix RTX 2080 Ti OC (experimental)
├── Mode      Fixed  
└── Color    ff0000  
```

## Controlling the LED

This GPU only has one led that can be set.  The table bellow summarizes the
available channels, modes, and their associated maximum number of colors for
each device family.

| Channel    | Mode          | colors  |
| ---------- | ------------- | ------- |
| `led`      | `off`         |       0 |
| `led`      | `fixed`       |       1 |
| `led`      | `flash`       |       1 |
| `led`      | `breathing`   |       1 |
| `led`      | `rainbow`     |       0 |

```
# liquidctl set led color off --unsafe=smbus,rog_turing
# liquidctl set led color rainbow --unsafe=smbus,rog_turing
# liquidctl set led color fixed ff8000 --unsafe=smbus,rog_turing
# liquidctl set led color flash ff8000 --unsafe=smbus,rog_turing
# liquidctl set led color breathing "hsv(90,85,70)" --unsafe=smbus,rog_turing
                ^^^       ^^^^^^^^^  ^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^
              channel        mode        color        enable unsafe features
```

The LED color can be specified using any of the
[supported formats](../README.md#supported-color-specification-formats).

The settings configured on the device are normally volatile, and are cleared
whenever the graphics card looses power (ie. unplugged, not power off).

It is possible to store them in non-volatile controller memory by passing
`--non-volatile`.  But as this memory has some unknown yet limited maximum
number of write cycles, volatile settings are preferable, if the use case
allows for them.

```
# liquidctl set led color fixed 00ff00 --non-volatile --unsafe=smbus,rog_turing
```

Note: The `off` mode is simply an alias for `fixed 000000`.
