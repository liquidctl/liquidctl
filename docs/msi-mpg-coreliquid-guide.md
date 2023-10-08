# MSI MPG Coreliquid AIO coolers
_Driver API and source code available in [`liquidctl.driver.msi`](../liquidctl/driver/msi)._

_Currently, only the K360 model is experimentally supported as more testing and feedback is needed._

This driver is for the MSI MPG coreliquid series of AIO coolers, of which currently only the coreliquid K360 has been tested and verified to be working. The usage of speed profiles for this model requires external periodic updates of the current cpu temperature. As a result, to use variable fan speeds you must be careful to make sure that the current cpu temperature gets sent to the device. An example method to accomplish this is the `--use-device-controller` option in [`extra/yoda`](../extra/yoda).

Device configuration persists until a new configuration is sent to the device. A cold boot does not reset the device configuration, but it does erase any previous cpu temperature data from the device. The default control temperature upon starting the device is 0°C, so on boot the device fans will spin on the lowest point of a fan profile.

LED lighting is controlled via preset modes, which are sent once to the device as a configuration, after which the device then independently commands the LEDs until a new configuration is received. Lighting modes persist similarly to the fan and pump speed settings.

The K360 model includes an LCD screen capable of displaying various preset animations, hardware status, ASCII banners with a preset or custom background image, and preset or custom images.

## Initialization

Controlling the device does not require initialization. Initialization is optional, and will set default fan curves and LCD screen settings.

## Monitoring

The AIO unit is able to report fan speeds, pump speed, water block speed, and duties.

```
# liquidctl status
MSI MPG Coreliquid K360
├── Fan 1 speed          1546  rpm
├── Fan 1 duty             60  %
├── Fan 2 speed          1562  rpm
├── Fan 2 duty             60  %
├── Fan 3 speed          1530  rpm
├── Fan 3 duty             60  %
├── Water block speed    2400  rpm
├── Water block duty       50  %
├── Pump speed           2777  rpm
├── Pump duty             100  %
```
## Fan and pump speeds

First, some important notes...

*You must carefully consider what pump and fan speeds to run.  Heat output, case airflow, radiator size, installed fans and ambient temperature are some of the factors to take into account.  Test your settings under different scenarios, and make sure that they are appropriate, correctly applied and persistent.*

*The device has no internal temperature measurement to control the fan speeds, and simply running a liquidctl command to set a speed profile will not persistently provide this necessary data to the device. You can use [`extra/yoda`](../extra/yoda) to communicate with the cooler, or create your own service to keep the device updated on the current temperature.*

*You should also consider monitoring your hardware temperatures and setting alerts for overheating components or pump failures.*

With those out of the way, the pump speed can be configured to a fixed duty value or with a profile dependent on a (temperature) signal that MUST be periodically sent to the device.

Fixed speeds can be set by specifying the desired channel and duty value.

```
# liquidctl set pump speed 90
```

| Channel | Minimum duty | Maximum duty |
| --- | -- | --- |
| `pump` | 60% | 100% |
| `radiator fan` | 20% | 100% | |
| `waterblock fan` | 0% | 100% | |

For profiles, one or more temperature–duty pairs are supplied instead of single value.

```
# liquidctl set pump speed 20 30 30 50 34 80 40 90 50 100
                           ^^^^^ ^^^^^ ^^^^^ ^^^^^ ^^^^^^
                        pairs of temperature (°C) -> duty (%)
```

liquidctl will normalize and optimize this profile before pushing it to the device.  Adding `--verbose` will trace the final profile that is being applied.

The device also has preset pump/fan curves that can be applied independently for each channel with [`yoda`](../extra/yoda). Perhaps most notable is the "smart" mode, which enables fan-stop for two of the three radiator fans. Fan-stop is locked by the device for custom fan profiles, likely to prevent the liquid from overheating.

The preset device profiles are:

  - Silent
  - Balance
  - Game
  - Default
  - Smart

The preset, named modes are supported in the driver and they currently have experimental support in [`yoda`](../extra/yoda), support in the liquidctl cli is on the way.

## RGB lighting with LEDs

LEDs on the device are always synced with the same effect, so the channel argument is unused when setting colors.

Colors can be specified in RGB, HSV or HSL (see [Supported color specification formats](../README.md#supported-color-specification-formats)). Each animation mode supports zero to two colors, and some animation modes include an additional "rainbow" mode.

Some lighting modes are intended to react to the sounds currently playing on the system. These modes do not currently function as intended with this driver.

| Mode | Colors | Rainbow option | Notes |
| --- | --- | --- | --- |
| `disable` | None | None |                        |
| `steady` | One | No |                        |
| `blink` | ? | ? | Not working as intended |
| `breathing` | One | No | Yes |
| `clock` | Two | Yes |                        |
| `color pulse` | ? | ? | Not working as intended |
| `color ring` | None | None |                        |
| `color ring double flashing` | None | None |                        |
| `color ring flashing` | None | None |                        |
| `color shift` | None | None | Not working as intended  |
| `color wave` | Two | Yes |                        |
| `corsair ique` | ? | ? | Unclear   |
| `disable2` | None | None |                        |
| `double flashing` | One | Yes |                        |
| `double meteor` | None | None |                        |
| `energy` | None | None |                        |
| `fan control` | ? | ? | Not working as intended |
| `fire` | Two | No |                        |
| `flashing` | One | Yes |                        |
| `jazz` | ? | ? | Not working as intended |
| `jrainbow` | ? | ? | Unclear |
| `lava` | ? | ? | Not working as intended |
| `lightning` | One | No |                        |
| `marquee` | One | No |                        |
| `meteor` | One | Yes |                        |
| `movie` | ? | ? | Not working as intended |
| `msi marquee` | One | Yes |                        |
| `msi rainbow` | ? | ? | Not working as intended |
| `planetary` | None | None |                        |
| `play` | ? | ? | Not working as intended |
| `pop` | ? | ? | Not working as intended |
| `rainbow` | ? | ? | Very jittery and slow, rainbow wave is recommended instead |
| `rainbow double flashing` | None | None |                        |
| `rainbow flashing` | None | None |                        |
| `rainbow wave` | None | None |                        |
| `random` | None | None |                        |
| `rap` | ? | ? | Not working as intended |
| `stack` | One | Yes |                        |
| `visor` | Two | Yes |                        |
| `water drop` | One | Yes |                        |

Support for the rainbow option in the liquidctl cli is on the way, but it is included in the driver.

## The LCD screen

The screen resolution is 320 x 240 px, and custom images uploaded with this driver are resized to fit this requirement. The screen orientation and brightness (0-10) can also be controlled. The only channel available for the K360 model is "lcd".

Maximum length of the displayed banner mesages is 62 ASCII characters. hardware status display functionality is limited, as the displayed data must be communicated to the device. This functionality is implemented in the driver, but currently its usage is limited to yoda, which gpu-unaware so the gpu_freq and gpu_usage parameters will not display correct information without custom update services.


| mode name | action | options |
| --- | --- | --- |
| hardware | set the screen to display hardware info | up to 3 semicolon delimited keys from the available sensors |
| image | set the screen to display a custom or preset image | \<type (0=preset,1=custom)\>;\<index\>[;\<filename\>] |
| banner | set the screen to display a message with custom or preset image as background | \<type (0=preset,1=custom)\>;\<index\>;\<message\>[;\<filename\>]
| clock | set the screen to display system time (requires control service to send the time to the device) | integer between 0 and 2 to specify the style of the clock display |
| settings | set the screen brightness and orientation | \<brightness (0-10)\>;\<direction (0-3)\> | 
| disable | disables the lcd screen | |

| Display orientation | value |
| --- | --- |
| Default (up) | 0 |
| Right | 1 |
| Down | 2 |
| Left | 3 |


| Displayed sensor data | Notes |
| --- | --- |
| cpu_freq |  |
| cpu_temp | this is the sensor value that controls set profile fan duties |
| gpu_freq | Used by the manufacturer to display gpu memory frequency |
| gpu_usage |  |
| fan_pump |  |
| fan_radiator |  |
| fan_cpumos | waterblock fan speed |
