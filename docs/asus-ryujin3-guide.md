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

_New in git._<br>

The Ryujin III Extreme has a 640×480 LCD.  A static image can be displayed
with:

```
# liquidctl set lcd screen static /path/to/image.png
```

Images are resized to the native resolution and converted to RGB automatically.
The image stays on screen while the cooler remains powered.

Animated GIFs are streamed from the host computer:

```
# liquidctl set lcd screen gif /path/to/animation.gif
```

The command keeps running while the animation plays; press Ctrl+C to stop it.

To rotate through the cooler statistics with the default dashboard, run:

```
# liquidctl set lcd screen stats B300FF 5
```

The first argument is an optional six-digit RGB font colour shorthand (default:
`B300FF`); the second is an optional page interval in seconds (default: `5`).
The display runs until Ctrl+C.  Display brightness and orientation controls
are not supported.

For a configurable dashboard, pass a JSON file instead:

```
# liquidctl set lcd screen stats extra/contrib/asus_ryujin/example_layouts/ryujin_extreme_stats.json
```

The [example configuration](../extra/contrib/asus_ryujin/example_layouts/ryujin_extreme_stats.json)
shows the supported keys.  `layout` maps one to four cards to rotating `stats`
lists.  Card geometry is calculated automatically.  Built-in statistics are
`liquid_temperature`, `pump_duty`, `pump_speed`, `pump_fan_duty`, and
`pump_fan_speed`.

`background_opacity` accepts a value from `0.0` to `1.0` and can be set on the
LCD background and each card.  `offset_x` and `offset_y` adjust a card's
position in pixels.

For system telemetry, use a `custom` stat with a `command` array and optional
`unit`.  Its standard output is displayed.  The command is executed directly,
without a shell; configuration files must still be trusted because they choose
the executable.

```json
{
  "stat": "custom",
  "indicator": "GPU TEMP",
  "command": ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
  "unit": "°C"
}
```

Colours are six-digit hexadecimal strings, such as `"100713"` or `"B300FF"`.
The leading `#` is optional.

Set `background` to an image or animated GIF.  Relative paths are resolved
from the JSON file's directory.
