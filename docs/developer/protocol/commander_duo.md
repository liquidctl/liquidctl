# Corsair Commander DUO Protocol

## Compatible devices

| Device Name | USB ID | LED channels | Fan channels | Temperature channels |
|:-----------:|:------:|:------------:|:------------:|:--------------------:|
| Commander DUO | `1b1c:0c56` | 2 | 2 | 2 |

The Commander DUO is a compact USB HID fan, temperature, and ARGB
controller.  The device requires SATA power before it enumerates on USB.

This protocol is similar to the Commander Core protocol, but several values and
state transitions differ.  In particular, the Commander DUO may return the
useful response to a read command in any response frame from the close, open,
read, or final close sequence.  Implementations should scan each response for
the expected data type instead of assuming the final close response contains the
payload.

Unless stated otherwise, multi-byte integer values are little endian.

## Firmware notes

The protocol has been tested with firmware versions `0.8.105` and `0.10.112`.
For software fixed-speed fan control, the device must remain in software mode
after the write.  Sending the sleep/hardware-mode command immediately after a
fixed-speed write prevents or cancels the fan response.
For fixed/off Device Memory lighting, the endpoint write must instead be sent
while the device is awake, then followed by sleep/hardware mode; direct hardware
testing showed that the same `65 6d` write can briefly preview the color and
revert if it is sent without first waking the controller.

## Command formats

Host to device reports use 96-byte HID reports on the tested firmware versions.
The following table describes the command body; existing liquidctl HID transport
code sends this body after the OS-level HID report ID.

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x08` |
| `0x01` | Command |
| `0x02` | Channel or subcommand |
| `0x03-...` | Data |

Device to host responses use the following layout.

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x00` |
| `0x01` | Command |
| `0x02` | `0x00` |
| `0x03-...` | Data |

## Global commands

### `0x01` - Wake up / Sleep

The wake command places the device in software mode.  The sleep command returns
the device to hardware mode.

Command:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x08` |
| `0x01` | `0x01` |
| `0x02` | `0x03` |
| `0x03` | `0x00` |
| `0x04` | `0x01` for sleep, `0x02` for wake up |

### `0x02` - Get Firmware Version

Command:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x08` |
| `0x01` | `0x02` |
| `0x02` | `0x13` |

Response:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x00` |
| `0x01` | `0x02` |
| `0x02` | `0x00` |
| `0x03` | Major version |
| `0x04` | Minor version |
| `0x05, 0x06` | Patch version as a little-endian u16 |

For firmware `0.8.105`, the observed response body is:

```text
00 02 00 00 08 69 00
```

This is parsed as major `0x00`, minor `0x08`, and patch `0x0069`.

### `0x05` - Close Endpoint

Command:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x08` |
| `0x01` | `0x05` |
| `0x02` | `0x01` |
| `0x03-...` | Endpoint bytes |

For normal read operations, the endpoint is closed with channel `0x00`.  For
write operations, iCUE and liquidctl close with channel `0x01` followed by the
endpoint bytes.

### `0x0d` - Open Endpoint

Command:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x08` |
| `0x01` | `0x0d` |
| `0x02` | Channel |
| `0x03-...` | Endpoint or mode bytes |

Normal read and color operations use channel `0x00`.  Endpoint write
transactions use channel `0x01`.

## Mode commands

### `0x06` - Write

Command:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x08` |
| `0x01` | `0x06` |
| `0x02` | Channel |
| `0x03, 0x04` | Data length, including the data type bytes |
| `0x05, 0x06` | Reserved, normally `0x00 0x00` |
| `0x07, 0x08` | Data type |
| `0x09-...` | Data |

Channel `0x01` is used for endpoint writes such as fixed-speed fan control.
Channel `0x00` is used for color endpoint writes.

### `0x07` - Write More

Used for continuation data when a write payload does not fit in a single report.
The Commander DUO uses this for large RGB or hardware profile payloads.

Command:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x08` |
| `0x01` | `0x07` |
| `0x02` | Channel |
| `0x03-...` | Continuation data |

### `0x08` - Read Initial / More / Final

The Commander DUO uses the same read command family as the Commander Core for
the normal data modes listed below.

Command:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x08` |
| `0x01` | `0x08` |
| `0x02` | `0x00` |
| `0x03` | `0x01` for initial, `0x02` for more, `0x03` for final |

Matching response frames contain the data type at bytes `0x03, 0x04` and the
payload starting at byte `0x05`.

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x00` |
| `0x01` | `0x08` |
| `0x02` | `0x00` |
| `0x03, 0x04` | Data type |
| `0x05-...` | Payload |

The response carrying the expected data type can appear in the initial, more,
final, or close response.  Implementations should inspect every response in the
full transaction.

### `0x09` - Read Metadata

iCUE uses command `0x09 0x01` when reading the Device Memory and hardware
profile endpoints described below.  The response includes length-like metadata
for the following `0x08 0x01` payload read.  This command has not been needed for
the normal status, fixed-speed, or software RGB paths.

## Modes

### `0x17` - Current Fan Speeds

Data Type: `0x06 0x00`

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | Number of fan ports, normally `0x02` |
| `0x01, 0x02` | Fan 1 speed, RPM |
| `0x03, 0x04` | Fan 2 speed, RPM |

### `0x1a` - Connected Fan Devices

Data Type: `0x09 0x00`

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | Number of fan ports |
| `0x01` | Fan 1 connection state |
| `0x02` | Fan 2 connection state |

Observed Commander DUO fan connection states:

| State | Description |
| ----- | ----------- |
| `0x03` | Connected fan |
| other | Not connected or not confirmed for Commander DUO |

FanControl.CorsairLink also uses a DUO-specific connected state value of
`0x03` for this device.

### `0x18` - Set Fixed Fan Speed

Data Type: `0x07 0x00`

Fixed-speed fan writes use endpoint mode `0x18`, not the Commander Core
hardware fixed-speed mode `0x61`.  The write transaction is:

1. wake the device;
2. close endpoint `0x18` with command `0x05 0x01 0x01 0x18`;
3. open endpoint `0x18` with command `0x0d 0x01`;
4. write command `0x06 0x01` with data type `0x07 0x00`;
5. close endpoint `0x18` with command `0x05 0x01 0x01 0x18`.

Payload format after the `0x06 0x01` command bytes:

| Byte index | Description |
| ---------- | ----------- |
| `0x00, 0x01` | Data length, including the data type bytes |
| `0x02, 0x03` | Reserved, normally `0x00 0x00` |
| `0x04, 0x05` | Data type `0x07 0x00` |
| `0x06` | Number of speed records |
| `0x07` | Fan channel index |
| `0x08` | Speed mode, `0x00` for fixed percentage |
| `0x09` | Fixed speed percentage |
| `0x0a` | Reserved, normally `0x00` |

For example, setting FAN1 to 61% sends the speed data:

```text
01 00 00 3d 00
```

wrapped as:

```text
07 00 00 00 07 00 01 00 00 3d 00
```

iCUE USBPcap captures confirmed the same packet shape for several presets:
58%, 92%, 27%, and 22% were all sent as single fixed-speed records for FAN1.

The fixed-speed command does not take effect if the device is immediately put
back into hardware mode after the write.  The device must remain in software
mode for the software fan speed to apply.

### `0x20` - Connected LEDs

Data Type: `0x0f 0x00`

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | Number of ARGB ports, normally `0x02` |
| `0x01, 0x02` | Port 1 state, `0x0002` when connected |
| `0x03, 0x04` | Port 1 LED count |
| `0x05, 0x06` | Port 2 state, `0x0002` when connected |
| `0x07, 0x08` | Port 2 LED count |

Example payload:

```text
02 02 00 0f 00 02 00 00 00
```

This reports two ports, port 1 connected with 15 LEDs, and port 2 connected with
zero detected LEDs.

### `0x21` - Get Temperatures

Data Type: `0x10 0x00`

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | Number of temperature sensors |
| `0x01` | Sensor 1 connection, `0x00` connected, `0x01` not connected |
| `0x02, 0x03` | Sensor 1 temperature in Celsius × 10 |
| `0x04` | Sensor 2 connection |
| `0x05, 0x06` | Sensor 2 temperature in Celsius × 10 |

For example, temperature bytes `3b 01` are `0x013b`, or `31.5 °C`.

## Lighting control

Commander DUO lighting is handled through a DUO-specific color endpoint.  The
Commander Pro and Lighting Node Pro direct LED commands (`0x33`, `0x34`,
`0x35`, `0x37`, and `0x38`) are not sufficient for this device.

### LED port setup

The DUO color path uses setup commands before color data is written.

| Command bytes | Purpose |
| ------------- | ------- |
| `0x1e ...` | Configure enabled LED ports |
| `0x1d ...` | Configure LED counts per port |
| `0x15 0x01` | Reset LED power / refresh LED detection |

Port enable payload for two ports:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x0d` |
| `0x01` | `0x00` |
| `0x02` | Number of ports, normally `0x02` |
| `0x03` | Port 1 marker, `0x01` |
| `0x04` | Port 1 enabled, `0x01` enabled or `0x00` disabled |
| `0x05` | Port 2 marker, `0x01` |
| `0x06` | Port 2 enabled, `0x01` enabled or `0x00` disabled |

LED count payload for two ports:

| Byte index | Description |
| ---------- | ----------- |
| `0x00` | `0x0c` |
| `0x01` | `0x00` |
| `0x02` | Number of ports, normally `0x02` |
| `0x03, 0x04` | Port 1 LED count |
| `0x05, 0x06` | Port 2 LED count |

If auto-detection reports zero LEDs, software can leave the port disabled or
use an explicit user-supplied LED count.

### `0x22` - Set Color Data

Data Type: `0x12 0x00`

Color data is written after opening the color endpoint with `0x0d 0x00 0x22`.
The first color report uses command `0x06 0x00`; additional color data uses
command `0x07 0x00`.

Captured iCUE color writes for a 15-LED strip use this frame shape:

```text
08 06 00 2f 00 00 00 12 00 <45 bytes of RGB data>
```

This is command `0x06 0x00`, length `0x002f`, reserved `0x0000`, data type
`0x12 0x00`, and 15 RGB triples.  Direction and animation speed changes in the
captured iCUE actions changed the sequence of RGB triples sent over this same
endpoint.

These `0x12 0x00` captures are not sufficient to describe the complete Device
Memory profile format.  A color saved with iCUE Device Memory Mode can persist
after iCUE exits and the device is returned to Linux, so the controller does
have a persistent profile store.  The repeated `0x12 0x00` frames only describe
the observed RGB frame stream while iCUE was controlling or previewing lighting.
On tested firmware, a single static software color frame may later fall back to
the stored Device Memory color when no more color frames are sent.  Re-sending
the same `0x12 0x00` frame periodically kept the software color active in live
testing; a 20 second refresh interval was sufficient in the tested setup.

## Device Memory endpoint observations

iCUE Device Memory operations were observed using additional endpoint modes
ending in `0x6d`.  Their complete semantics are not yet characterized, and
liquidctl only uses the minimal color write described below for fixed/off
Device Memory lighting.  Normal status, software fixed-speed fan control, and
volatile RGB streaming do not use these endpoints.

| Open mode | Data type | Observed purpose |
| --------- | --------- | ---------------- |
| `65 6d` | `7e 20` | Static Device Memory lighting color |
| `65 6d` | `02 a4` | Rainbow Device Memory lighting effect |
| `61 6d` | `03 00` | Hardware cooling/profile mode data |
| `62 6d` | `04 00` | Hardware cooling/profile fixed data |
| `63 6d` | `05 00` | Hardware cooling/profile curve data |

A captured Device Memory off sequence wrote these endpoints and was accepted by
the device, but did not immediately change fan speed or RGB output by itself.
Subsequent normal fixed-speed writes through mode `0x18` still actuated the fan.

The implemented fixed/off Device Memory lighting path writes endpoint `65 6d`
with data type `7e 20`.  The packet captured while iCUE committed fixed color
`112233` was the endpoint transaction below; liquidctl wraps it in
`08 01 03 00 02` before the write and `08 01 03 00 01` after the write.

```text
08 0d 01 65 6d
08 09 01
08 06 01 0e 00 00 00 7e 20 09 00 00 00 01 ff 33 22 11 02 00 01
08 05 01 01
```

The `0x000e` length includes the two data-type bytes, so the data payload is 12
bytes:

```text
09 00 00 00 01 ff bb gg rr 02 00 01
```

The first `ff` appears to be a fixed brightness/value byte.  Focused commit and
readback captures for fixed color `112233` showed the remaining color bytes as
`33 22 11`, so liquidctl maps an input RGB color `(rr, gg, bb)` to
`ff bb gg rr` in this payload.  For `off`, liquidctl writes zero value/color
bytes:

```text
09 00 00 00 01 00 00 00 00 02 00 01
```

This is intentionally narrower than full Device Memory profile management: the
remaining bytes are preserved from the capture, hardware mode uses one global
lighting profile rather than per-port color settings, and direction, speed, and
palette data are not inferred from the available traces.

The implemented rainbow Device Memory lighting path uses the same `65 6d` mode
with data type `02 a4`.  The focused rainbow commit capture wrote:

```text
08 0d 01 65 6d
08 09 01
08 06 01 0a 00 00 00 02 a4 08 04 00 00 00 02 00 01
08 05 01 01
```

The `0x000a` length includes the two data-type bytes, so the data payload is 8
bytes:

```text
08 04 00 00 00 02 00 01
```

The exact meaning of those fields is not yet known; the driver only replays this
observed global rainbow payload for `rainbow --non-volatile`.

Additional Device Memory captures in May 2026 provided these negative/limiting
observations:

* Applying a saved static red profile wrote the same `65 6d` payload shape,
  specifically `09 00 00 00 01 ff 00 00 ff 02 00 01`.  A later focused commit
  and readback for fixed `112233` confirmed the non-symmetric color order as
  `ff bb gg rr`.
* Captures intended to save fixed `aa55cc`, off, global red, direction, speed,
  and two-color palette changes did not contain additional lighting-profile
  endpoint writes.  Those operations were observed as live RGB frames over
  endpoint `0x22` with data type `0x12 0x00`, so they only describe
  preview/software streaming behavior.
  iCUE appears to preview Device Memory lighting changes before committing
  them; the persistent endpoint writes may only be emitted when hardware mode is
  disabled, saved, or otherwise applied.
* Save/apply and after-replug captures wrote `65 6d` followed by `61 6d`,
  `62 6d`, and `63 6d`.  The latter three payloads match hardware cooling
  profile shapes seen on Commander-class devices (`03 00` mode selection,
  `04 00` fixed value, and `05 00` curve data), so liquidctl deliberately does
  not emit them as part of lighting control.
* LED-count changes used endpoints `1e` (`0d 00`) and `1d` (`0c 00`) plus the
  existing LED power reset command.  No evidence currently links those topology
  writes to Device Memory lighting effects or global persistent color data.

iCUE reads these endpoints with the sequence:

```text
08 0d 01 <endpoint bytes>
08 09 01
08 08 01
08 05 01 01 <endpoint bytes>
```

Live reads of endpoint `65 6d 00 00 00` returned a payload containing the bytes
`ff 41 3d` after that color had been stored through iCUE Device Memory Mode.
Changing the current software RGB color did not change that readback, and the
stored color remained visible without iCUE or Windows retaining control of the
USB device.  This is a useful reference for future Device Memory support, but it
is not a current software RGB frame readback.

## Differences from Commander Core

| Aspect | Commander Core | Commander DUO |
| ------ | -------------- | ------------- |
| Product ID | `0x0c1c` | `0x0c56` |
| Fan channels | 6 | 2 |
| LED channels | 7 | 2 |
| Temperature sensors | 2 | 2 |
| Data response | Typically final close response | Matching payload may appear in any response |
| Connected fan state | Core-specific values | `0x03` confirmed for DUO |
| Software fixed fan speed | Not this path | mode `0x18`, dtype `0x07 0x00` |
| Lighting control | Not exposed by liquidctl Core driver | volatile `0x22`; Device Memory `65 6d` |

## Confirmed implementation scope

The implemented liquidctl driver uses the read paths above for fan speeds, fan
connection state, temperature probes, and LED counts.  It implements fixed fan
speed through mode `0x18`, volatile fixed/off RGB through the `0x22` color
endpoint, and fixed/off/rainbow Device Memory lighting writes through endpoint
`65 6d`.  Custom fan profiles, other advanced RGB effects, and broader Device
Memory profile management are not implemented.
