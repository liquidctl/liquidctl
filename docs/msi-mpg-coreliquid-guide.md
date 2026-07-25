# MSI MPG Coreliquid AIO coolers
_Driver API and source code available in [`liquidctl.driver.msi`](../liquidctl/driver/msi.py)._

_The K360 and D360 models are experimentally supported as more testing and feedback is needed._

## Supported models

_New in git: the MPG Coreliquid D360._<br>

| Model | USB id | Cooling & monitoring | RGB lighting | LCD/OLED display |
| --- | --- | --- | --- | --- |
| MPG Coreliquid K360 | `0db0:b130` | yes | yes (`sync`) | yes |
| MPG Coreliquid D360 | `0db0:edfc` | yes | none on the device | yes, as a separate device (`0db0:8dbf`) |

The **D360** reuses the same cooling and monitoring protocol as the K360 and has
been verified against hardware for status reporting and fan/pump control.  It
does not require any unsafe feature.  It differs from the K360 in a few ways:

- It has no addressable RGB lighting, so the `sync` lighting channel does not
  apply.
- Its display is a **separate USB device** and uses a different protocol than
  the K360's OLED, so the `lcd` screen commands (and `set_time`) raise
  `NotSupportedByDevice` on the cooler itself.  See
  [The D-series LCD screen](#the-d-series-lcd-screen) below.
- A fixed speed set with `liquidctl set <channel> speed <duty>` takes effect on
  its own (the driver sends the device the control temperature it needs).  The
  device enforces its own temperature-linked minimum duty (a safety floor of
  roughly 30–35% when cool), so requests below that floor settle at the floor
  rather than going lower.  Fan speeds also ramp gradually toward the target.

This driver is for the MSI MPG coreliquid series of AIO coolers.  The coreliquid
K360 has been tested and verified to be working, and the D360 has been verified
for cooling and monitoring (see above). The usage of speed profiles requires external periodic updates of the current cpu temperature. As a result, to use variable fan speeds you must be careful to make sure that the current cpu temperature gets sent to the device. An example method to accomplish this is the `--use-device-controller` option in [`yoda.py`](../extra/yoda.py). Fan profiles persist until a new configuration is sent to the device, but saved settings are lost after power is lost (power state S5).

The remainder of this section applies to the K360, which has RGB lighting and a display. Its lighting configuration likewise persists until a new one is sent to the device, and is also lost after power is lost (power state S5). Uploaded display images are saved onto the device, and so they can be accessed by their uploaded type and index even after loss of power, preventing the need to repeatedly upload the same files. The lcd display resets to the default animation when the system is suspended (S3).

LED lighting is controlled via preset modes, which are sent once to the device as a configuration, after which the device then independently commands the LEDs until a new configuration is received.

The K360 model includes an LCD screen capable of displaying various preset animations, hardware status, ASCII banners with a preset or custom background image, and preset or custom images.

## Initialization

Controlling the device does not always require initialization, but some features, such as changing the display settings may not function before initialization. Initialization on its own will set default fan curves and LCD screen settings.

```
# liquidctl initialize --pump-mode smart
MSI MPG Coreliquid K360
├── Display firmware version               2
├── APROM firmware version                 0
├── LDROM firmware version               256
├── Serial number               A02020123456
└── Pump mode                          smart
```

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

*The device has no internal temperature measurement to control the fan speeds, and simply running a liquidctl command to set a speed profile will not persistently provide this necessary data to the device. You can use [`yoda.py`](../extra/yoda.py) to communicate with the cooler, or create your own service to keep the device updated on the current temperature.*

*You should also consider monitoring your hardware temperatures and setting alerts for overheating components or pump failures.*

With those out of the way, the pump speed can be configured to a fixed duty value or with a profile dependent on a (temperature) signal that MUST be periodically sent to the device.

Fixed speeds can be set by specifying the desired channel and duty value.

```
# liquidctl set pump speed 90
```

| Channel | Minimum duty | Maximum duty |
| --- | -- | --- |
| `pump` | 60% | 100% |
| radiator fans (`fans`, `fan1`, `fan2`, `fan3`) | 20% | 100% | |
| `waterblock-fan` | 0% | 100% | |

For profiles, one or more temperature–duty pairs are supplied instead of single value.

```
# liquidctl set pump speed 20 30 30 50 34 80 40 90 50 100
                           ^^^^^ ^^^^^ ^^^^^ ^^^^^ ^^^^^^
                        pairs of temperature (°C) -> duty (%)
```

liquidctl will normalize and optimize this profile before pushing it to the device.  Adding `--verbose` will trace the final profile that is being applied.

The device also has preset pump/fan curves that can be applied independently for each channel with [`yoda.py`](../extra/yoda.py). Perhaps most notable is the "smart" mode, which enables fan-stop for two of the three radiator fans. Fan-stop is locked by the device for custom fan profiles, likely to prevent the liquid from overheating.

The preset device profiles are:

  - Silent
  - Balance
  - Game
  - Default
  - Smart

The preset, named modes are supported in the driver and they currently have experimental support in [`yoda.py`](../extra/yoda.py), support in the liquidctl cli is on the way.

## RGB lighting with LEDs

LEDs on the device are always synced with the same effect, so the only supported channel argument is "sync".

Colors can be specified in RGB, HSV or HSL (see [Supported color specification formats](../README.md#supported-color-specification-formats)). Each animation mode supports zero to two colors, and some animation modes include an additional "rainbow" mode.

Lighting effect speed can be controlled with the `--speed` parameter, which can vary between 0 and 3.

```
# liquidctl set sync color clock aa00aa 00aaaa --speed 0
# liquidctl set sync color steady ffb6c1
```

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

Support for the rainbow option is not yet exposed by the liquidctl cli, but it is included in the driver as the color_selection flag.

```
>>> from liquidctl.driver import find_liquidctl_devices
>>> coreliquid_device = next(find_liquidctl_devices())
>>> coreliquid_device.connect()
>>> coreliquid_device.set_colors("sync", "clock", [], color_selection=0)
```

## The D-series LCD screen

_New in git._<br>

On the D-series the display is a **separate USB device** (`0db0:8dbf`) from the
cooler itself (`0db0:edfc`), and so it appears as its own liquidctl device:

```
# liquidctl list
Device #0: MSI MPG Coreliquid D360
Device #1: MSI MPG Coreliquid D-series LCD
```

This is also why the cooler ignores the K360 screen commands documented below;
those apply to the K360 only.

The panel is 320 x 240 px and decodes H.264 MP4 files itself, so media must be
converted before it is uploaded:

```
# ffmpeg -i input.gif -vf scale=320:240 -c:v libx264 -profile:v baseline \
      -pix_fmt yuv420p -movflags +faststart output.mp4
# liquidctl --match lcd set lcd screen video output.mp4
```

Brightness, orientation and a built-in clock face are also supported:

```
# liquidctl --match lcd set lcd screen brightness 60
# liquidctl --match lcd set lcd screen orientation 90
# liquidctl --match lcd set lcd screen clock 0
# liquidctl --match lcd set lcd screen off
```

| mode | action | values |
| --- | --- | --- |
| `brightness` | set the backlight level | 0–100 |
| `orientation` | rotate the panel | 0, 90, 180 or 270 |
| `video` | upload and play a file | path to an H.264 MP4, optionally followed by `;save` |
| `clock` | show a clock face | 0–4 |
| `off` | switch the backlight off | |

Some notes:

- MSI Center must not be running: it holds the display open, and it will also
  push its own configuration over anything set here.
- Uploaded media is not written to the device's storage unless `;save` is
  appended to the path, in which case the panel also remembers the mode and
  shows the file again after the machine loses power:

  ```
  # liquidctl --match lcd set lcd screen video 'output.mp4;save'
  ```
- The panel keeps separate assets for the upright and rotated orientations, and
  falls back to showing the vendor logo if the one it wants is missing.  The
  driver picks the right one for the current orientation, but a file uploaded
  before rotating will not be used afterwards; upload it again.
- Because the panel is physically mounted rotated on some coolers, content may
  need to be pre-rotated to appear upright.

## The K360 LCD screen

The screen resolution is 320 x 240 px, and custom images uploaded with this driver are resized to fit this requirement. The screen orientation and brightness (0-100) can also be controlled. The only channel available for the K360 model is "lcd".

Uploading and choosing which images or banner backgrounds to display is experimentally supported, sometimes an uploaded file may be viewable from a different index on the device than the one it was originally uploaded to.

```
# liquidctl set lcd screen settings '80;0'
# liquidctl set lcd screen hardware 'cpu_temp;cpu_freq;fan_radiator'
```
```
# liquidctl set lcd screen banner '1;4;A cool message in 62 characters!;/home/username/Pictures/pic.jpg'
# liquidctl set lcd screen banner '0;1;Hello, MSI?'
# liquidctl set lcd screen banner '1;4;I can also show a previously uploaded background!'
```

```
# liquidctl set lcd screen disable
```

Maximum length of the displayed banner mesages is 62 ASCII characters. hardware status display functionality is limited, as the displayed data must be communicated to the device. This functionality is implemented in the driver, but currently its usage is limited to [`yoda.py`](../extra/yoda.py), which is gpu-unaware so the gpu_freq and gpu_usage parameters will not display correct information without custom update services.

| mode name | action | options |
| --- | --- | --- |
| hardware | set the screen to display hardware info | up to 3 semicolon delimited keys from the available sensors |
| image | set the screen to display a custom or preset image | \<type (0=preset,1=custom)\>;\<index (0-5)\>[;\<filename\>] |
| banner | set the screen to display a message with custom or preset image as background | \<type (0=preset,1=custom)\>;\<index (0-3)\>;\<message\>[;\<filename\>]
| clock | set the screen to display system time (requires control service to send the time to the device) | integer between 0 and 2 to specify the style of the clock display |
| settings | set the screen brightness and orientation | \<brightness (0-100)\>;\<direction (0-3)\> |
| disable | disables the lcd screen | |

The index field of image and banner modes denotes which of the device-stored images to show on the display, or to which save slot to store an uploaded image in. Use type=0 to display one of the preset animations, and type=1 to upload or display a custom image.

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
