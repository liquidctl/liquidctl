# Fourth-generation NZXT liquid coolers
_Driver API and source code available in [`liquidctl.driver.kraken3`](../liquidctl/driver/kraken3.py)._

The fourth-generation of NZXT Kraken coolers is composed by X models—featuring the familiar infinity mirror—and Z models—replacing the infinity mirror with an LCD screen.

Both X and Z models house seventh-generation Asetek pump designs, plus secondary PCBs from NZXT for enhanced control and visual customization.  The coolers are powered directly from the power supply unit.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The coolers also report relevant data via USB, including pump and/or fan speeds and liquid temperature.  The pump speed can be sent to the motherboard (or other device) via the sense pin of a standard fan connector.

Monitoring and/or configuring the coolers is not possible with CAM running, otherwise you'll get errors such as `OSError('read error')`.


## NZXT Kraken X53, X63, X73

The X models incorporate customizable pump speed control, a liquid temperature probe in the block and addressable RGB lighting.  In comparison with the previous generation of X42/X52/X62/X72 coolers, fan control is no longer provided.

All capabilities available at the hardware level are supported, but other features offered by CAM, like presets based on CPU or GPU temperatures, are not part of the scope of the liquidctl CLI.


## NZXT Kraken Z53, Z63, Z73

The most notable difference between Kraken X and Kraken Z models is the replacement of the infinity mirror by a LCD screen.

In addition to this, Kraken Z coolers restore the embedded fan controller that is missing from the current Kraken X models.


## NZXT Kraken 2023 Standard, Elite

Kraken 2023 AIOs use the same pump and as their Z3 predecessor but the integrated LED controller has been removed. The LCD resolution is 240x240 for the standard version and 640x640 for the Elite variant, which also features a light ring on the pump housing. **Controlling the light ring is not yet supported**.


## NZXT Kraken Elite V2

NZXT's 2024 Kraken Elite refresh, which the cooler reports over USB as _Kraken Elite V2_.  It shares the 2023 Elite's 640x640 LCD pump and adds an addressable RGB ring around the pump cap.  A single USB id (`1e71:3012`) covers both the RGB-fan bundle (retailed as _Kraken Elite RGB_) and the plain-fan bundle (_Kraken Elite_); these are the same cooler — firmware-identical and indistinguishable over USB — so liquidctl uses the generation name for both.  As of the 1.2.1 firmware, the GIF and static LCD modes are also supported.

Three lighting channels are exposed: `ring`, the pump-cap ring; `external`, the RGB header where the bundled RGB (radiator) fans connect (empty when no RGB accessory is plugged in); and `sync`, which drives both at once.  The ring is driven with the Hue 2 _direct_ protocol; `fixed` is mapped to a per-LED `super-fixed` write so the whole ring shows a single solid color, instead of the periodic flicker the animation protocol produces on this channel.  (For a solid ring color use the `ring` channel; the same `fixed` on `sync` reaches the ring over the animation protocol and may flicker.)

```
# liquidctl set ring color fixed 00aaff
# liquidctl set external color spectrum-wave
# liquidctl set sync color breathing ff2608 --speed slower
```

NZXT RGB fans (and other Hue 2 accessories) daisy-chained to the cooler's RGB header are controlled through the `external` channel; run `liquidctl initialize` to list the connected accessories.  The complete list of color modes is in the [RGB lighting](#rgb-lighting-with-leds) section below.


## NZXT Kraken 2024 Plus

The functionality of the 2024 RGB AIO is identical to the 2023 Standard model, with a 240x240 LCD.


## Initialization

Devices must be initialized being read or written to.  This is necessary after powering on from Mechanical Off, or if there has been hardware changes.  Only then monitoring, proper fan control and all lighting effects will be available.

The firmware version and all connected LED accessories are reported during the device initialization.

```
# liquidctl initialize
NZXT Kraken X (X53, X63 or X73)
├── Firmware version                    1.8.0
├── LED accessory 1    HUE 2 LED Strip 300 mm
├── LED accessory 1          AER RGB 2 140 mm
├── LED accessory 2          AER RGB 2 140 mm
├── Pump Logo LEDs                   detected
└── Pump Ring LEDs                   detected
```


## Monitoring

The cooler can report the pump speed and liquid temperature.

```
# liquidctl status
NZXT Kraken X (X53, X63 or X73)
├── Liquid temperature    24.1  °C
├── Pump speed            1869  rpm
└── Pump duty               60  %
```


## Fan and pump speeds

First, some important notes...

*You must carefully consider what pump and fan speeds to run.  Heat output, case airflow, radiator size, installed fans and ambient temperature are some of the factors to take into account.  Test your settings under different scenarios, and make sure that they are appropriate, correctly applied and persistent.*

*The X models do not provide a way to control your fan speeds.  You must set those fan curves wherever you plugged your fans in (e.g. motherboard).*

*Additionally, the liquid temperature should never reach 60°C, as at that point the pump and tubes might fail or quickly degrade.  You must monitor this during your tests and make any necessary adjustments.  As a safety measure, pump speed will forcibly be programmed to 100% for liquid temperatures of 60°C and above.*

*You should also consider monitoring your hardware temperatures and setting alerts for overheating components or pump failures.*

With those out of the way, the pump speed can be configured to a fixed duty value or with a profile dependent on the liquid temperature.

Fixed speeds can be set by specifying the desired channel and duty value.

```
# liquidctl set pump speed 90
```

| Channel | Minimum duty | Maximum duty | X models | Z models |
| --- | -- | --- | :---: | :---: |
| `pump` | 20% | 100% | ✓ | ✓ |
| `fan` | 0% | 100% | | ✓ |

For profiles, one or more temperature–duty pairs are supplied instead of single value.

```
# liquidctl set pump speed 20 30 30 50 34 80 40 90 50 100
                           ^^^^^ ^^^^^ ^^^^^ ^^^^^ ^^^^^^
                        pairs of temperature (°C) -> duty (%)
```

liquidctl will normalize and optimize this profile before pushing it to the Kraken.  Adding `--verbose` will trace the final profile that is being applied.

_New in 1.14.0._<br>

Adds support for NZXT Kraken 2023 Standard, Elite

Adds support for NZXT Kraken Elite V2 (2024 Elite)

## RGB lighting with LEDs

One or more LED channels are provided, depending on the model.

| Channel | Type | LED count | X models | Z models | 2024 Elite |
| --- | --- | --- | :---: | :---: | :---: |
| `external` | HUE 2/HUE+ accessories | up to 40 | ✓ |  ✓ | ✓ |
| `ring` | Pump ring | 8 (X3) | ✓ | | ✓ |
| `logo` | Infinity mirror: logo | 1 | ✓ | | |
| `sync` | Synchronize all channels | up to 40 | ✓ | | ✓ |

On the 2024 Elite the `ring` is the RGB ring around the pump-cap LCD, addressed over the Hue 2 _direct_ protocol; `external` is the RGB-fan (radiator) header; and `sync` drives both together.

Color modes can be set independently for each lighting channel, but the specified color mode will then apply to all devices daisy chained on that channel.

```
# liquidctl set sync color fixed af5a2f
# liquidctl set ring color fading 350017 ff2608
# liquidctl set logo color pulse ffffff
# liquidctl set external color marquee-5 2f6017 --direction backward --speed slower
```

Colors can be specified in RGB, HSV or HSL (see [Supported color specification formats](../README.md#supported-color-specification-formats)), and each animation mode supports different number of colors.  The animation speed can be customized with the `--speed <value>`, and five relative values are accepted by the device: `slowest`, `slower`, `normal`, `faster` and `fastest`.

Some of the color animations can be in either the `forward` or `backward` direction.
This can be specified by using the `--direction` flag.

| Mode | Colors | Variable speed |
| --- | --- | :---: |
| `off` | None | |
| `fixed` | One | |
| `fading` | Between 1 and 8 | ✓ | |
| `super-fixed` | Between 1 and 40 | |
| `spectrum-wave` | None | ✓ |
| `marquee-<length>`, 3 ≤ length ≤ 6 | One | ✓ |
| `covering-marquee` | Between 1 and 8 | ✓ |
| `alternating-<length>` | Between 1 and 2 | ✓ |
| `moving-alternating-<length>`, 3 ≤ length ≤ 6 | Between 1 and 2 | ✓ |
| `pulse` | Between 1 and 8 | ✓ |
| `breathing` | Between 1 and 8 | ✓ |
| `super-breathing` | Between 1 and 40 | ✓ |
| `candle` | One | |
| `starry-night` | One | ✓ |
| `rainbow-flow` | None | ✓ |
| `super-rainbow` | None | ✓ |
| `rainbow-pulse` | None | ✓ |
| `loading` | One | |
| `tai-chi` | Between 1 and 2 | ✓ |
| `water-cooler` | Two | ✓ |
| `wings` | One | ✓ |


#### Deprecated modes

The following modes are now deprecated and the use of the `--direction backward` is preferred,
they will be removed in a future version and are kept for now for backward compatibility.

| Mode | Colors | Variable speed |
| --- | --- | :---: |
| `backwards-spectrum-wave` | None | ✓ |
| `backwards-marquee-<length>`, 3 ≤ length ≤ 6 | One | ✓ |
| `covering-backwards-marquee` | Between 1 and 8 | ✓ |
| `backwards-moving-alternating-<length>`, 3 ≤ length ≤ 6 | Between 1 and 2 | ✓ |
| `backwards-rainbow-flow` | None | ✓ |
| `backwards-super-rainbow` | None | ✓ |
| `backwards-rainbow-pulse` | None | ✓ |


## The LCD screen (only Z, 2023, 2024 models)

_New in 1.11.0._<br>

The LCD screen can be configured in a few different modes.

```
# liquidctl [options] set lcd screen liquid
# liquidctl [options] set lcd screen brightness <value>
# liquidctl [options] set lcd screen orientation (0|90|180|270)
# liquidctl [options] set lcd screen (static|gif) <path to image>
```

Images and GiFs are automatically resized and rotated to match the device orientation.

*Note that, on the 2023 models (Standard and Elite), the GIF screen mode is not currently supported
on firmware versions 2.X (see [#631][`issue-631`]).*


## Interaction with Linux hwmon drivers
[Linux hwmon]: #interaction-with-linux-hwmon-drivers

_New in 1.9.0._<br>
_Changed in 1.12.0: expanded support for reading and writing through hwmon._<br>

Kraken X3 and Z3 devices feature support by the [liquidtux] `nzxt-kraken3` driver,
and status data is provided through a standard hwmon sysfs interface.

Starting with version 1.9.0, liquidctl automatically detects when a kernel
driver is bound to the device and, whenever possible, uses it instead of
directly accessing the device. Alternatively, direct access to the device can
be forced with `--direct-access`.

[liquidtux]: https://github.com/liquidctl/liquidtux
[`issue-631`]: https://github.com/liquidctl/liquidctl/issues/631
