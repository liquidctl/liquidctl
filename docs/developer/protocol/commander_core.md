# Corsair Commander Core Protocol

### Compatible devices

| Device Name | USB ID | LED channels | Fan channels | Temperature channels | 
|:-----------:|:------:|:------------:|:------------:|:--------------------:|
| Commander Pro | `1B1C:0C1C` | 7 | 6 | 2 |
**NOTE: The first two LED and temperature channels go to the EXT port and potentially the AIO**

### Command formats

**NOTES:**
 - The commander core works in different modes so ensure the proper mode has been sent for each command
 - Unless stated otherwise all multi-byte numbers used little endian

Host -> Device: 1024 bytes

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | command |
| 0x02 | channel |
| 0x03-... | data |

Device -> Host: 1024 bytes

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | command |
| 0x02 | 0x00 |
| 0x03-... | data |

___
## Global Commands

Global commander should work in any mode.

### `0x01` - Init/Wakeup

Needs to be run every time the device has not been sent any data for a predefined number of seconds.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x01 |
| 0x02 | 0x03 |
| 0x03 | 0x00 |
| 0x04 | 0x02 |

### `0x02` - Get Firmware Version

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x02 |
| 0x02 | 0x13 |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | 0x00 |
| 0x02 | Major |
| 0x03 | Minor |
| 0x04 | Patch |

Note: the `0x01` Init/Wakeup command is exceptionally not necessary before this command.

### `0x05` - Init/Wakeup

Needs to be run before changing the mode on a channel if there is a chance the channel has already been used.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x05 |
| 0x02 | 0x01 |
| 0x03 | channel to reset |

### `0x0d` - Set Channel Mode

Sets the mode for the channel to use  
`0x05` - Init/Wakeup will likely need to be run first.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x0d |
| 0x02 | channel |
| 0x03 | new mode |

___

## Modes:

### `0x17` - Get Speeds of Pump and Fans

#### `0x08` - Get Speeds of Pump and Fans

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x08 |
| 0x02 | channel |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | 0x08 |
| 0x02 | 0x00 |
| 0x03, 0x04 | ???????? |
| 0x05 | Number of speed items |
| 0x06, 0x07 | Speed of AIO/EXT port |
| 0x08, 0x09 | Speed of Fan 1 |
| 0x0a, 0x0b | Speed of Fan 2 |
| 0x0c, 0x0d | Speed of Fan 3 |
| 0x0e, 0x0f | Speed of Fan 4 |
| 0x10, 0x11 | Speed of Fan 5 |
| 0x12, 0x13 | Speed of Fan 6 |

___

### `0x20` - Detect LEDs

#### `0x08` - Get LED Configuration

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x08 |
| 0x02 | channel |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | 0x08 |
| 0x02 | 0x00 |
| 0x03, 0x04 | 0x0f - Number of numbers after this |
| 0x05 | Number of RGB channels |
| 0x06, 0x07 | EXT RGB mode |
| 0x08, 0x09 | EXT LED count |
| 0x0a, 0x0b | RGB Port 1 mode |
| 0x0c, 0x0d | RGB Port 1 LED count |
| 0x0e, 0x0f | RGB Port 2 mode |
| 0x10, 0x11 | RGB Port 2 LED count |
| 0x12, 0x13 | RGB Port 3 mode |
| 0x14, 0x15 | RGB Port 3 LED count |
| 0x16, 0x17 | RGB Port 4 mode |
| 0x18, 0x19 | RGB Port 4 LED count |
| 0x1a, 0x1b | RGB Port 5 mode |
| 0x1c, 0x1d | RGB Port 5 LED count |
| 0x1e, 0x1f | RGB Port 6 mode |
| 0x20, 0x21 | RGB Port 6 LED count |

RGB Mode:

| Fan Mode     | Value |
| ------------ | ----- |
| Connected    | 0x02  |
| Disconnected | 0x03  |

___

### `0x21` - Get Temperatures

#### `0x08` - Get Temperatures

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x08 |
| 0x02 | channel |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | 0x08 |
| 0x02 | 0x00 |
| 0x03, 0x04 | ???????? |
| 0x05 | Number of temperature sensors |
| 0x06 | 0x00 if connected or 0x01 if not connected |
| 0x07, 0x08 | Temperature in Celsius (needs to be divided by 10) |
| 0x09 | 0x00 if connected or 0x01 if not connected |
| 0x0a, 0x0b | Temperature in Celsius (needs to be divided by 10) |

___
