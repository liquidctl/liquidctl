# Cooler Master HAF 700 EVO IRIS protocol

## Compatible devices

| Device | USB ID | Display |
| --- | --- | --- |
| Cooler Master HAF 700 EVO IRIS | `2516:01c1` | 480 × 480 LCD |

The protocol described here is supported by the original HAF 700 EVO IRIS panel
identified as USB `2516:01c1`, revision `0.01`.  The commands and responses
below have been tested with this device.  Other device revisions have not been
verified.

## USB interfaces and transport

The panel contains an Android 4.4.2 system and enumerates as a Full Speed USB
device with two interfaces:

| Interface | Class/subclass/protocol | Endpoints | Function |
| --- | --- | --- | --- |
| 0 | HID `03/00/00` | `0x81` interrupt IN, `0x01` interrupt OUT; 4-byte packets | HID control |
| 1 | `ff/42/01` | `0x82` bulk IN, `0x02` bulk OUT; 64-byte packets | Android Debug Bridge (ADB) |

The display service accepts TCP connections on port 9900.  On Linux, liquidctl
uses the system ADB client to forward this port to the host:

```console
adb -s <serial> forward tcp:0 tcp:9900
```

ADB assigns a local TCP port, which liquidctl uses to communicate with the
panel.  The protocol is transmitted over the forwarded TCP connection without
additional ADB framing.

## Packet format

All documented requests and responses start with a six-byte header.  Multi-byte
integer fields are big-endian unless stated otherwise.

| Byte index | Description |
| --- | --- |
| `0x00` | Command |
| `0x01`–`0x03` | Fixed bytes `80 00 01` |
| `0x04`–`0x05` | Payload length (uint16) |
| `0x06`–... | Payload |

For example, a request with command `0xf0` and no payload is:

```text
f0 80 00 01 00 00
```

## Display commands

### `0x12` - Select LCD mode

Selects a display page and applies its configuration.  The request contains the
[LCD mode payload](#lcd-mode-payload).  The device acknowledges successful
selection with a zero-length response:

```text
12 80 00 01 00 00
```

### `0x15` - Update LCD mode

Updates the value shown on the selected telemetry page without reloading its
presentation.  This command uses the same LCD mode payload as `0x12`, but does
not return a response.

For a persistent connection, liquidctl uses `0x12` when a page is selected and
`0x15` for subsequent value changes to that page.

### LCD mode payload

| Byte index | Size | Description |
| --- | ---: | --- |
| `0x00` | 1 | Mode ID |
| `0x01`–`0x02` | 2 | Current value (uint16) |
| `0x03`–`0x04` | 2 | Minimum (uint16) |
| `0x05`–`0x06` | 2 | Maximum (uint16) |
| `0x07` | 1 | Scroll |
| `0x08`–`0x0a` | 3 | Reserved |
| `0x0b` | 1 | Round speed |
| `0x0c`–`0x0f` | 4 | Text color (AARRGGBB) |
| `0x10` | 1 | Text length `T` |
| `0x11`–... | `T` | UTF-8 text |
| `0x11+T` | 1 | Background state |
| `0x12+T` | 4 | Background color (AARRGGBB) |
| `0x16+T` | 1 | Image-name length `I` |
| `0x17+T` | `I` | UTF-8 image name |
| `0x17+T+I` | 1 | Media-name length `M` |
| `0x18+T+I` | `M` | UTF-8 media name |

The total payload size is `24 + T + I + M` bytes.  String lengths count UTF-8
bytes, not characters.  The driver supports all the fields shown here; the
visible effects of some optional fields have not been established.

### Native telemetry modes

Each mode selects a complete page, including its labels, graphics and numeric
value.  All thirteen telemetry pages have been tested.

| Mode ID | liquidctl mode | Value |
| ---: | --- | --- |
| 1 | `cpu-frequency` | MHz (displayed in GHz) |
| 2 | `gpu-frequency` | MHz (displayed in GHz) |
| 3 | `cpu-temperature` | °C |
| 4 | `gpu-temperature` | °C |
| 5 | `cpu-usage` | % |
| 6 | `gpu-usage` | % |
| 7 | `memory-usage` | % |
| 8 | `cpu-fan` | rpm |
| 9 | `case-fan-1` | rpm |
| 10 | `case-fan-2` | rpm |
| 11 | `case-fan-3` | rpm |
| 12 | `case-fan-4` | rpm |
| 13 | `case-fan-5` | rpm |

Mode 17 displays a media file specified by `media_name`.  PNG and JPEG images
and MP4 video have been tested.  Other display modes are not implemented by
this driver.

### Example: CPU temperature at 42 °C

Request (`0x12`, mode 3, minimum 0, maximum 100):

```text
12 80 00 01 00 18
03 00 2a 00 00 00 64 00
00 00 00 00
ff ff ff ff
00
00
ff 00 00 00
00
00
```

Changing the current value while retaining mode 3 can be done with command
`0x15`.  For example, values 50, 60, 70 and 45 were displayed consecutively
without reselecting the page.

## Storage and file-transfer commands

### `0xf0` - Query storage information

Request:

```text
f0 80 00 01 00 00
```

Response from the tested unit:

```text
f0 80 00 01 00 08 00 00 10 00 00 01 34 58
```

The eight-byte response payload contains two big-endian uint32 values:
`block_size = 4096` and `block_count = 78936`.

### `0xf1` - List files

Returns a `|`-separated listing of the top-level application files directory.
It does not list files within subdirectories.  For example, the dedicated media
subdirectory appears as `liquidctl` rather than a list of its contents.

### `0xf2` - Delete file

The request contains a one-byte state followed by a UTF-8 filename.  State `1`
deletes the named file; the response echoes the request payload.  State `0` can
remove other files and is not used by liquidctl.

### `0xf3` - Check file existence

The request payload is a UTF-8 filename.  The response is a status byte followed
by the same filename:

| Status | Meaning |
| --- | --- |
| `0x00` | File does not exist |
| `0x01` | File exists |

### `0xf5` - Begin file upload

The request payload contains the file size (uint32, big-endian), followed by
the UTF-8 filename.  Successful responses begin with `00 00 00 00` and echo
the filename.  An invalid request returned `ff ff ff ff` as the status.

### `0xf7` - Upload file data

The request payload contains a four-byte prefix followed by a chunk of file
data.  liquidctl sends the chunk offset as a big-endian uint32 in this prefix,
with chunks of up to 16 KiB.  The device responds with:

```text
00 00 00 04
```

Other uses of the four-byte prefix have not been tested.

### `0xf6` - Finish file upload

Completes the transfer and returns an empty response payload.  liquidctl then
uses `0xf3` to check that the uploaded file exists.

## Media storage

Files are addressed by UTF-8 paths relative to the application files directory.
For example, `liquidctl/<hash>.png` corresponds to a file under:

```text
/data/data/com.magic.box/files/liquidctl
```

liquidctl mounts a 32 MiB `tmpfs` at this directory to keep uploaded media in
RAM and limits individual files to 16 MiB.  The remaining application files are
not affected by the mount.

Uploaded files use SHA-256 content-based names.  This also avoids a display
cache issue in which replacing an image at the same pathname can continue to
show the previous image.

The RAM-backed files are lost when Android reboots.  The driver recreates the
mount and uploads the requested file again when necessary.

## Connection recovery

If the TCP connection is lost, the driver reestablishes its ADB port forward and
TCP connection.  After a failed telemetry update, it reselects the previously
selected page with `0x12` before retrying `0x15`.  Reselecting an image after
a transport reset has also been tested.
