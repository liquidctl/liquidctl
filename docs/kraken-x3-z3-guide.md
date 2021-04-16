# Fourth-generation NZXT liquid coolers
_Driver API and source code available in [`liquidctl.driver.kraken3`](../liquidctl/driver/kraken3.py)._

The fourth-generation of NZXT Kraken coolers is composed by X models—featuring the familiar infinity mirror—and Z models—replacing the infinity mirror with an LCD screen.

Both X and Z models house seventh-generation Asetek pump designs, plus secondary PCBs from NZXT for enhanced control and visual customization.  The coolers are powered directly from the power supply unit.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The coolers also report relevant data via USB, including pump and/or fan speeds and liquid temperature.  The pump speed can be sent to the motherboard (or other device) via the sense pin of a standard fan connector.


## NZXT Kraken X53, X63, X73

The X models incorporate customizable pump speed control, a liquid temperature probe in the block and addressable RGB lighting.  In comparison with the previous generation of X42/X52/X62/X72 coolers, fan control is no longer provided.

All capabilities available at the hardware level are supported, but other features offered by CAM, like presets based on CPU or GPU temperatures, are not part of the scope of the liquidctl CLI.


## NZXT Kraken Z53, Z63, Z73

The most notable difference between Kraken X and Kraken Z models is the replacement of the infinity mirror by a LCD screen.

In addition to this, Kraken Z coolers restore the embedded fan controller that is missing from the current Kraken X models.

The LCD screen cannot yet be controlled with liquidctl, but all other hardware capabilities are supported.


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
| --- | --- | --- | :---: | :---: |
| `pump` | 20% | 100% | ✓ | ✓ |
| `fan` | 20% | 100% | | ✓ |

For profiles, one or more temperature–duty pairs are supplied instead of single value.

```
# liquidctl set pump speed 20 30 30 50 34 80 40 90 50 100
                           ^^^^^ ^^^^^ ^^^^^ ^^^^^ ^^^^^^
                        pairs of temperature (°C) -> duty (%)
```

liquidctl will normalize and optimize this profile before pushing it to the Kraken.  Adding `--verbose` will trace the final profile that is being applied.


## RGB lighting with LEDs

One or more LED channels are provided, depending on the model.

| Channel | Type | LED count | X models | Z models |
| --- | --- | --- | :---: | :---: |
| `external` | HUE 2/HUE+ accessories | up to 40 | ✓ |  ✓ |
| `ring` | Infinity mirror: ring | 8 | ✓ | |
| `logo` | Infinity mirror: logo | 1 | ✓ | |
| `sync` | Synchronize all channels | up to 40 | ✓ | |

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

## The LCD screen (only Z models)

To be implemented.
