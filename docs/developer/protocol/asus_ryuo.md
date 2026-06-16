# ASUS ROG Ryuo I 240 Liquid Cooler Protocol

All USB packets are 65 bytes long, prefixed with `0xEC` (HID report ID).

Vendor ID: `0x0B05` (ASUS), Product ID: `0x1887`.

The protocol was reverse-engineered from ASUS LiveDash v1.05.03
(`AuraIC.dll`, `WriteFileToFW()` function) and confirmed against hardware.

## Generic Operations

### Get firmware version

- Request:
    - Header: `0xEC 0x82`
- Response:
    - Header: `0xEC 0x02`
    - Data:
        - Byte 2–18: firmware version (ASCII, null-terminated)

### Get sensor data

- Request:
    - Header: `0xEC 0xEA`
- Response:
    - Header: `0xEC 0x6A`
    - Data:
        - Byte 3: coolant temperature (°C, unsigned integer)
        - Bytes 4–7: dynamic values (encoding uncertain, possibly pump-related)

## Cooling Operations

### Set fixed fan speed

- Request:
    - Header: `0xEC 0x2A`
    - Data:
        - Byte 2: fan duty % from `0x00` to `0x64` (0–100%)
- Response:
    - None

## LED Operations

### Set LED mode and color

- Request:
    - Header: `0xEC 0x3B`
    - Data:
        - Byte 2: `0x00` (padding)
        - Byte 3: `0x22` (configuration flag)
        - Byte 4: mode (`0x00`=off, `0x01`=static, `0x02`=breathing,
          `0x03`=flash, `0x04`=spectrum, `0x05`=rainbow)
        - Byte 5: red (0–255)
        - Byte 6: green (0–255)
        - Byte 7: blue (0–255)
        - Byte 8: `0x00` (padding)
        - Byte 9: `0x02` (zone count or config)
- Response:
    - None

### Save LED settings

- Request:
    - Header: `0xEC 0x3F`
    - Data:
        - Byte 2: `0x55` (commit flag)
- Response:
    - None

Send immediately after `Set LED mode and color` to persist the setting.

## OLED Display Operations

The pump head contains a 160×128 pixel OLED display.  Images must be in GIF
format.  The upload uses a 9-step chunked transfer protocol.

### OLED upload sequence

Protocol from `AuraIC.dll` → `WriteFileToFW()`:

1. **Init transfer:** `0xEC 0x51 0xA0`
2. **Set file slot:** `0xEC 0x6B 0x01 0x00 N` (N = slot index, typically 1)
3. **Stop animation:** `0xEC 0x6C 0x01`
4. **Force stop animation:** `0xEC 0x6C 0x03`
5. **Prepare for transfer:** `0xEC 0x6C 0x04`
6. **Send data chunks:** For each 62-byte chunk of the GIF file:
   `0xEC 0x6E [byte_count] [data...]` where `byte_count` ≤ 62.
   A 20ms delay between chunks is required — the hardware writes to SPI flash
   and cannot accept data faster.
7. **Transfer complete:** `0xEC 0x6C 0x05`
8. **Finalize / start animation:** `0xEC 0x6C 0xFF`
9. **Commit transfer:** `0xEC 0x51 0x10 0x01 N` (N = slot index)

After the commit, set the slot again and start playback:
- `0xEC 0x6B 0x01 0x00 N`
- `0xEC 0x6E 0x00` (start playback)

### Important warnings

**Do NOT write to register `0x5C` after upload.**  Any write to `0x5C`
(the `SaveAIO` / display mode register) causes the OLED to go permanently
black until a full power cycle of the cooler.  The upload protocol works
correctly without it — the firmware picks up the new GIF from the file slot
automatically.

## Notes

- The device uses HID WriteFile (not SetFeature), 65 bytes per report.
- HID vendor usage page: `0xFF72`, usage: `0xA1`.
- Register reads use command `0x80 + register_number`; the response byte at
  offset 1 is `register_number` (i.e., command minus `0x80`).
- Register writes use the command byte directly with no response.
