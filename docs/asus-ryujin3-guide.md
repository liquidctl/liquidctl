# ASUS Ryujin III liquid coolers
_Driver API and source code available in [`liquidctl.driver.asus_ryujin`](../liquidctl/driver/asus_ryujin.py)._

_New in 1.16.0._<br>

## Initialization

Initialization is not required. It outputs the firmware version:

```
# liquidctl initialize
ASUS Ryujin III Extreme
└── Firmware version    AURJ3-S5F9-0104
```

## Monitoring

The cooler reports the liquid temperature, the speeds and duties of pump and internal fan.

```
# liquidctl status
ASUS Ryujin III Extreme
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

_New in git._

The Ryujin III has a 320x240 LCD. The screen can be controlled via the `lcd` channel.

### Display a static image

```
# liquidctl set lcd screen static /path/to/image.png
```

Any image format supported by Pillow (PNG, JPEG, BMP, etc.) will be automatically
resized to 320x240 and displayed. Requires `Pillow` (`pip install Pillow`).

### Built-in animation

Switch back to the default ROG animation:

```
# liquidctl set lcd screen liquid
```

### Clock mode

Display a clock synced to the system time:

```
# liquidctl set lcd screen clock 24h
# liquidctl set lcd screen clock 12h
```

### Hardware monitor

Display live sensor readings (liquid temperature, pump RPM, fan RPM):

```
# liquidctl set lcd screen monitor
```

### Turn off the display

```
# liquidctl set lcd screen off
```

### Set brightness

```
# liquidctl set lcd screen brightness 50
```

Values range from 0 (off) to 100 (maximum).

### Set orientation

```
# liquidctl set lcd screen orientation 0
# liquidctl set lcd screen orientation 1
```

Where `0` is horizontal (default) and `1` is vertical (rotated). Values `2` and `3` are 180° and 270°.

### Standby / Wake

Put the display to sleep (for system suspend) or wake it back up:

```
# liquidctl set lcd screen standby
# liquidctl set lcd screen wake
```

The standby command sends `EC 5C 20` which the firmware uses for ACPI sleep.
Wake sends `EC 5C 10` (display reset).
