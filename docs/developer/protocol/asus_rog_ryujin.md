# ASUS ROG RYUJIN II liquid cooler protocol

The data of all usb packets is 65 bytes long and starts with `0xEC`


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

### Get speed

- Request:
    - Header: `0xEC 0x9A`
- Response:
    - Header: `0xEC 0x1A`
    - Data: (same as set speed request but shifted right by 1 byte)
        - Byte 5: Pump duty % from 0x00 to 0x64
        - Byte 6: Embedded Micro Fan duty % from 0x00 to 0x64

### Set speed

- Request:
    - Header: `0xEC 0x1A`
    - Data:
        - Byte 4: Pump duty % from 0x00 to 0x64
        - Byte 5: Embedded Micro Fan duty % from 0x00 to 0x64
- Response:
    - `0xEC 0x1A`

## Unknown

- Request:
    - Header: `0xEC 0xA0`
- Response:
    - Header: `0xEC 0x20`

---
- Request:
    - Header: `0xEC 0xA1`
- Response:
    - Header: `0xEC 0x21`
    - Data:
        - Byte 5: ?

---
- Request:
    - Header: `0xEC 0x21`
    - Data:
        - Byte 5: ?
- Response:
    - Header: `0xEC 0x21`
