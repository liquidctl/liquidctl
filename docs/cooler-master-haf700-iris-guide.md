# Cooler Master HAF 700 EVO IRIS LCD
_Driver API and source code available in [`liquidctl.driver.haf700_iris`](../liquidctl/driver/haf700_iris.py)._

_New in git._<br>

The original HAF 700 EVO IRIS (`2516:01c1`) has a 480 × 480 LCD that can display
hardware information, images and video.  liquidctl supports the display on
Linux through the system Android Debug Bridge (`adb`) client.  Fan and RGB
control are not provided by this driver.

## Requirements

Install ADB using your distribution's package manager.  For example:

```console
# Fedora
sudo dnf install android-tools

# Debian or Ubuntu
sudo apt install adb

# Arch Linux
sudo pacman -S android-tools
```

The device must be accessible through ADB:

```console
# adb devices
List of devices attached
1234567890ABCDEF    device
```

The serial number shown above is an example.  Linux users should install the
liquidctl udev rules and reconnect the device if necessary.

## Initialization

Initialize the display to check connectivity and query its capabilities:

```console
# liquidctl --match 'HAF 700 EVO IRIS' initialize
Cooler Master HAF 700 EVO IRIS
├── Native telemetry modes       13
├── LCD width                   480  px
├── LCD height                  480  px
├── Storage block size         4096  B
├── Storage block count       78936
└── Custom media mode            17
```

The storage values are reported by the device and may vary between units.

## Hardware monitoring display

The IRIS provides thirteen built-in pages for hardware information.  Each page
has its own graphics and labels.  To select a page, specify `lcd` as the
channel, `screen` as the operation, a mode and the value to display:

```console
# liquidctl --match 'HAF 700 EVO IRIS' set lcd screen cpu-temperature 42
# liquidctl --match 'HAF 700 EVO IRIS' set lcd screen gpu-usage 75
# liquidctl --match 'HAF 700 EVO IRIS' set lcd screen cpu-fan 1350
```

Supported modes:

| Mode | Value | Default range |
| --- | --- | --- |
| `cpu-frequency` | MHz (displayed in GHz) | 0–9999 |
| `gpu-frequency` | MHz (displayed in GHz) | 0–9999 |
| `cpu-temperature` | °C | 0–100 |
| `gpu-temperature` | °C | 0–100 |
| `cpu-usage` | % | 0–100 |
| `gpu-usage` | % | 0–100 |
| `memory-usage` | % | 0–100 |
| `cpu-fan` | rpm | 0–9999 |
| `case-fan-1` | rpm | 0–9999 |
| `case-fan-2` | rpm | 0–9999 |
| `case-fan-3` | rpm | 0–9999 |
| `case-fan-4` | rpm | 0–9999 |
| `case-fan-5` | rpm | 0–9999 |

The driver accepts aliases such as `cpu-temp`, `gpu-temp`, `ram-usage` and
`case-fan1`.  Numeric values are transmitted as integers; fractional inputs
are rounded.

### Updating a selected page

A long-running application can update the value without reloading the page.
With the default `action=auto`, the driver selects the page on the first call
and updates it on subsequent calls that use the same mode.

A new liquidctl CLI invocation starts a new connection, so commands entered
separately will normally select the page each time.

Programmatic callers can keep the connection open:

```python
dev.set_screen('lcd', 'cpu-temperature', {'value': 42})
dev.set_screen('lcd', 'cpu-temperature', {'value': 43})
dev.set_screen('lcd', 'cpu-temperature', {'value': 44})
```

## Images and video

The display can show PNG and JPEG images or MP4 video:

```console
# liquidctl --match 'HAF 700 EVO IRIS' set lcd screen image ./image.png
# liquidctl --match 'HAF 700 EVO IRIS' set lcd screen image ./photo.jpg
# liquidctl --match 'HAF 700 EVO IRIS' set lcd screen video ./video.mp4
```

The aliases `image`, `media` and `video` all select the same display mode.
The file extension determines the content type.  `.jpeg` is also accepted.

Media files are limited to 16 MiB.  The driver uploads files to a dedicated
32 MiB RAM-backed directory on the panel, avoiding repeated media writes to
its persistent storage.  Files are named using SHA-256 hashes of their contents
to avoid stale images when the same filename is reused.

The RAM storage is cleared when the panel reboots.  liquidctl recreates it and
uploads the selected file again on the next media request.  The media storage
requires the root ADB access available on the supported device.

## Advanced screen options

Additional fields can be supplied using a semicolon-separated value:

```console
# liquidctl --match 'HAF 700 EVO IRIS' set lcd screen cpu-temperature \
  '42;minimum=0;maximum=100;text-color=FFFFFFFF;action=select'
```

The following fields are available for telemetry pages:

| Field | Value | Default |
| --- | --- | --- |
| `value` | Unsigned 16-bit integer | Required |
| `minimum` | Unsigned 16-bit integer | Depends on mode |
| `maximum` | Unsigned 16-bit integer | Depends on mode |
| `scroll` | Unsigned 8-bit integer | 0 |
| `reserved` | Three bytes as hexadecimal | `000000` |
| `round-speed` | Unsigned 8-bit integer | 0 |
| `text-color` | `RRGGBB` or `AARRGGBB` | `FFFFFFFF` |
| `text` | UTF-8, up to 255 encoded bytes | Empty |
| `background-state` | Unsigned 8-bit integer | 0 |
| `background-color` | `RRGGBB` or `AARRGGBB` | `FF000000` |
| `image-name` | UTF-8, up to 255 encoded bytes | Empty |
| `media-name` | UTF-8, up to 255 encoded bytes | Empty |
| `action` | `auto`, `select` or `update` | `auto` |

`action=select` forces the page-selection command, while `action=update` forces
an update of the selected page.  `auto` is recommended for normal use.

JSON is also accepted by the CLI, and Python applications can pass a mapping:

```console
# liquidctl --match 'HAF 700 EVO IRIS' set lcd screen gpu-temperature \
  '{"value":58,"minimum":0,"maximum":100,"action":"auto"}'
```

```python
dev.set_screen('lcd', 'gpu-temperature', {
    'value': 58,
    'minimum': 0,
    'maximum': 100,
})
```

The driver also accepts positional semicolon-separated fields, in the order
listed in the table.  For a persistent connection, unspecified presentation
fields retain the values previously configured for the selected mode.

Programmatic callers can query `Haf700Iris.get_screen_capabilities()` for the
supported modes and fields.  This is a driver-specific extension, not part of
the standard liquidctl API.

## Limitations

- Only the original HAF 700 EVO IRIS with USB ID `2516:01c1` has been tested.
- The driver currently supports Linux and requires the external `adb` client.
- The display must be reachable through ADB.
- Uploaded media needs root ADB access to set up RAM-backed storage.

For command byte layouts and the transport details, see the
[HAF 700 EVO IRIS protocol](developer/protocol/haf700_iris.md).
