# Monster/AIC AIO LCD control protocol

The protocol documented here was independently reconstructed from observed
USB traffic and validated on one Monster Tulpar TD3 AIO system.  It covers the
minimum control path required to wake the LCD, keep it awake, change
brightness, and rotate the image.  Firmware revisions may differ.

## Transport

The tested controller is a HID device with identifiers `1d6b:0130`.  Writes
use report ID `0x00`; the encoded control frame follows the report ID.

On the tested Linux system the HID interface is enumerated by the
libusb-backed hidapi module but not by the hidraw backend.  The driver therefore
uses a device-specific libusb-hidapi discovery fallback.

The identifiers alone may not be globally unique.  Systems exposing multiple
matching HID interfaces must identify the correct interface before sending
commands.

## Inner message

Commands use an HTTP-like UTF-8 message with CRLF line endings.  An empty line
between the headers and body is mandatory, including for commands without a
body.

```text
POST power 1\r\n
SeqNumber=3\r\n
Date=1700000000000\r\n
ContentType=json\r\n
ContentLength=18\r\n
\r\n
{"event":"resume"}
```

`SeqNumber` is a monotonically increasing signed 31-bit counter.  `Date` is
Unix time in milliseconds.  JSON is compact, without insignificant spaces.

## Control frame

The complete frame is:

```text
[0x5a][escaped(uint16be(payload_length + 5) + payload + checksum)][0x5a]
```

The checksum covers the two length bytes and the payload:

```text
sum(uint16be(payload_length + 5) + payload) & 0xff
```

Bytes inside the delimiters are escaped as follows:

| Input | Encoded |
| :-- | :-- |
| `0x5a` | `0x5b 0x01` |
| `0x5b` | `0x5b 0x02` |

For example, the complete frame for the payload `abc` is:

```text
5a 00 08 61 62 63 2e 5a
```

## Initialization

The observed startup synchronization is:

1. `POST conn` without a body.
2. `POST power` with `{}`.
3. `STATE all` without a body.
4. `POST power` with `{"event":"resume"}`.

A short delay between these messages is used by the reference application.

## Keep-alive

While the host is awake, the observed application repeats these messages
approximately once per second:

1. `POST power` with `{"event":"resume"}`.
2. `STATE all` without a body.

The tested hardware turns the screen off after this traffic stops.  Some
firmware revisions act on requests without returning a reply that can be
correlated through `AckNumber`, so missing application-level acknowledgements
are not treated as write failures.

## Brightness

The user-facing range of 0–100 is mapped to the observed firmware range of
10–100 with JavaScript-compatible rounding:

```text
firmware_value = round((percentage * 0.9) + 10)
```

The resulting request is:

```text
POST brightness 1
{"value":firmware_value}
```

## Orientation

The four supported right-angle orientations use:

```text
POST rotate 1
{"degree":0|90|180|270}
```

## Media transfer

Captured media traffic contains separate `0x5c`-prefixed TLV/block records.
Those records are not the outer framing for the control requests above.  Media
upload is intentionally not implemented until its block format, transfer
ordering, and timing can be validated independently.

Additional reverse-engineering notes and the standalone Linux implementation
are available in the
[monster-td3-aio-lcd-linux](https://github.com/orcunulutas/monster-td3-aio-lcd-linux)
repository.
