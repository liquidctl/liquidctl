# NZXT Smart Device (V1) and Grid+ V3
_Driver API and source code available in [`liquidctl.driver.smart_device`](../liquidctl/driver/smart_device.py)._

The Smart Device is a fan and LED controller that ships with the H200i, H400i, H500i and H700i cases.

It provides three independent fan channels with standard 4-pin connectors.  Both PWM and DC control is supported, and the device automatically chooses the appropriate mode.

Additionally, up to four chained HUE+ LED strips or five chained Aer RGB fans can be driven from a single RGB channel.  The firmware installed on the device exposes several presets, most of them familiar to other NZXT products.

A microphone is also present onboard for noise level optimization through CAM and AI.

This driver also supports the NZXT Grid+ V3 fan controller, which has six fan speed channels but no LED support or microphone.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The device also reports the state of each fan channel, as well as speed, voltage and current.

All capabilities available at the hardware level are supported, but other features offered by CAM, like noise level optimization and presets based on CPU/GPU temperatures, have not been implemented.


## Initialization

After powering on from Mechanical Off, or if there have been hardware changes, the device must first be initialized.  This takes a few seconds and should detect all connected fans and LED accessories.  Only then monitoring, proper fan control and all lighting effects will be available.

```
# liquidctl initialize
```


## Monitoring

The device can report fan information for each channel, the noise level at the onboard sensor, as well as the type of the connected LED accessories.

```
# liquidctl status
NZXT Smart Device (V1)
├── Fan 1 speed                 1473  rpm
├── Fan 1 voltage              11.91  V
├── Fan 1 current               0.01  A
├── Fan 1 control mode           PWM
├── Fan 2 speed                 1341  rpm
├── Fan 2 voltage              11.91  V
├── Fan 2 current               0.02  A
├── Fan 2 control mode            DC
├── Fan 3 speed                 1352  rpm
├── Fan 3 voltage              11.91  V
├── Fan 3 current               0.02  A
├── Fan 3 control mode           N/A
├── Firmware version           1.0.7
├── LED accessories                2
├── LED accessory type    HUE+ Strip
├── LED count (total)             20
└── Noise level                   65  dB
```


## Fan speeds

Fan speeds can only be set to fixed duty values.

```
# liquidctl set fan2 speed 90
```

| Channel | Minimum duty | Maximum duty | Note |
| --- | --- | --- | - |
| fan1 | 0% | 100% ||
| fan2 | 0% | 100% ||
| fan3 | 0% | 100% ||
| fan4 | 0% | 100% | Grid+ V3 only |
| fan5 | 0% | 100% | Grid+ V3 only |
| fan6 | 0% | 100% | Grid+ V3 only |
| sync | 0% | 100% | all available channels |

*Always check that the settings are appropriate for the use case, and that they correctly apply and persist.*


## RGB lighting

_Only NZXT Smart Device (V1)_

For lighting, the user can control up to 40 LEDs, if all four strips or five fans are connected.  They are chained in a single channel: `led`.

```
# liquidctl set led color fixed af5a2f
# liquidctl set led color fading 350017 ff2608 --speed slower
# liquidctl set led color pulse ffffff
# liquidctl set led color marquee-5 2f6017 --direction backward --speed slowest
```

Colors can be specified in RGB, HSV or HSL (see [Supported color specification formats](../README.md#supported-color-specification-formats)), and each animation mode supports different number of colors.  The animation speed can be customized with the `--speed <value>`, and five relative values are accepted by the device: `slowest`, `slower`, `normal`, `faster` and `fastest`.

Some of the color animations can be in either the `forward` or `backward` direction.
This can be specified by using the `--direction` flag.

| Mode | Colors | Notes |
| --- | --- | --- |
| `off` | None |
| `fixed` | One |
| `super-fixed` | Up to 40, one for each LED |
| `fading` | Between 2 and 8, one for each step |
| `spectrum-wave` | None |
| `super-wave` | Up to 40 |
| `marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| `covering-marquee` | Up to 8, one for each step |
| `alternating` | Two |
| `moving-alternating` | Two |
| `breathing` | Up to 8, one for each step |
| `super-breathing` | Up to 40, one for each LED | Only one step |
| `pulse` | Up to 8, one for each pulse |
| `candle` | One |
| `wings` | One |

#### Deprecated modes

The following modes are now deprecated and the use of the `--direction backward` is preferred,
they will be removed in a future version and are kept for now for backward compatibility.

| Mode | Colors | Notes |
| --- | --- | --- |
| `backwards-spectrum-wave` | None |
| `backwards-super-wave` | Up to 40 |
| `backwards-marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| `covering-backwards-marquee` | Up to 8, one for each step |
| `backwards-moving-alternating` | Two |
