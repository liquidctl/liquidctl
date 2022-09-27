# Aquacomputer Octo fan controller
_Driver API and source code available in [`liquidctl.driver.aquacomputer`](../liquidctl/driver/aquacomputer.py)._

_New in 1.11.0._  

## Initialization

Initialization is _currently_ not required, but is recommended. It outputs the firmware version:

```
# liquidctl initialize
Aquacomputer Octo
├── Firmware version           1019
└── Serial number       14994-51690
```

The Octo automatically sends a status HID report every second as soon as it's connected.

## Monitoring

The Octo exposes four temperature senso and eight groups of fan sensors for optionally connected fans. These groups provide RPM speed, voltage, current and power readings:

```
# liquidctl status
Aquacomputer Octo
├── Sensor 1          37.0  °C 
├── Fan 1 speed          0  rpm
├── Fan 1 power       0.00  W  
├── Fan 1 voltage    12.09  V  
├── Fan 1 current     0.00  A  
├── Fan 2 speed          0  rpm
├── Fan 2 power       0.00  W
├── Fan 2 voltage     0.00  V
├── Fan 2 current     0.00  A
├── Fan 3 speed          0  rpm
├── Fan 3 power       0.00  W
├── Fan 3 voltage     0.00  V
├── Fan 3 current     0.00  A
├── Fan 4 speed          0  rpm
├── Fan 4 power       0.00  W
├── Fan 4 voltage     0.00  V
├── Fan 4 current     0.00  A
├── Fan 5 speed          0  rpm
├── Fan 5 power       0.00  W
├── Fan 5 voltage     0.00  V
├── Fan 5 current     0.00  A
├── Fan 6 speed          0  rpm
├── Fan 6 power       0.00  W
├── Fan 6 voltage     0.00  V
├── Fan 6 current     0.00  A
├── Fan 7 speed          0  rpm
├── Fan 7 power       0.00  W
├── Fan 7 voltage     0.00  V
├── Fan 7 current     0.00  A
├── Fan 8 speed          0  rpm
├── Fan 8 power       0.02  W
├── Fan 8 voltage    12.09  V
└── Fan 8 current     0.00  A
```

## Programming the fan speeds

Currently, eight optionally connected fans can be set to a fixed duty cycle, ranging from 0-100%.

```
liquidctl set fan1 speed 56
              ^^^^       ^^
             channel    duty
```

Valid channel values on the Octo are `fan1` through `fan8`.

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
