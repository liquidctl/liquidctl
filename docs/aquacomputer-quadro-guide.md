# Aquacomputer Quadro fan controller
_Driver API and source code available in [`liquidctl.driver.aquacomputer`](../liquidctl/driver/aquacomputer.py)._

_New in 1.11.0._<br>

## Initialization

Initialization is _currently_ not required, but is recommended. It outputs the firmware version:

```
# liquidctl initialize
Aquacomputer Quadro (experimental)
├── Firmware version           1032
└── Serial number       23410-65344
```

The Quadro automatically sends a status HID report every second as soon as it's connected.

## Monitoring

The Quadro exposes four temperature sensors (with support for temp offsets) and four groups of fan sensors for
optionally connected fans. These groups provide RPM speed, voltage, current and power readings:

```
# liquidctl status
Aquacomputer Quadro (experimental)
├── Sensor 3            24.5  °C
├── Soft. Sensor 2      41.2  °C
├── Soft. Sensor 3      50.0  °C
├── Soft. Sensor 13     50.0  °C
├── Sensor 1 offset      7.0  °C
├── Sensor 2 offset    -13.0  °C
├── Sensor 3 offset      0.0  °C
├── Sensor 4 offset     12.0  °C
├── Fan 1 speed            0  rpm
├── Fan 1 power         0.00  W
├── Fan 1 voltage      12.06  V
├── Fan 1 current       0.00  A
├── Fan 2 speed            0  rpm
├── Fan 2 power         0.00  W
├── Fan 2 voltage      12.06  V
├── Fan 2 current       0.00  A
├── Fan 3 speed          249  rpm
├── Fan 3 power         0.00  W
├── Fan 3 voltage      12.06  V
├── Fan 3 current       0.00  A
├── Fan 4 speed            0  rpm
├── Fan 4 power         0.00  W
├── Fan 4 voltage      12.06  V
├── Fan 4 current       0.00  A
└── Flow sensor            0  dL/h
```

_Changed in git: read virtual temperature sensors as well._<br>
_Changed in git: read temperature sensor offsets as well._<br>

## Programming the fan speeds

Currently, four optionally connected fans can be set to a fixed duty cycle, ranging from 0-100%.

```
# liquidctl set fan1 speed 56
                ^^^^       ^^
               channel    duty
```

Valid channel values on the Quadro are `fan1` through `fan4`.

## Setting offsets for temperature sensors

Temp sensor offsets can be set to a value from 0 to 15C.

```
# liquidctl set sensor1 tempoffset 7.7
                ^^^^^^^            ^^^
                channel           offset
```

_Changed in git: write temperature sensor offsets._<br>

## Interaction with Linux hwmon drivers
[Linux hwmon]: #interaction-with-linux-hwmon-drivers

Aquacomputer devices are supported by the mainline Linux kernel with its
[`aquacomputer_d5next`] driver, and status data is provided through a standard
hwmon sysfs interface.

Liquidctl automatically detects when a kernel driver is bound to the device
and, whenever possible, uses it instead of directly accessing the device.
Alternatively, direct access to the device can be forced with
`--direct-access`.

[`aquacomputer_d5next`]: https://www.kernel.org/doc/html/latest/hwmon/aquacomputer_d5next.html
