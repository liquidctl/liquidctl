# Corsair Commander Pro and Lighting Node Pro protocol

### Compatible devices

| Device Name | USB ID | LED channels | Fan channels |
| ----------- | ------ | ------------ | ------------ |
| Commander Pro | `1B1C:0C10` | 2 | 6 |
| Lighting Node Pro | `1B1C:0C0B` | 2 | 0 |

### Command formats

Host -> Device: 16 bytes
Device -> Host: 64 bytes

## Get Information commands

### Get Firmware version -  `0x02`

Response:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x00 |
| 0x01 | X |
| 0x02 | Y |
| 0x03 | Z |

Firmware version is `X.Y.Z`

### Get Bootloader version -  `0x06`

Response:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x00 |
| 0x01 | X |
| 0x02 | Y |

Bootloader version is `X.Y`

### Get temperature sensor configuration -  `0x10`

Response:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x00 |
| 0x01 | `0x01` temp sensor 1 connected, otherwise `0x00` |
| 0x02 | `0x01` temp sensor 2 connected, otherwise `0x00` |
| 0x03 | `0x01` temp sensor 3 connected, otherwise `0x00` |
| 0x04 | `0x01` temp sensor 4 connected, otherwise `0x00` |


### Get temperature value -  `0x11`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x11 |
|  0x01 | temp sensor number (0x00 - 0x03) |

Response:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x00 |
| 0x01 | temp MSB |
| 0x02 | temp LSB |

Divide the temperature value by 100 to get the value is degrees celsius.

### Get bus voltage value -  `0x12`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x12 |
|  0x01 | rail number (0x00 - 0x02) |

rail 0 = 12v
rail 1 = 5v
rail 2 = 3.3v

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | voltage MSB |
| 0x02 | voltage LSB |

Divide the value by 1000 to get the actual voltage.

### Get fan configuration -  `0x20`

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | Fan 1 mode |
| 0x02 | Fan 2 mode |
| 0x03 | Fan 3 mode |
| 0x04 | Fan 4 mode |
| 0x05 | Fan 5 mode |
| 0x06 | Fan 6 mode |

Fan modes:

| Fan Mode     | Value |
| ------------ | ----- |
| Disconnected | 0x00  |
| DC (3 pin)   | 0x01  |
| PWM (4 pin)  | 0x02  |


### Get fan RPM value -  `0x21`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x21 |
|  0x01 | fan number (0x00 - 0x05) |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | rpm MSB |
| 0x02 | rpm LSB |


## Set commands

### Set fixed % - `0x23`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x23 |
|  0x01 | fan number (0x00 - 0x05) |
|  0x02 | percentage |

### Set fan curve % - `0x25`

Request:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x25 |
| 0x01 | fan number (0x00 - 0x05) |
| 0x02 | temp sensor to use (0x00 - 0x03) 0xFF to use external sensor |
| 0x03, 0x04 | temp point 1 MSB |
| 0x05, 0x06 | temp point 2 MSB |
| 0x07, 0x08 | temp point 3 MSB |
| 0x09, 0x0A | temp point 4 MSB |
| 0x0B, 0x0C | temp point 5 MSB |
| 0x0D, 0x0E | temp point 6 MSB |
| 0x0F, 0x10 | rpm point 1 MSB  |
| 0x11, 0x12 | rpm point 2 MSB  |
| 0x13, 0x14 | rpm point 3 MSB  |
| 0x15, 0x16 | rpm point 4 MSB  |
| 0x17, 0x18 | rpm point 5 MSB  |
| 0x19, 0x1A | rpm point 6 MSB  |

### Hardware LED commands

- Send reset channel
- send start LED effect
- set channel to hardware mode
- send effect (one or more messages)
- send commit


### Reset channel  - `0x37`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x37 |
|  0x01 | channel number (0x00 or 0x01) |


### Start channel LED effect  - `0x34`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x34 |
|  0x01 | channel number (0x00 or 0x01) |

### Set channel state - `0x38`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x38 |
|  0x01 | channel number (0x00 or 0x01) |
|  0x02 | 0x01 hardware control, 0x02 software control |


### Set LED effect - `0x35`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x35 |
|  0x01 | channel number (0x00 or 0x01) |
|  0x02 | start LED number |
|  0x03 | number of LEDs |
|  0x04 | mode |
|  0x05 | speed |
|  0x06 | direction |
|  0x07 | random colors |
|  0x08 | 0xFF |


| mode | value | Num Colors |
| ---- | ----- | --------- |
| rainbow     | `0x00` | 0 |
| color_shift | `0x01` | 2 |
| color_pulse | `0x02` | 2 |
| color_wave  | `0x03` | 2 |
| fixed       | `0x04` | 1 |
| visor       | `0x06` | 2 |
| marquee     | `0x07` | 1 |
| blink       | `0x08` | 2 |
| sequential  | `0x09` | 1 |
| rainbow2    | `0x0A` | 0 |

| speed | value |
| ----- | ----- |
| slow | `0x02` |
| medium | `0x01` |
| fast | `0x00` |


| direction | value |
| ----- | ----- |
| forward | `0x01` |
| backward | `0x00` |


### Commit hardware settings  - `0x33`

Request:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0x33 |
|  0x01 | 0xFF |
