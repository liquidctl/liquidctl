# Corsair Commander Core
_Driver API and source code available in [`liquidctl.driver.commander_core`](../liquidctl/driver/commander_core.py)._

Currently, functionality implemented is listed here. More is planned to be added.

## Initializing the device

The device should be initialized every time it is powered on.

```
# liquidctl initialize
Corsair Commander Core (experimental)
├── Firmware version                 1.6.135  
├── AIO RGB                               29  LEDs
├── RGB port 1                             8  LEDs
├── RGB port 2                             8  LEDs
├── RGB port 3                  Disconnected  
├── RGB port 4                  Disconnected  
├── RGB port 5                  Disconnected  
├── RGB port 6                  Disconnected  
├── Water Temperature Sensor       Connected  
└── Temperature Sensor 1        Disconnected  
```

## Retrieving the pump speed, fan speeds, and temperatures


The Commander Core currently can retrieve the pump speed, fan speeds, temperature of the water, and
the temperature measured by the probe.

```
# liquidctl status
Corsair Commander Core (experimental)
├── Pump Speed           2342  rpm
├── Fan Speed 1           872  rpm
├── Fan Speed 2           851  rpm
├── Fan Speed 3             0  rpm
├── Fan Speed 4             0  rpm
├── Fan Speed 5             0  rpm
├── Fan Speed 6             0  rpm
└── Water Temperature    36.9  °C
```