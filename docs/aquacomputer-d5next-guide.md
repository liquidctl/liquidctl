# Aquacomputer D5 Next watercooling pump
_Driver API and source code available in [`liquidctl.driver.aquacomputer`](../liquidctl/driver/aquacomputer.py)._

_New in 1.11.0._  

## Initialization

Initialization is _currently_ not required, but is recommended. It outputs the firmware version:

```
# liquidctl initialize
Aquacomputer D5 Next
├── Firmware version           1023
└── Serial number       03500-24905
```

The pump automatically sends a status HID report every second as soon as it's connected.

## Monitoring

The D5 Next exposes sensor values such as liquid temperature and two groups of fan sensors, for the pump and the optionally connected fan. These groups provide RPM speed, voltage, current and power readings. The pump additionally exposes +5V and +12V voltage rail readings:

```
# liquidctl status
Aquacomputer D5 Next
├── Liquid temperature     26.9  °C
├── Pump speed             1968  rpm
├── Pump power             2.56  W
├── Pump voltage          12.04  V
├── Pump current           0.21  A
├── Fan speed               373  rpm
├── Fan power              0.38  W
├── Fan voltage           12.06  V
├── Fan current            0.03  A
├── +5V voltage            5.01  V
└── +12V voltage          12.06  V
```

## Programming the fan speeds

Currently, the pump and optionally connected fan can be set to a fixed duty cycle, ranging from 0-100%.

```
liquidctl set pump speed 56
              ^^^^       ^^
             channel    duty
```

Valid channel values on the D5 Next are `pump` and `fan`. 

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
