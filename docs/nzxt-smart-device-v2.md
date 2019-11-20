# HUE 2, HUE 2 Ambient and Smart Device V2

The NZXT HUE 2 lighting system is a refresh of the original HUE+.  The main improvement is the ability to mix Aer RGB 2 fans and HUE 2 lighting accessories (e.g. HUE 2 LED strip, HUE 2 Underglow, HUE 2 Cable Comb) in a channel.  HUE+ devices, including the original Aer RGB fans, are also supported, but HUE 2 components cannot be mixed with HUE+ components in the same channel.

Each channel supports up to 6 accessories and a total of 40 LEDs, and the firmware exposes several color presets, most of them common to other NZXT products.

All configuration is done through USB, and persists as long as the device still gets power, even if the system has gone to Soft Off (S5) state.  Most capabilities available at the hardware level are supported, but other features offered by CAM, like noise level optimization and presets based on CPU/GPU temperatures, have not been implemented.


## NZXT HUE 2

The NZXT HUE 2 controller features four lighting channels.


## NZXT HUE 2 Ambient

The NZXT HUE 2 Ambient controller features two lighting channels.


## NZXT Smart Device V2

The NZXT Smart Device V2 is a HUE 2 variant of the original Smart Device fan and LED controller, that ships with NZXT's cases released in mid-2019 including the H510 Elite, H510i, H710i, and H210i.

It provides two HUE 2 lighting channels and three independent fan channels with standard 4-pin connectors.  Both PWM and DC fan control is supported, and the device automatically chooses the appropriate mode for each channel; the device also reports the state of each fan channel, as well as speed and duty (from 0% to 100%).

A microphone is still present onboard for noise level optimization through CAM and AI.


## Initialization

After powering on from Mechanical Off, or if there have been hardware changes, the device must first be initialized.  Only then monitoring, proper fan control and all lighting effects will be available.  The firmware version and the connected LED accessories are also reported during device initialization.

```
# liquidctl initialize
NZXT Smart Device V2 (experimental)
├── Firmware version                      1.5.0  
├── LED 1 accessory 1    HUE 2 LED Strip 300 mm  
├── LED 1 accessory 2    HUE 2 Underglow 200 mm  
├── LED 1 accessory 3    HUE 2 Underglow 200 mm  
├── LED 2 accessory 1          AER RGB 2 140 mm  
├── LED 2 accessory 2          AER RGB 2 140 mm  
├── LED 2 accessory 3          AER RGB 2 140 mm  
└── LED 2 accessory 4          AER RGB 2 120 mm  
```


## Monitoring

The device can report fan information for each channel and the noise level at the onboard sensor

```
# liquidctl status
NZXT Smart Device V2 (experimental)
├── Fan 2 duty                              42  %
├── Fan 2 speed                            934  rpm
└── Noise level                             62  dB
```


## Fan speeds

_Only NZXT Smart Device V2_

Fan speeds can only be set to fixed duty values.

```
# liquidctl set fan2 speed 90
```

| Channel | Minimum duty | Maximum duty | Note |
| --- | --- | --- | - |
| fan1 | 0% | 100% ||
| fan2 | 0% | 100% ||
| fan3 | 0% | 100% ||
| sync | 0% | 100% | all available channels |

*Always check that the settings are appropriate for the use case, and that they correctly apply and persist.*


## RGB lighting

LED channels are numbered sequentially: `led1`, `led2`, (only HUE 2: `led3`, `led4`).  Color modes can be set independently for each lighting channel, but the specified color mode will then apply to all devices daisy chained on that channel.

```
# liquidctl set led1 color fixed af5a2f
# liquidctl set led2 color fading 350017 ff2608 --speed slower
# liquidctl set led3 color pulse ffffff
# liquidctl set led4 color backwards-marquee-5 2f6017 --speed slowest
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
| `marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| `backwards-marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| `covering-marquee` | Up to 8, one for each step |
| `covering-backwards-marquee` | Up to 8, one for each step |
| `alternating-<length>` | Two | 3 ≤ `length` ≤ 6 |
| `moving-alternating-<length>` | Two | 3 ≤ `length` ≤ 6 |
| `backwards-moving-alternating-<length>` | Two | 3 ≤ `length` ≤ 6 |
| `pulse` | Up to 8, one for each pulse |
| `breathing` | Up to 8, one for each step |
| `super-breathing` | Up to 40, one for each LED | Only one step |
| `candle` | One |
| `starry-night` | One |
| `rainbow-flow` | None |
| `backwards-rainbow-flow` | None |
| `super-rainbow` | None |
| `backwards-super-rainbow` | None |
| `rainbow-pulse` | None |
| `backwards-rainbow-pulse` | None |
| `wings` | One |
