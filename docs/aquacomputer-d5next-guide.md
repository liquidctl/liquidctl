# Aquacomputer D5 Next watercooling pump
_Driver API and source code available in [`liquidctl.driver.aquacomputer`](../liquidctl/driver/aquacomputer.py)._

## Initialization

Initialization is _currently_ not required, but is recommended. It outputs the firmware version:

```
Aquacomputer D5 Next
└── Firmware version    1023
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