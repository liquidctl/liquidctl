# NZXT X3 devices

## NZXT Kraken X53, X63, X73

The Kraken X53, X63 and X73 compose the fourth generation of liquid coolers by NZXT.  These devices are manufactured by Asetek and house seventh generation Asetek pumps, plus secondary PCBs specially designed by NZXT for enhanced control and lighting.

They incorporate customizable pump speed control, a liquid temperature probe in the block and addressable RGB lighting.  The coolers are powered directly by the power supply unit.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The cooler also reports pump speed and liquid temperature via USB; pump speed can also be sent to the motherboard (or other device) via the sense pin of a standard fan connector.

All capabilities available at the hardware level are supported, but other features offered by CAM, like presets based on CPU or GPU temperatures, have not been implemented.


## Monitoring

The cooler can report the pump speed and liquid temperature.

```
# liquidctl status
NZXT Kraken X3 Pump (X53, X63 or X73) (experimental)
├── Liquid temperature    24.1  °C
├── Pump speed            1869  rpm
└── Pump duty               60  %
```


## Pump speeds

First, some important notes...

*You must carefully consider what pump and fan speeds to run.  Heat output, case airflow, radiator size, installed fans and ambient temperature are some of the factors to take into account.  Test your settings under different scenarios, and make sure that they are appropriate, correctly applied and persistent.*

*The X3 devices do not provide a way to control your fan speeds! Please set those fan curves wherever you plugged your fans in (e.g. motherboard).*

*Additionally, the liquid temperature should never reach 60°C, as at that point the pump and tubes might fail or quickly degrade.  You must monitor this during your tests and make any necessary adjustments.  As a safety measure, pump speed will forcibly be programmed to 100% for liquid temperatures of 60°C and above.*

*You should also consider monitoring your hardware temperatures and setting alerts for overheating components or pump failures.*

With those out of the way, the pump speed can be configured to a fixed duty value or with a profile dependent on the liquid temperature.  Fixed speeds can be set by specifying the desired channel – `fan` or `pump` – and duty.


```
# liquidctl set pump speed 90
```

| Channel | Minimum duty | Maximum duty |
| --- | --- | --- |
| pump | 20% | 100% |

For profiles, one or more temperature–duty pairs must be supplied.  Liquidctl will normalize and optimize this profile before pushing it to the Kraken.  Adding `--verbose` will trace the final profile that is being applied.

```
# liquidctl set pump speed  20 30  30 50  34 80  40 90  50 100
```


## RGB lighting

For lighting, the user can control a total of nine LEDs: one behind the NZXT logo and eight forming the ring that surrounds it.  These are separated into two channels, independently accessed through `logo` and `ring`.

```
# liquidctl set logo color fixed af5a2f
# liquidctl set ring color fading 350017 ff2608
# liquidctl set logo color pulse ffffff
# liquidctl set ring color backwards-marquee-5 2f6017 --speed slower
```

Colors can be specified in RGB, HSV or HSL (see [Supported color specification formats](../README.md#supported-color-specification-formats)), and each animation mode supports different number of colors.  The animation speed can be customized with the `--speed <value>`, and five relative values are accepted by the device: `slowest`, `slower`, `normal`, `faster` and `fastest`.

| `ring` | `logo` | Mode | Colors | Speed | Notes |
| :---: | :---: | --- | --- | :---: | --- |
| ✓ | ✓ | `off` | None | | 
| ✓ | ✓ | `fixed` | One | |
| ✓ | ✓ | `fading` | Between 1 and 8 | ✓ | |
| ✓ | ✓ | `super-fixed` | Between 1 and 8 | | |
| ✓ | ✓ | `spectrum-wave` | None | ✓ | |
| ✓ | ✓ | `backwards-spectrum-wave` | None | ✓ | |
| ✓ | ✓ | `marquee-<length>` | One | ✓ | 3 ≤ `length` ≤ 6 | 
| ✓ | ✓ | `backwards-marquee-<length>` | One | ✓ | 3 ≤ `length` ≤ 6 |
| ✓ | ✓ | `covering-marquee` | Between 1 and 8 | ✓ | |
| ✓ | ✓ | `covering-backwards-marquee` | Between 1 and 8 | ✓ | |
| ✓ | ✓ | `alternating-<length>` | Between 1 and 2 | ✓ | |
| ✓ | ✓ | `moving-alternating-<length>` | Between 1 and 2 | ✓ | 3 ≤ `length` ≤ 6 |
| ✓ | ✓ | `backwards-moving-alternating-<length>` | Between 1 and 2 | ✓ | 3 ≤ `length` ≤ 6 |
| ✓ | ✓ | `pulse` | Between 1 and 8 | ✓ | |
| ✓ | ✓ | `breathing` | Between 1 and 8 | ✓ | |
| ✓ | ✓ | `super-breathing` | Between 1 and 8 | ✓ | |
| ✓ | ✓ | `candle` | One | | |
| ✓ | ✓ | `starry-night` | One | ✓ | |
| ✓ | ✓ | `rainbow-flow` | None | ✓ | |
| ✓ | ✓ | `super-rainbow` | None | ✓ | |
| ✓ | ✓ | `rainbow-pulse` | None | ✓ | |
| ✓ | ✓ | `backwards-rainbow-flow` | None | ✓ | |
| ✓ | ✓ | `backwards-super-rainbow` | None | ✓ | |
| ✓ | ✓ | `backwards-rainbow-pulse` | None | ✓ | |
| ✓ | ✓ | `loading` | One | | |
| ✓ | ✓ | `tai-chi` | Between 1 and 2 | ✓ | |
| ✓ | ✓ | `water-cooler` | Two | ✓ | |
| ✓ | ✓ | `wings` | One | ✓ | |
