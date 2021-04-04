# Third-generation NZXT liquid coolers
_Driver API and source code available in [`liquidctl.driver.kraken2`](../liquidctl/driver/kraken2.py)._

## NZXT Kraken X42, X52, X62, X72

The Kraken X42, X52, X62 and X72 are the third generation of Kraken X liquid coolers by NZXT.  These devices are manufactured by Asetek and house fifth generation Asetek pumps, plus secondary PCBs specially designed by NZXT for enhanced control and lighting.

They incorporate customizable fan and pump speed control with PWM, a liquid temperature probe in the block and addressable RGB lighting.  The coolers are powered directly from the power supply unit.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The cooler also reports fan and pump speed and liquid temperature via USB; pump speed can also be sent to the motherboard (or other device) via the sense pin of a standard fan connector.

All capabilities available at the hardware level are supported, but other features offered by CAM, like presets based on CPU or GPU temperatures, have not been implemented.  Pump and fan control based on liquid temperature is supported on units running firmware versions 4 or above.


## NZXT Kraken M22

This driver also supports the NZXT Kraken M22.  However, this device has no pump or fan control, nor reports liquid temperatures.


## Monitoring

The cooler can report the fan and pump speed, as well as the liquid temperature.

```
# liquidctl status
NZXT Kraken X (X42, X52, X62 or X72)
├── Liquid temperature     29.9  °C
├── Fan speed               853  rpm
├── Pump speed             1948  rpm
└── Firmware version      6.0.2  
```


## Fan and pump speeds

First, some important notes...

*You must carefully consider what pump and fan speeds to run.  Heat output, case airflow, radiator size, installed fans and ambient temperature are some of the factors to take into account.  Test your settings under different scenarios, and make sure that they are appropriate, correctly applied and persistent.*

*Additionally, the liquid temperature should never reach 60°C, as at that point the pump and tubes might fail or quickly degrade.  You must monitor this during your tests and make any necessary adjustments.  As a safety measure, fan and pump speeds will forcibly be programmed to 100% for liquid temperatures of 60°C and above.*

*You should also consider monitoring your hardware temperatures and setting alerts for overheating components or pump failures.*

With those out of the way, each channel can be independently configured to a fixed duty value or with a profile dependent on the liquid temperature.  Fixed speeds can be set by specifying the desired channel – `fan` or `pump` – and duty.


```
# liquidctl set pump speed 90
```

| Channel | Minimum duty | Maximum duty |
| --- | --- | --- |
| fan | 25% | 100% |
| pump | 50% | 100% |

*Another important note: pump speeds between 50% and 60% are not currently exposed in CAM.  Presumably, there might be some scenarios when these lower speeds are not suitable.*

For profiles, one or more temperature–duty pairs must be supplied.  liquidctl will normalize and optimize this profile before pushing it to the Kraken.  Adding `--verbose` will trace the final profile that is being applied.

```
# liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
```


## RGB lighting

For lighting, the user can control a total of nine LEDs: one behind the NZXT logo and eight forming the ring that surrounds it.  These are separated into two channels, independently accessed through `logo` and `ring`, or synchronized with `sync`.

```
# liquidctl set sync color fixed af5a2f
# liquidctl set ring color fading 350017 ff2608
# liquidctl set logo color pulse ffffff
# liquidctl set ring color marquee-5 2f6017 --direction backward --speed slower
```

Colors can be specified in RGB, HSV or HSL (see [Supported color specification formats](../README.md#supported-color-specification-formats)), and each animation mode supports different number of colors.  The animation speed can be customized with the `--speed <value>`, and five relative values are accepted by the device: `slowest`, `slower`, `normal`, `faster` and `fastest`.

Some of the color animations can be in either the `forward` or `backward` direction.
This can be specified by using the `--direction` flag.

| `ring` | `logo` | `sync` | Mode | Colors | Notes |
| --- | --- | --- | --- | --- | --- |
| ✓ | ✓ | ✓ | `off` | None |
| ✓ | ✓ | ✓ | `fixed` | One |
| ✓ | ✓ | ✓ | `super-fixed` | Up to 9 (logo + each ring LED) |
| ✓ | ✓ | ✓ | `fading` | Between 2 and 8, one for each step |
| ✓ | ✓ | ✓ | `spectrum-wave` | None |
| ✓ |   |   | `super-wave` | Up to 8 |
| ✓ |   |   | `marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| ✓ |   |   | `covering-marquee` | Up to 8, one for each step |
| ✓ |   |   | `alternating` | Two |
| ✓ |   |   | `moving-alternating` | Two |
| ✓ | ✓ | ✓ | `breathing` | Up to 8, one for each step |
| ✓ | ✓ | ✓ | `super-breathing` | Up to 9 (logo + each ring LED) | Only one step |
| ✓ | ✓ | ✓ | `pulse` | Up to 8, one for each pulse |
| ✓ |   |   | `tai-chi` | Two |
| ✓ |   |   | `water-cooler` | None |
| ✓ |   |   | `loading` | One |
| ✓ |   |   | `wings` | One |


#### Deprecated modes

The following modes are now deprecated and the use of the `--direction backward` is preferred,
they will be removed in a future version and are kept for now for backward compatibility.

| `ring` | `logo` | `sync` | Mode | Colors | Notes |
| --- | --- | --- | --- | --- | --- |
| ✓ | ✓ | ✓ | `backwards-spectrum-wave` | None |
| ✓ |   |   | `backwards-super-wave` | Up to 8 |
| ✓ |   |   | `backwards-marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| ✓ |   |   | `covering-backwards-marquee` | Up to 8, one for each step |
| ✓ |   |   | `backwards-moving-alternating` | Two |
