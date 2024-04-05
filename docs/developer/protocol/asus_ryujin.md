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
