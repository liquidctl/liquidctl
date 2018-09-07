# NZXT Kraken X, 3rd generation
<!-- move to /doc once there are more devices -->

The Kraken X42, X52, X62 and X72 compose the third generation of liquid coolers by NZXT.  These devices are manufactured by Asetek and house fifth generation Asetek pumps and PCBs, plus secondary PCBs specially designed by NZXT for enhanced control and lighting.

They incorporate customizable fan and pump speed control with PWM, a liquid temperature probe in the block and addressable RGB lighting.  The coolers are powered directly by the power supply unit.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The cooler also reports fan and pump speed and liquid temperature via USB; pump speed can also be sent to the motherboard (or other device) via the sense pin of a standard fan connector.


## Fan and pump speeds

Fan and pump speeds can be set either to fixed PWM duty values or as profiles dependent on the liquid temperature.

Fixed speed values can be set simply by specifying the desired channel (`fan` or `pump`) and PWM duty.

```
# liquidctl set pump speed 90
```

| Channel | Minimum duty | Maximum duty |
| --- | --- | --- |
| fan | 25% | 100% |
| pump | 60% | 100% |

For profiles, any number of temperature–duty pairs can be specified; liquidctl will normalize and optimize the profile before pushing it to the Kraken.  You can use `--verbose` to inspect the final profile.

```
# liquidctl set fan speed  20 30  30 50  34 80  40 90  50 100
```

As a safety measure, fan and pump speeds will always be set to 100% for liquid temperatures of 60°C and above.

**Always check that the settings are appropriate for the use case, and that they correctly apply and persist.**


## RGB lighting

For lighting, the user can control a total of nine LEDs: one behind the NZXT logo and eight forming the ring that surrounds it.  These are separated into two channels, independently accessed through `logo` and `ring`, or synchronized with `sync`.

```
# liquidctl set sync color fixed af5a2f
# liquidctl set ring color fading 350017 ff2608
# liquidctl set logo color pulse ffffff
# liquidctl set ring color backwards-marquee-5 2f6017 --speed slower
```

Colors are set in hexadecimal RGB, and each animation mode supports different number of colors.  The animation speed can be customized with the `--speed <value>`, and five relative values are accepted by the device: `slowest`, `slower`, `normal`, `faster` and `fastest`.

| `ring` | `logo` | `sync` | Mode | Colors | Notes |
| --- | --- | --- | --- | --- | --- |
| ✓ | ✓ | ✓ | `off` | None |
| ✓ | ✓ | ✓ | `fixed` | One |
| ✓ | ✓ | ✓ | `super-fixed` | Up to 9 (logo + each ring LED) |
| ✓ | ✓ | ✓ | `fading` | Between 2 and 8, one for each step |
| ✓ | ✓ | ✓ | `spectrum-wave` | None |
| ✓ | ✓ | ✓ | `backwards-spectrum-wave` | None |
| ✓ |   |   | `super-wave` | Up to 8 |
| ✓ |   |   | `backwards-super-wave` | Up to 8 |
| ✓ |   |   | `marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| ✓ |   |   | `backwards-marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| ✓ |   |   | `covering-marquee` | Up to 8, one for each step |
| ✓ |   |   | `covering-backwards-marquee` | Up to 8, one for each step |
| ✓ |   |   | `alternating` | Two |
| ✓ |   |   | `moving-alternating` | Two |
| ✓ |   |   | `backwards-moving-alternating` | Two |
| ✓ | ✓ | ✓ | `breathing` | Up to 8, one for each step |
| ✓ | ✓ | ✓ | `super-breathing` | Up to 9 (logo + each ring LED) | Only one step |
| ✓ | ✓ | ✓ | `pulse` | Up to 8, one for each pulse |
| ✓ |   |   | `tai-chi` | Two |
| ✓ |   |   | `water-cooler` | None |
| ✓ |   |   | `loading` | One |
| ✓ |   |   | `wings` | One |
