# ASUS Ryujin II liquid cooler protocol

The data of all usb packets is 65 bytes long, prefixed with `0xEC`.


## Ryujin III Extreme LCD

The Ryujin III Extreme (USB ID `0b05:1bcb`) exposes its LCD on a separate bulk
USB interface.  The cooler control interface is HID, while the LCD pixel data
is written to bulk OUT endpoint `0x02`.

The display is 640×480 pixels in packed RGB888 format (921,600 bytes per
frame).  Before a frame upload, perform the following HID operations:

1. Query LCD state: `EC D0`; the reply is headed by `EC 50`.
   - byte 4 is the panel ID;
   - byte 5 is the current display mode;
   - bytes 6–7 are mode arguments.
2. Write raw framebuffer mode `EC 51 20 <reply byte 6> <reply byte 7>`.
   Reapply this command even when the reported mode is already `0x20`, to
   reset display state left by an earlier raw-frame session.
3. Announce the byte length with `EC 7F 03 <u32le length>`.
4. Write the RGB888 frame to bulk endpoint `0x02`.

Frame data is sent in ordinary top-to-bottom, left-to-right RGB888 order.


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
