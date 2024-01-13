# NZXT HUE 2 and Smart Device V2 controllers
_Driver API and source code available in [`liquidctl.driver.smart_device`](../liquidctl/driver/smart_device.py)._

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

## NZXT H1 V2

_New in 1.10.0._<br>

The second revision of the NZXT H1 case, labeled H1 V2, ships with a variant of the NZXT Smart Device V2 that handles both the internal fans and the AIO pump. Two fan and one pump channels are available,
where the formers can be controlled via PWM or DC. The pump speed is not user controllable. The device reports the state, speed and duty of each fan channel, as well as the pump speed.

There are no lighting channels available nor an onboard microphone.

## NZXT RGB & Fan Controller

The NZXT RGB & Fan Controller is a retail version of the NZXT Smart Device V2.

## NZXT RGB & Fan Controller (3+6 channels)

_New in 1.12.1._<br>

In 2022 NZXT released a new version of the RGB & Fan Controller with 3 fan speed channels and 6 lighting channels.

For now, this new version is only partially supported by liquidctl: only monitoring and fan control are available.


## Initialization

After powering on from Mechanical Off, or if there have been hardware changes, the device must first be initialized.  Only then monitoring, proper fan control and all lighting effects will be available.  The firmware version and the connected LED accessories are also reported during device initialization.

```
# liquidctl initialize
NZXT Smart Device V2
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

_Changed in 1.9.0: the noise level is not available when data is read from
[Linux hwmon]._<br>

The device can report fan information for each channel and the noise level at
the on-board sensor.

```
# liquidctl status
NZXT Smart Device V2
├── Fan 2 control mode                     PWM
├── Fan 2 duty                              42  %
├── Fan 2 speed                            934  rpm
└── Noise level                             62  dB
```


## Fan speeds

_Only Smart Device V2, RGB & Fan Controller and H1 V2_

Fan speeds can only be set to fixed duty values.

```
# liquidctl set fan2 speed 90
```

| Channel | Minimum duty | Maximum duty | Note |
| --- | --- | --- | --- |
| fan1 | 0% | 100% | H1 V2: GPU exhaust fan |
| fan2 | 0% | 100% | H1 V2: AIO fan |
| fan3 | 0% | 100% | H1 V2: not available |
| sync | 0% | 100% | all available channels |

*Always check that the settings are appropriate for the use case, and that they correctly apply and persist.*


## RGB lighting

LED channels are numbered sequentially: `led1`, `led2`, etc., up to the number of channels supported by the device.  Color modes can be set independently for each lighting channel, but the specified color mode will then apply to all devices daisy chained on that channel.  There is also a `sync` channel.

```
# liquidctl set led1 color fixed af5a2f
# liquidctl set led2 color fading 350017 ff2608 --speed slower
# liquidctl set led3 color pulse ffffff
# liquidctl set led4 color marquee-5 2f6017 --direction backward --speed slowest
# liquidctl set sync color spectrum-wave
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
| `marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| `covering-marquee` | Up to 8, one for each step |
| `alternating-<length>` | Two | 3 ≤ `length` ≤ 6 |
| `moving-alternating-<length>` | Two | 3 ≤ `length` ≤ 6 |
| `pulse` | Up to 8, one for each pulse |
| `breathing` | Up to 8, one for each step |
| `super-breathing` | Up to 40, one for each LED | Only one step |
| `candle` | One |
| `starry-night` | One |
| `rainbow-flow` | None |
| `super-rainbow` | None |
| `rainbow-pulse` | None |
| `wings` | One |

#### Deprecated modes

The following modes are now deprecated and the use of the `--direction backward` is preferred,
they will be removed in a future version and are kept for now for backward compatibility.

| Mode | Colors | Notes |
| --- | --- | --- |
| `backwards-spectrum-wave` | None |
| `backwards-marquee-<length>` | One | 3 ≤ `length` ≤ 6 |
| `covering-backwards-marquee` | Up to 8, one for each step |
| `backwards-moving-alternating-<length>` | Two | 3 ≤ `length` ≤ 6 |
| `backwards-rainbow-flow` | None |
| `backwards-super-rainbow` | None |
| `backwards-rainbow-pulse` | None |


## Interaction with Linux hwmon drivers
[Linux hwmon]: #interaction-with-linux-hwmon-drivers

_New in 1.9.0._<br>

Smart Device V2 controllers are supported by the mainline Linux kernel with its
[`nzxt-smart2`] driver, and status data is provided through a standard hwmon
sysfs interface.

Starting with version 1.9.0, liquidctl automatically detects when a kernel
driver is bound to the device and, whenever possible, uses it instead of
directly accessing the device.  Alternatively, direct access to the device can
be forced with `--direct-access`.

[`nzxt-smart2`]: https://www.kernel.org/doc/html/latest/hwmon/nzxt-smart2.html
