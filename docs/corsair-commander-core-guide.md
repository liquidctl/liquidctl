# Corsair Commander Core
_Driver API and source code available in [`liquidctl.driver.commander_core`](../liquidctl/driver/commander_core.py)._

Currently, functionality implemented is listed here. More is planned to be added.

## Initializing the device

The device should be initialized every time it is powered on.

```
# liquidctl initialize
Corsair Commander Core (experimental)
├── Firmware version            1.6.135  
├── AIO LED count                    29  
├── RGB port 1 LED count              8  
├── RGB port 2 LED count              8  
├── RGB port 3 LED count            N/A  
├── RGB port 4 LED count            N/A  
├── RGB port 5 LED count            N/A  
├── RGB port 6 LED count            N/A  
├── Water temperature sensor        Yes  
└── Temperature sensor 1             No   
```

## Retrieving the pump speed, fan speeds, and temperatures

The Commander Core currently can retrieve the pump speed, fan speeds, temperature of the water, and
the temperature measured by the probe.

```
# liquidctl status
Corsair Commander Core (experimental)
├── Pump speed           2356  rpm
├── Fan speed 1           810  rpm
├── Fan speed 2           791  rpm
├── Fan speed 3             0  rpm
├── Fan speed 4             0  rpm
├── Fan speed 5             0  rpm
├── Fan speed 6             0  rpm
└── Water temperature    35.8  °C
```
