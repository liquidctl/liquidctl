# ASUS Ryuo I Liquid Coolers
_Driver API and source code available in [`liquidctl.driver.asus_ryuo`](../liquidctl/driver/asus_ryuo.py)._

_New in git._<br>

## Initialization

Initialization is not required. It outputs the firmware version:

```
# liquidctl initialize
ASUS ROG Ryuo I 240
└── Firmware version    AURO0-S452-0205
```

## Monitoring

This driver does **not** report status information (e.g. temperature, fan RPM, or duty cycle).

```
# liquidctl status
ASUS ROG Ryuo I 240
└── No status available
```

## Speed control

### Setting fixed fan speed

Use channel `fans` or `fan` to set the speed of all fans connected to the cooler:

```
# liquidctl set fans speed 60
```

Only a single fan channel is available. Speeds are set as a fixed percentage (duty cycle) from 0–100%.

## Limitations

- No telemetry (fan speed, liquid temperature, etc.) is currently available.
- Only fixed fan speed control is supported.
- The cooler’s screen is not supported.

