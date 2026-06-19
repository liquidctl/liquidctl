# Lian Li HydroShift LCD AIO protocol

The HydroShift LCD family is controlled by a USB HID custom protocol that
extends the protocol used by the [GA II LCD][ga2]. Three HID report types are
involved:

- Report `A` (id `0x01`, 64 bytes) — control commands and small responses.
- Report `B` (id `0x02`, 1024 bytes) — bulk transfers used by older firmware
  (< 1.2) for LCD payloads.
- Report `C` (id `0x03`, 512 bytes) — bulk transfers used by firmware ≥ 1.2
  in place of report B. The selection is made from the firmware version
  reported by the `Get firmware` command at initialization.

The host always initiates communication; the device only replies when the
specific command requires it. All multi-byte fields are big endian.

[ga2]: lian_li_ga-2-lcd.md

## Type A PDU

```txt
1     :  Report ID (0x01)
2     :  Command ID
3     :  Reserved (0x00)
4-5   :  PDU sequence number (multi-packet only)
6     :  Payload size (≤ 58 in this packet)
7-64  :  Payload + zero padding
```

A request whose payload exceeds 58 bytes is split across multiple PDUs that
share the command ID and increment the sequence number. The same scheme is
used in reverse for multi-part responses.

## Type B / C PDU

```txt
1     :  Report ID (0x02 for B, 0x03 for C)
2     :  Command ID
3-6   :  Total payload size across all PDUs (u32)
7-9   :  Packet sequence number (u24)
10-11 :  Payload size in this PDU (u16)
12-…  :  Payload data + zero padding
```

For B reports the maximum payload per PDU is 1013 bytes (1024 − 11 header).
For C reports it is 501 bytes (512 − 11 header).

## A-commands

### Get firmware version

Request: `0x01 0x86`

Response: two A-PDUs containing ASCII payloads. The first carries hardware
identifiers and a firmware version; the second carries a build timestamp.
The driver parses the *last* `major.minor` numeric segment of the first
response to choose between report B and report C for LCD transfers.

Example:

- Part 1: `N9,01,HS,SQ,HydroShift,V3.0C.013,1.3`
- Part 2: `Sep 30 2025,11:42:08`

### Handshake

Request: `0x01 0x81`

Returns RPM readings and the coolant temperature. Payload layout:

```txt
1-2  :  Fan RPM
3-4  :  Pump RPM
5    :  Validity flag (non-zero ⇒ temperature fields valid)
6    :  Coolant temperature, integer °C
7    :  Coolant temperature, deci-°C (modulo 10)
```

### Set pump speed

Request: `0x01 0x8a`, payload size `0x02`.

```txt
1   :  Reserved (0x00)
2   :  Duty cycle (0-100)
```

No response.

### Set fan speed

Request: `0x01 0x8b`, payload size `0x02`. Same payload shape as
"Set pump speed". No response.

### Set fan lighting

Request: `0x01 0x85`, payload size `0x14`.

```txt
1      :  Mode (see table below)
2      :  Brightness (0x00-0x04)
3      :  Speed (0x00-0x04)
4-6    :  Color 1 RGB
7-9    :  Color 2 RGB
10-12  :  Color 3 RGB
13-15  :  Color 4 RGB
16     :  Direction (0x00 forward, 0x01 backward)
17     :  Off flag
18     :  Source (0x00 = MCU)
19     :  Sync-to-pump flag
20     :  LED count (e.g. 0x18 for 24 fan LEDs)
```

Modes:

| Mode           | Value | Mode           | Value |
|----------------|-------|----------------|-------|
| `rainbow`      | 0x01  | `tide`         | 0x09  |
| `rainbow-morph`| 0x02  | `mixing`       | 0x0A  |
| `static`       | 0x03  | `ripple`       | 0x0E  |
| `breathing`    | 0x04  | `reflect`      | 0x0F  |
| `runway`       | 0x05  | `tail-chasing` | 0x10  |
| `meteor`       | 0x06  | `paint`        | 0x11  |
| `color-cycle`  | 0x07  | `ping-pong`    | 0x12  |
| `staggered`    | 0x08  |                |       |

No response.

### Set pump lighting

Request: `0x01 0x83`. Payload layout mirrors the fan-lighting frame; not yet
implemented in the driver. Capture pending.

### Reset device

Request: `0x01 0x8e`. Returns the cooler to its power-on default state. No
response.

## B / C-commands (LCD)

### LCD control

Command: `0x0c`. Sent as a single B/C PDU with no chunking — `total_size`
and `pkt_num` are zero, and the payload is exactly 8 bytes:

```txt
1   :  LCD mode
        0  Local UI
        1  Application (host-streamed)
        2  Local H.264
        3  Local AVI
        4  LCD setting
        5  LCD test
2   :  Brightness (0-100)
3   :  Rotation (0=0°, 1=90°, 2=180°, 3=270°) — driver applies rotation
       client-side and leaves this byte at 0
4-7 :  Reserved
8   :  Frame rate (fps)
```

The driver issues `LCD control` with mode 1 before sending any image, and
again on `set lcd screen lcd` to hand control back to the firmware.

### Send JPEG frame

Command: `0x0e`. Streams a JPEG image to the LCD as the payload of one or
more B/C PDUs. The total payload size is the JPEG byte length; PDUs are
emitted with monotonically increasing `pkt_num` until the byte count is met.

The driver encodes 480×480 RGB frames at JPEG quality 85 with 4:2:0 chroma
subsampling. Static images are sent as one JPEG; GIFs and videos send one
JPEG per frame, paced at 24 fps (or the GIF's native interval if longer).

After each JPEG transfer the driver attempts a short non-blocking read on
report A to drain any acknowledgement the device emits.

### LCD available

Command: `0x17`. Used to query LCD readiness; not currently emitted by the
driver but reserved in the command map for completeness.

## Notes and open items

- Pump-head lighting (`0x83`) is documented above by analogy with the fan
  lighting frame and the GA II LCD protocol; needs USB capture to confirm
  byte layout on a HydroShift unit.
- The `LCD setting` and `LCD test` modes (`0x0c` payload byte 1, values 4
  and 5) are observed in firmware strings but their semantics in the
  application protocol are not yet documented.
- The driver applies rotation client-side instead of via byte 3 of the
  `LCD control` payload; firmware-side rotation has not been validated end
  to end.
