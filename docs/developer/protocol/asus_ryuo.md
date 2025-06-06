# ASUS ROG Ryuo I 240 liquid cooler protocol

_New in git: added support for the ASUS ROG Ryuo I 240 AIO with fixed fan speed control and firmware version reporting._

The data of all USB packets is 65 bytes long and prefixed with `0xEC`.

## Generic Operations

### Get firmware version

- Request:
    - Header: `0xEC 0x82`
- Response:
    - Header: `0xEC 0x02`
    - Data:
        - Byte 2–18: ASCII-encoded firmware version (null-terminated)

## Cooling Operations

### Set fixed fan speed

- Request:
    - Header: `0xEC 0x2A`
    - Data:
        - Byte 2: Fan duty % from `0x00` to `0x64` (0–100%)
- Response:
    - None

## Notes

- Only the `"fans"`/`"fan"` channel is supported.
- No real-time status or telemetry (e.g. fan RPM, temperature) is available for this device.

