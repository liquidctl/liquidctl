# ASUS Ryuo I Liquid Coolers
_Driver API and source code available in [`liquidctl.driver.asus_ryuo`](../liquidctl/driver/asus_ryuo.py)._

_New in git._<br>

## Initialization

Initialization is not required. It outputs the firmware version:

```
# liquidctl initialize
ASUS Ryuo I 240
└── Firmware version    AURO0-S452-0205
```

## Monitoring

This driver does **not** report status information (e.g. temperature, fan RPM, or duty cycle).

```
# liquidctl status
ASUS Ryuo I 240
└── No status available
```

## Speed control

### Setting fixed fan speed

Use channel `fans` or `fan` to set the speed of all fans connected to the cooler:

```
# liquidctl set fans speed 60
```

Only a single fan channel is available. Speeds are set as a fixed percentage (duty cycle) from 0–100%.

### Duty to speed relation

The resulting speeds do not scale linearly to the set duty values.  
For example duty values below 20% result in no changes in pump speed.

Fan duty values approximately map to the following speeds (± 10%):

| Duty (%) | Fan speed (rpm) |
|:---:|:---:|
| 0 | 810 |
| 10 | 810 |
| 20 | 810 |
| 30 | 1110 |
| 40 | 1380 |
| 50 | 1590 |
| 60 | 1830 |
| 70 | 2070 |
| 80 | 2250 |
| 90 | 2430 |
| 100 | 2580 |


## Limitations

- No telemetry (fan speed, liquid temperature, etc.) is currently available.
- Only fixed fan speed control is supported.
- The cooler’s screen is not supported.

