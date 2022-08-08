# Aquacomputer Farbwerk 360 RGB controller
_Driver API and source code available in [`liquidctl.driver.aquacomputer`](../liquidctl/driver/aquacomputer.py)._

_New in 1.11.0._  

## Initialization

Initialization is _currently_ not required, but is recommended. It outputs the firmware version:

```
Aquacomputer Farbwerk 360
├── Firmware version           1022
└── Serial number       16827-56978
```

The controller automatically sends a status HID report every second as soon as it's connected.

## Monitoring

The Farbwerk 360 exposes four temperature sensors.

```
# liquidctl status
Aquacomputer Farbwerk 360
├── Sensor 1    24.1  °C
├── Sensor 2    25.7  °C
├── Sensor 3    25.2  °C
└── Sensor 4    25.6  °C
```
