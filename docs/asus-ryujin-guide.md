# ASUS Ryujin II liquid coolers
_Driver API and source code available in [`liquidctl.driver.asus_ryujin`](../liquidctl/driver/asus_ryujin.py)._

_New in git._<br>

## Initialization

Initialization is not required. It outputs the firmware version:

```
# liquidctl initialize
ASUS ROG RYUJIN II 360
└── Firmware version    AURJ1-S750-0104
```


## Monitoring

The cooler reports the liquid temperature, the speeds and duties of all fans.

```
# liquidctl status
ASUS ROG RYUJIN II 360
├── Liquid temperature                  26.2  °C
├── Pump duty                             38  %
├── Pump speed                          1410  rpm
├── Embedded Micro Fan duty               40  %
├── Embedded Micro Fan speed            2550  rpm
├── AIO Fan Controller duty               38  %
├── AIO Fan Controller speed - Fan 1     780  rpm
├── AIO Fan Controller speed - Fan 2       0  rpm
├── AIO Fan Controller speed - Fan 3       0  rpm
└── AIO Fan Controller speed - Fan 4     750  rpm
```


## Speed control

### Setting fan and embedded pump duty

Pump duty can be set using channel `pump`.

```
# liquidctl set pump speed 90
```

Use channel `fans` to set all fans at the same time:

```
# liquidctl set fans speed 50
```

Use channel `pump-fan` to set the duty of the embedded fan:

```
# liquidctl set pump-fan speed 50
```

Use channel `external-fans` to set the duty of the fans connected to the AIO fan controller:

```
# liquidctl set external-fans speed 50
```

### Duty to speed relation

The resulting speeds do not scale linearly to the set duty values.  
For example pump duty values below 20% result in relatively small changes in pump speed.

Speeds of the fans connected to the AIO fan controller depend on the fans themselves.

Pump impeller and embedded fan duty values approximately map to the following speeds (± 10%):

| Duty (%) | Pump impeller speed (rpm) | Pump fan speed (rpm) |
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

Note the minimum speed of the embedded pump fan is 390 rpm, meaning the fan may not start spinning at duty values below 10%.



## Screen

The screen of the cooler is not yet supported.
