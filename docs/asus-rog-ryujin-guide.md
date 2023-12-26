# ASUS ROG RYUJIN II liquid cooler
_Driver API and source code available in [`liquidctl.driver.asus_rog_ryujin`](../liquidctl/driver/asus_rog_ryujin.py)._


## Initialization

Initialization is not required. It outputs the firmware version:

```
# liquidctl initialize
ASUS ROG RYUJIN II 360
└── Firmware version    AURJ1-S750-0104
```


## Monitoring

The cooler reports the liquid temperature, the speed and the set duty of the pump and embedded micro fan.

```
# liquidctl status
ASUS ROG RYUJIN II 360
├── Liquid temperature          31.4  °C
├── Pump speed                  1200  rpm
├── Pump duty                     30  %
├── Embedded Micro Fan speed    1290  rpm
└── Embedded Micro Fan duty       20  %
```


## Speed control

### Setting fan and embedded pump duty

Pump duty can be set using channel `pump`.

```
# liquidctl set pump speed 90
```

Embedded fan duty can be set using channel `fan` or `fan1`.

```
# liquidctl set fan speed 50
# liquidctl set fan1 speed 50
```

Control of the AIO fan controller is currently not supported.

### Duty to speed relation

The resulting speeds do not scale linearly to the set duty values.  
For example pump duty values below 20%
result in relatively small changes in pump speed.

A mapping of duty values to pump and fan speeds:

| Duty (%) | Pump speed (rpm) | Embedded fan speed (rpm) |
|:---:|:---:|:---:|
| 0 | 840 | 0 |
| 10 | 870 | **390** |
| 20 | 900 | 1200 |
| 30 | 1140 | 1860 |
| 40 | 1470 | 2460 |
| 50 | 1650 | 3000 |
| 60 | 1890 | 3450 |
| 70 | 2130 | 3870 |
| 80 | 2310 | 4230 |
| 90 | 2520 | 4590 |
| 100 | 2800 | 4800 |

Note the minimum speed of the embedded fan is 390 rpm,
meaning the fan may not start spinning at duty values below 10%.

Speeds can deviate +- 10% from the stated values.
