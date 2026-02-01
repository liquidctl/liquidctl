# ASUS Ryujin III EXTREME liquid cooler
_Driver API and source code available in [`liquidctl.driver.asus_ryujin`](../liquidctl/driver/asus_ryujin.py)._

_New in 1.16.0._<br>
_Changed in git: support added for ASUS Ryujin III EVA EDITION_<br>

## Initialization

Initialization is not required. It outputs the firmware version:

```
# liquidctl initialize
ASUS Ryujin III EXTREME
└── Firmware version    AURJ3-S5F9-0104
```

## Monitoring

The cooler reports the liquid temperature, the speeds and duties of pump and internal fan.

```
# liquidctl status
ASUS Ryujin III EXTREME
├── Liquid temperature    29.9  °C
├── Pump duty               30  %
├── Pump speed            1260  rpm
├── Pump fan duty           30  %
└── Pump fan speed         870  rpm
```

## Speed control

### Setting fan and embedded pump duty

Pump duty can be set using channel `pump`.

```
# liquidctl set pump speed 90
```

Use channel `pump-fan` to set the duty of the embedded fan:

```
# liquidctl set pump-fan speed 50
```

### Duty to speed relation

The resulting speeds do not scale linearly to the set duty values.

Pump impeller and embedded fan duty values approximately map to the following speeds (± 10%):

| Duty (%) | Pump impeller speed (rpm) | Pump fan speed (rpm) |
|:---:|:---:|:---:|
| 0 | 800 | 0 |
| 10 | 840 | 0 |
| 20 | 1260 | 0 |
| 30 | 1710 | **800*** |
| 40 | 2100 | 1620 |
| 50 | 2460 | 2229 |
| 60 | 2460 | 2814 |
| 70 | 2760 | 3471 |
| 80 | 3090 | 4026 |
| 90 | 3360 | 4569 |
| 100 | 3600 | 5100 |

**Note***: the minimum speed of the embedded pump fan is 800 rpm, meaning the fan may not start spinning at duty values below 30%.

## Screen

The screen of the cooler is not yet supported.
