# ASUS Ryujin II liquid cooler protocol

The data of all usb packets is 65 bytes long, prefixed with `0xEC`.


## Generic Operations

### Get firmware info

- Request:
    - Header: `0xEC 0x82`
- Response:
    - Header: `0xEC 0x02`
    - Data:
        - Byte 4-18: Firmware version (ascii)


## Cooling Operations

### Get cooling info

- Request:
    - Header: `0xEC 0x99`
- Response:
    - Header: `0xEC 0x19`
    - Data:
        - Byte 4: Liquid temperature (integer digits)
        - Byte 5: Liquid temperature (decimal digit)
        - Byte 6-7: Pump rpm (little endian)
        - Byte 8-9: Embedded Micro Fan rpm (little endian)

### Get duties of pump and of embedded micro fan

- Request:
    - Header: `0xEC 0x9A`
- Response:
    - Header: `0xEC 0x1A`
    - Data:
        - Byte 5: Pump duty % from 0x00 to 0x64
        - Byte 6: Embedded Micro Fan duty % from 0x00 to 0x64

### Get fan speed of AIO fan controller

- Request:
    - Header: `0xEC 0xA0`
- Response:
    - Header: `0xEC 0x20`
    - Data:
        - Byte 4-5: Fan 4 rpm (little endian)
        - Byte 6-7: Fan 1 rpm (little endian)
        - Byte 8-9: Fan 2 rpm (little endian)
        - Byte 10-11: Fan 3 rpm (little endian)

### Get duty of AIO fan controller

- Request:
    - Header: `0xEC 0xA1`
- Response:
    - Header: `0xEC 0x21`
    - Data:
        - Byte 5: AIO fan controller duty from 0x00 to 0xFF

### Set duties of pump and of embedded micro fan

- Request:
    - Header: `0xEC 0x1A`
    - Data:
        - Byte 4: Pump duty % from 0x00 to 0x64
        - Byte 5: Embedded Micro Fan duty % from 0x00 to 0x64
- Response:
    - Header: `0xEC 0x1A`

### Set duty of AIO fan controller

- Request:
    - Header: `0xEC 0x21`
    - Data:
        - Byte 5: AIO fan controller duty from 0x00 to 0xFF
- Response:
    - Header: `0xEC 0x21`


## Display Operations

### Switch display mode

- Request:
    - Header: `0xEC 0x51`
    - Data:
        - Byte 2: Display mode
            - `0x00` = off
            - `0x04` = animation (built-in ROG animation)
            - `0x08` = clock
            - `0x10` = single animation
            - `0x20` = framebuffer (static image via bulk EP)
            - `0x21` = hardware monitor
- Response:
    - Header: `0xEC 0x51 0x00`

### Set hardware monitor layout

- Request:
    - Header: `0xEC 0x52`
    - Data:
        - Byte 2: Background style (`0x00` = galactic, `0x01` = cyberpunk, `0x02` = custom)
        - Byte 3: Number of lines (upper nibble)
        - Byte 4: Number of lines (lower nibble)
        - Byte 5: Reserved (`0x00`)
        - Byte 6-9: Background color (R, G, B, alpha)
        - Byte 10-13: Text color line 1 (R, G, B, alpha)
        - Byte 14-17: Text color line 2 (R, G, B, alpha)
        - Byte 18-21: Text color line 3 (R, G, B, alpha)
        - Byte 22-25: Text color line 4 (R, G, B, alpha)
- Response:
    - Header: `0xEC 0x52 0x00`

### Set hardware monitor string

- Request:
    - Header: `0xEC 0x53`
    - Data:
        - Byte 2: Line index (0-based)
        - Byte 3-20: Label string (18 bytes, null-padded UTF-8)
        - Byte 21-32: Value string (12 bytes, null-padded UTF-8)
- Response:
    - Header: `0xEC 0x53 0x00`

### Set display option

- Request:
    - Header: `0xEC 0x5C`
    - Data:
        - Byte 2: Sub-command
            - `0x01` = set config (followed by display_type, mode, orientation, reserved, brightness)
            - `0x10` = reset (wake from standby)
            - `0x20` = standby (screen off for system sleep)
        - For sub-command `0x01`:
            - Byte 3: Display type
            - Byte 4: Mode byte
            - Byte 5: Orientation (0-3 for 0°, 90°, 180°, 270°)
            - Byte 6: Reserved
            - Byte 7: Brightness (0-100 %)
- Response:
    - Header: `0xEC 0x5C 0x00`

### Set clock

- Request:
    - Header: `0xEC 0x11`
    - Data:
        - Byte 2-3: Reserved (`0x00 0x00`)
        - Byte 4: Prefix (`0x08`)
        - Byte 5: Reserved (`0x00`)
        - Byte 6: Hour format (`0x00` = 24h, `0x01` = 12h)
        - Byte 7: Hour (BCD encoded)
        - Byte 8: Minute (BCD encoded)
        - Byte 9: Second (BCD encoded)
        - Byte 10: PM flag (`0x00` = AM/24h, `0x01` = PM)
        - Byte 11: Separator flag (`0x01`)
- Response:
    - Header: `0xEC 0x11 0x00`

### Flush framebuffer

Used after sending a static image via the bulk endpoint.

- Request:
    - Header: `0xEC 0x7F`
    - Data:
        - Byte 2: `0x03`
        - Byte 3-4: Frame size bytes (`0x00 0x84 0x03` = 230400 = 320x240x3)
- Response:
    - Header: `0xEC 0x7F 0x00`

Note: All display commands send ACK responses (`0xEC` + command byte + status).


## Unknown

- Request:
    - Header: `0xEC 0xAF`
- Response:
    - Header: `0xEC 0x2F`
        - Byte 4-17: ?
