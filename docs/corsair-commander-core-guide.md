# Corsair Commander Core
_Driver API and source code available in [`liquidctl.driver.commander_core`](../liquidctl/driver/commander_core.py)._

Currently, functionality implemented is listed here. More is planned to be added.

## Initializing the device

The device should be initialized every time it is powered on.

```
# liquidctl initialize
Corsair Commander Core (experimental)
├── Firmware version            2.6.201  
├── AIO LED count                    29  
├── RGB port 1 LED count              8  
├── RGB port 2 LED count              8  
├── RGB port 3 LED count            N/A  
├── RGB port 4 LED count            N/A  
├── RGB port 5 LED count            N/A  
├── RGB port 6 LED count            N/A  
├── AIO port connected              Yes  
├── Fan port 1 connected            Yes  
├── Fan port 2 connected            Yes  
├── Fan port 3 connected             No  
├── Fan port 4 connected             No  
├── Fan port 5 connected             No  
├── Fan port 6 connected             No  
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

## Programming the pump and fan speeds

_New in 1.9.0._  

Currently, the pump and each fan can be set to a fixed duty cycle. 

```
# liquidctl set fan1 speed 70
                ^^^^       ^^
               channel    duty
```

Valid channel values are `pump`, `fanN`, where 1 <= N <= 6 is the fan number, and
`fans`, to simultaneously configure all fans.

In iCUE the pump can be set to different modes that correspond to a fixed percent that can be used in liquidctl.
Quiet is 75%, Balanced is 85% and Extreme is 100%. 

Note: The pump and some fans have a limit to how slow they can go and will not stop when set to zero.
This is a hardware limitation that cannot be changed.
