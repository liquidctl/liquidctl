# Aquacomputer Farbwerk RGB controller
_Driver API and source code available in [`liquidctl.driver.aquacomputer`](../liquidctl/driver/aquacomputer.py)._

_New in 1.13.1._<br>

## Initialization

Initialization is _currently_ not required, but is recommended. It outputs the firmware version:

```
# liquidctl initialize
Aquacomputer Farbwerk
├── Firmware version           1022
└── Serial number       16827-56978
```

The controller automatically sends a status HID report every second as soon as it's connected.

## Monitoring

The Farbwerk 360 exposes four physical temperature sensors.

```
# liquidctl status
Aquacomputer Farbwerk 
├── Sensor 1          24.1  °C
├── Sensor 2          25.7  °C
├── Sensor 3          25.2  °C
├── Sensor 4          25.6  °C
```

