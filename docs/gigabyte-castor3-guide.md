# Gigabyte Aorus Waterforce X II 360

_Driver API and source code available in [`liquidctl.driver.gigabyte_castor3`](../liquidctl/driver/gigabyte_castor3.py)._

_New in git._<br>

## Supported devices

| Device | VID | PID | Controller |
|--------|-----|-----|------------|
| Gigabyte Aorus Waterforce X II 360 | `0x0414` | `0x7a5e` | Castor3 |

This cooler features a 320×320 LCD screen, a pump, a fan header, and an RGB
LED ring, all controlled through a single HID interface.

**Note:** this device is only supported on Linux.

## Initialization
[Initialization]: #initialization

The cooler must be initialized after system boot.  Only then will status queries
and other operations work correctly.  Pump mode can be set during initialization.

```
# liquidctl initialize --pump-mode balanced
Gigabyte Aorus Waterforce X II 360
└── Firmware version    2
```

Supported pump modes: `balanced` (default) and `turbo`.

_New in git._<br>

During initialization, a background sensor push daemon is started automatically.
This daemon feeds CPU temperature, usage, and clock data to the device at ~1
second intervals, keeping Enthusiast display modes live without requiring
additional configuration.

## Device monitoring

The cooler reports CPU temperature and usage (from kernel hwmon and `/proc/stat`),
CPU clock, fan RPM, pump RPM, current fan mode, pump mode, and display mode.

```
# liquidctl status
Gigabyte Aorus Waterforce X II 360
├── CPU temperature        49.0  °C
├── CPU usage                 2  %
├── CPU clock              1746  MHz
├── Fan speed              1917  rpm
├── Pump speed             2675  rpm
├── Fan mode           balanced
├── Pump mode          balanced
└── Display mode          image
```

**Note:** fan RPM readings may be unreliable at low speeds when using a fan hub
(e.g. Noctua NA-FH1) that shares a single tach signal across multiple fans.

**Note:** the AIO does not have a USB-accessible coolant temperature sensor.

## Fan speed control

Fan speed can be set to a fixed duty (0–100%):

```
# liquidctl set fan speed 50
```

Or to a temperature-duty profile (2–5 points):

```
# liquidctl set fan speed 30 30 50 60 70 100
```

Duty percentages are mapped linearly to RPM (0%=0 RPM, 100%=3000 RPM).  The
device uses closed-loop RPM regulation, so the actual fan speed will match the
target regardless of fan model.

## LED ring

The LED ring supports 12 lighting modes.  Use the `led` channel:

```
# liquidctl set led color static ff6600
# liquidctl set led color pulse 00ffff --speed normal
# liquidctl set led color rainbow --speed faster
# liquidctl set led color off 000000
```

### Available modes

| Mode | Colors | Notes |
|------|--------|-------|
| `static` | 1 | Fixed color |
| `pulse` | 1 | Pulsing/breathing |
| `flash` | 1 | Single flash |
| `double-flash` | 1 | Double flash |
| `gradient` | 1 | Gradient sweep |
| `cycle` | 0 | Firmware color cycle |
| `color-shift` | up to 8 | Smooth palette shift |
| `wave` | 0 | Firmware wave |
| `rainbow` | 0 | Firmware rainbow |
| `tri-color` | up to 3 | Three-color cycle |
| `spin` | up to 3 | Spinning palette |
| `switch` | up to 2 | Hard color switch |
| `off` | 1 (black) | LEDs off |

### Speed

`--speed` accepts: `slowest`, `slower`, `normal` (default), `faster`, `fastest`.

### Multi-color palette example

```
# liquidctl set led color color-shift ff0000 ff7200 ffff00 00ff00 00ffff 0000ff ff00ff ff8080
# liquidctl set led color tri-color 0000ff 7d00ff ff00ff
```

## LCD screen modes

The LCD supports 5 Enthusiast display modes, screen rotation, custom image
display with overlays, and a Carousel mode that cycles through display modes.
These features are accessible through the Python API via `set_screen()`.

### Display rotation

Screen rotation (0–330° in 30° increments) is available from the CLI:

```
# liquidctl set lcd screen rotation 90
# liquidctl set lcd screen rotation 0
```

Rotation persists across power cycles.

### Enthusiast modes, image upload, overlays, and other LCD features

The following features are available through the Python API:

- **Enthusiast modes 1–5:** configurable CPU/fan/pump metric displays with
  custom colors
- **Custom image upload:** JPEG/PNG upload with automatic 320×320 resize
- **System info overlay:** CPU metrics overlaid on image display
- **Text overlay:** rendered text with Pango/Cairo (supports arc text, glow,
  shadow, outline)
- **ROM management:** list, free space, and delete files from device storage
- **Carousel mode:** cycle through any combination of display modes
- **Image slot management:** select active images, set display duration

Example using the Python API:

```python
from liquidctl.driver import find_liquidctl_devices

for dev in find_liquidctl_devices(match='Aorus'):
    with dev.connect():
        dev.initialize()

        # Enthusiast 4 — four quadrants
        dev.set_screen('lcd', 'enthusiast4', {
            'q1': 'cpu-temp', 'q2': 'cpu-usage',
            'q3': 'fan', 'q4': 'pump',
            'colors': [(0xff, 0, 0), (0, 0xff, 0), (0, 0, 0xff), (0xff, 0xff, 0)],
        })

        # Upload a custom image
        dev.upload_file('/path/to/image.jpg')

        # Text overlay
        dev.upload_text_overlay('CASTOR3', font_size=40, bold=True,
                                 color=(0x00, 0xff, 0xff))

        # Carousel
        dev.set_screen('lcd', 'carousel', {
            'modes': ['enthusiast1', 'enthusiast4', 'image'],
            'interval': 10,
        })
```

## Automatic startup

To initialize the device on boot, create a systemd service:

```
[Unit]
Description=Initialize Castor3 AIO cooler
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/liquidctl -m "Aorus" initialize --pump-mode balanced
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

The sensor push daemon is started automatically by `initialize()` and does not
require a separate service.

## Known issues and limitations

- **Linux only:** sensor reading depends on `/proc/stat` and hwmon sysfs.
  CPU temperature is detected from `k10temp`/`zenpower` (AMD), `coretemp`
  (Intel), `cpu_thermal` (ARM), or `acpitz` (ACPI fallback).
- **No coolant temperature:** the AIO has no USB-accessible thermistor.
- **Fan RPM jitter:** the Noctua NA-FH1 fan hub shares a single tach signal,
  causing unreliable RPM readings at low speeds.
- **LED get returns stale color:** reading the `ea` register returns the last
  color written, not the active effect color.  This is a firmware limitation.
- **f0 command corrupts ROM:** the `f0` command is not used by this driver.
  Logo toggling must be done through GCC (Gigabyte Control Center).
