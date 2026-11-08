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


## Unknown

- Request:
    - Header: `0xEC 0xAF`
- Response:
    - Header: `0xEC 0x2F`
        - Byte 4-17: ?


## Screen Operations

Byte numbers below follow the convention of this document (byte 1 is the `0xEC` prefix).
The host reads the sensors and only sends text; the firmware draws the layout, icons and
units.  These offsets were checked on a Ryujin II 360 (firmware `AURJ1-S750-0104`); the
Ryujin III uses a different layout for the same commands.

### Set hardware monitor line

- Request:
    - Header: `0xEC 0x53`
    - Data:
        - Byte 3: Line index, 0 to 3
        - Byte 4-39: Label, ASCII, null padded (the manufacturer software truncates it to 11
          characters)
        - Byte 40-51: Value, UTF-8, null padded, ending with a single unit character:
            - `U+2103` (℃): temperature
            - `U+338F` (㎓): frequency
            - `U+218C`: fan speed (rpm)
            - `U+218A`: voltage
            - `U+218D`: water flow

### Set hardware monitor layout

- Request:
    - Header: `0xEC 0x52`
    - Data:
        - Byte 3: Theme: `0x02` dark, `0x01` light, `0x00` custom
        - Byte 4: Number of lines minus one (0 to 3)
        - Byte 5: Sensor group of the first line
        - Byte 6: Sensor group of the first line (same value as byte 5 in all captures)
            - `0x00`: voltage
            - `0x01`: fan speed
            - `0x02`: temperature
            - `0x03`: frequency
            - `0x04`: water flow
        - Byte 7-9: `0x00`
        - Byte 10-26: `0xFF` with the dark theme; with custom colors, a background RGB
          triplet followed by one text RGB triplet per line, each triplet followed by
          `0xFF`

The manufacturer software sends the lines first and then the layout, and only resends the
layout when the number of lines or the group of the first line changes.  Page rotation is
done on the host by resending lines.

### Set display mode

- Request:
    - Header: `0xEC 0x51`
    - Data:
        - Byte 3: `0x21` for hardware monitor mode
