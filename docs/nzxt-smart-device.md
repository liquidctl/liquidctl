# NZXT Smart Device V1/V2 and Grid+ V3

The Smart Device is a fan and LED controller that ships with the H200i, H400i, H500i and H700i cases.  The NZXT Smart Device V2 is a newer model of the original fan and LED controller. It ships with NZXT's cases released in mid-2019 including the H510 Elite, H510i, H710i, and H210i.

Both versions of the Smart Device provide three independent fan channels with standard 4-pin connectors; PWM and DC control is supported, and the device automatically chooses the appropriate mode.

The Smart Device (V1) only supports only HUE+ accessories.  Up to four chained HUE+ LED strips or five chained Aer RGB fans can be driven from the single RGB channel.

The Smart Device V2 adds support for HUE 2 and a second LED channel.  HUE 2 and HUE+ devices (including Aer RGB 2 and Aer RGB fans) are supported, but HUE 2 components cannot be mixed with HUE+ components in the same channel. Each lighting channel supports up to 6 HUE 2 or 4 HUE+ accessories, and a total of 40 LEDs.

The firmware installed on the device exposes several lighting presets, most of them familiar to other NZXT products.  A microphone is also present onboard for noise level optimization through CAM and AI.

The NZXT Grid+ V3 is a fan controller very similar to the Smart Device (V1): the Grid+ has more fan channels (six in total), and no support for LEDs or onboard microphone.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  The device also reports the state of each fan channel, as well as speed, voltage and current.

All capabilities available at the hardware level are supported, but other features offered by CAM, like noise level optimization and presets based on CPU/GPU temperatures, have not been implemented.


## Experimental support

Support for the NZXT Grid+ V3 and for the NZXT Smart Device V2 is currently **experimental**.


## Experimental support for the Smart Device V2

This driver also has **experimental** support for the NZXT Smart Device V2, which has an extra LED channel over the original Smart Device.


## Initialization

After powering on from Mechanical Off, or if there have been hardware changes, the device must first be initialized.  This takes a few seconds and should detect all connected fans and LED accessories.  Only then monitoring, proper fan control and all lighting effects will be available.

```
# liquidctl initialize
```


## Monitoring

The device can report fan information for each channel, the noise level at the onboard sensor, as well as the type of the connected LED accessories.

```
# liquidctl status
Device 0, NZXT Smart Device (V1)
Fan 1                        PWM     
Fan 1 current               0.03  A  
Fan 1 speed                 1634  rpm
Fan 1 voltage              11.91  V  
Fan 2                        PWM     
Fan 2 current               0.07  A  
Fan 2 speed                 1618  rpm
Fan 2 voltage              11.91  V  
Fan 3                        PWM     
Fan 3 current               0.03  A  
Fan 3 speed                 1732  rpm
Fan 3 voltage              11.91  V  
Firmware version           1.0.7     
LED accessories                2     
LED accessory type    HUE+ Strip     
LED count (total)             20     
Noise level                   61  dB 
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

Up to 40 LEDs can be controlled per channel.

| Device | Channels |
| --- | --- |
| Smart Device | `led` |
| Smart Device V2 | `led1`, `led2` |
| Grid+ V3 | — |

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
