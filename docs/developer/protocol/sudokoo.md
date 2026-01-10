# Sudokoo SK700V CPU Cooler LCD Display Protocol

The SK700V is a CPU air cooler with an integrated LCD display that shows system
metrics (temperature, load, frequency, power consumption).

All USB packets are 64 bytes long and use HID reports.

## Device Information

- Vendor ID: `0x381c`
- Product ID: `0x0003`
- Connection: USB HID

## Packet Types

### Heartbeat Packet

Sent periodically (every ~1 second) to keep the device responsive.

- Header: `0x10 0x68 0x01 0x09 0x02 0x03 0x01 0x78 0x16`
- Remaining bytes: `0x00` (padding to 64 bytes)

### Data Packet

Sends CPU metrics to be displayed on the LCD.

- Header: `0x10 0x68 0x01 0x09 0x0d 0x01 0x02 0x00`
- Data bytes:
    - Byte 8: Power in Watts (0–255)
    - Byte 9: Power correlated value = `round(power * 10 / 23)`
    - Byte 10: Temperature scale (`0x00` = Celsius, `0x01` = Fahrenheit)
    - Byte 11: Constant `0x42`
    - Byte 12: Encoded temperature (see encoding below)
    - Byte 13–14: Unknown, typically `0x00`
    - Byte 15: CPU load percentage (0–100)
    - Byte 16–17: Frequency in MHz (big-endian)
    - Byte 18: Checksum
    - Byte 19: Constant `0x16`
- Remaining bytes: `0x00` (padding to 64 bytes)

### Screen Off Packet

Same as Data Packet but with byte 6 set to `0x00` instead of `0x02`.

## Temperature Encoding

### Celsius Mode (byte 10 = `0x00`)

```
if temp <= 64:
    encoded = (temp - 32) * 4
else:
    encoded = (temp - 64) * 2 + 128
```

### Fahrenheit Mode (byte 10 = `0x01`)

```
encoded = temp * 2
```

## Frequency Encoding

The display only accepts certain frequency values following the pattern:

```
valid_freq = 480 + n * 510
```

Where `n` is a non-negative integer. Valid values include:
480, 990, 1500, 2010, 2520, 3030, 3540, 4050, 4560, 5070, 5580, 6090 MHz...

Other values should be rounded to the nearest valid frequency.

## Checksum Calculation

The checksum (byte 18) is calculated as:

```
checksum = (b8 + b9 + b10 + b11 + b12 + b13 + b14 + b15 + b16 + b17 + 0x82) & 0xFF
```

Where `b8`–`b17` are the data bytes at positions 8–17.

## Communication Pattern

The typical communication pattern is:

1. Send Heartbeat packet
2. Wait ~50ms
3. Send Data packet with current CPU metrics
4. Wait ~1 second
5. Repeat

## Notes

- The device is write-only; it does not send status information back.
- The display turns on automatically when valid data packets are received.
- To turn off the display, send a Screen Off packet (byte 6 = `0x00`).
- Protocol was reverse-engineered from the Windows MasterCraft software.
