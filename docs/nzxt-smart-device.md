## NZXT Smart Device
<!-- move to /doc -->

The Smart Device is a fan and LED controller that ships with the H200i, H400i, H500i and H700i cases.

It provides three independent fan channels with standard 4-pin connectors.  Both PWM and DC control is supported, and the device automatically chooses the appropriate mode.

Additionally, up to four chained HUE+ LED strips can be driven from a single channel.  The firmware installed on the device exposes several presets, most of them familiar to other NZXT products.

A microphone is also present onboard, for  noise level optimization through CAM and AI.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The device also reports the state of each fan channel, as well as speed, voltage and current.

All capabilities available at the hardware level are supported, but other features offered by CAM, like noise level optimization, have not been implemented.


## Initialization

After powering on from Mechanical Off, or if there have been hardware changes, the device must be re-initilizated.

```
liquidctl reset
```

Connected fans and LED strips will be detected and data reporting will begin.


## Fan speeds

Fan speeds can only be set to fixed PWM duty values.

```
# liquidctl set fan2 speed 90
```

| Channel | Minimum duty | Maximum duty |
| --- | --- | --- |
| fan1 | 0% | 100% |
| fan2 | 0% | 100% |
| fan3 | 0% | 100% |

**Always check that the settings are appropriate for the use case, and that they correctly apply and persist.**


## RGB lighting

For lighting, the user can control up to 40 LEDs, if all four strips are connected.  They are chained in a single channel: `led`.

```
# liquidctl set led color fixed af5a2f
# liquidctl set led color fading 350017 ff2608 --speed slower
# liquidctl set led color pulse ffffff
# liquidctl set led color backwards-marquee-5 2f6017 --speed slowest
```

Colors are set in hexadecimal RGB, and each animation mode supports different number of colors.  The animation speed can be customized with the `--speed <value>`, and five relative values are accepted by the device: `slowest`, `slower`, `normal`, `faster` and `fastest`.

| Mode | Colors | Notes |
| --- | --- | --- |
| `off` | None |
| `fixed` | One |
| `super-fixed` | Up to 40, one for each LED |
| `fading` | Between 2 and 8, one for each step |
| `spectrum-wave` | None |
| `backwards-spectrum-wave` | None |
| `super-wave` | Up to 40 |
| `backwards-super-wave` | Up to 40 |
| `marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| `backwards-marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| `covering-marquee` | Up to 8, one for each step |
| `covering-backwards-marquee` | Up to 8, one for each step |
| `alternating` | Two |
| `moving-alternating` | Two |
| `backwards-moving-alternating` | Two |
| `breathing` | Up to 8, one for each step |
| `super-breathing` | Up to 40, one for each LED | Only one step |
| `pulse` | Up to 8, one for each pulse |
| `candle` | One |
| `wings` | One |
