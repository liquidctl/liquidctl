# ASUS Ryuo I Liquid Coolers
_Driver API and source code available in [`liquidctl.driver.asus_ryuo`](../liquidctl/driver/asus_ryuo.py)._

_New in 1.16.0._<br>
_Sensor telemetry, LED control, and OLED display upload new in git._<br>

## Initialization

Initialization is not required. It outputs the firmware version:

```
# liquidctl initialize
ASUS Ryuo I 240
└── Firmware version    AURO0-S452-0205
```

## Monitoring

_New in git._

The driver reports the coolant temperature from the device's built-in sensor:

```
# liquidctl status
ASUS Ryuo I 240
└── Liquid temperature    32  °C
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

## LED control

_New in git._

Use channel `led` to control the pump-head RGB LED:

```
# liquidctl set led color static ff0000
# liquidctl set led color breathing 0000ff
# liquidctl set led color spectrum
# liquidctl set led color off
```

Available modes:

| Mode | Colors | Description |
|:---|:---:|:---|
| `off` | — | Turn LED off |
| `static` | 1 | Fixed color |
| `breathing` | 1 | Pulsing color |
| `flash` | 1 | Strobing color |
| `spectrum` | — | Cycle through full spectrum |
| `rainbow` | — | Rainbow wave effect |

## OLED display

_New in git.  Unstable._

The pump head has a 160×128 pixel OLED display.  Use channel `lcd` to upload images or animated GIFs:

```
# liquidctl set lcd screen static photo.png
# liquidctl set lcd screen gif animation.gif
```

For pump heads mounted with tubes pointing up, pass `rotation=180` to flip
the image:

```
# liquidctl set lcd screen gif animation.gif rotation=180
```

Images are automatically resized and centered to fit the 160×128 display.
Animated GIFs are re-encoded with optimized quantization for the hardware.

Requires [Pillow](https://pillow.readthedocs.io/) (`pip install pillow`).

**Note:** Large GIF files take longer to upload due to a hardware-imposed
20ms delay between 62-byte chunks (the device writes to internal SPI flash).
A 50 KB GIF takes approximately 16 seconds to upload.

## Limitations

- Fan speed (RPM) and pump speed are not available through the sensor register.
- Only fixed fan speed control is supported (no duty curves).
- OLED display upload requires Pillow as an additional dependency.
- Writing to register `0x5C` causes the OLED to go black — the driver avoids this.
