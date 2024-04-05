# Aquacomputer Farbwerk 360 RGB controller
_Driver API and source code available in [`liquidctl.driver.aquacomputer`](../liquidctl/driver/aquacomputer.py)._

_New in 1.11.0._<br>

## Initialization

Initialization is _currently_ not required, but is recommended. It outputs the firmware version:

```
# liquidctl initialize
Aquacomputer Farbwerk 360
├── Firmware version           1022
└── Serial number       16827-56978
```

The controller automatically sends a status HID report every second as soon as it's connected.

## Monitoring

The Farbwerk 360 exposes four physical and sixteen virtual temperature sensors.

```
# liquidctl status
Aquacomputer Farbwerk 360
├── Sensor 1          24.1  °C
├── Sensor 2          25.7  °C
├── Sensor 3          25.2  °C
├── Sensor 4          25.6  °C
└── Soft. Sensor 1    52.0  °C
```

_Changed in 1.12.0: read virtual temperature sensors as well._<br>

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
