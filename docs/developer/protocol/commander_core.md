# Corsair Commander Core Protocol

## Compatible devices

| Device Name | USB ID | LED channels | Fan channels | Temperature channels | 
|:-----------:|:------:|:------------:|:------------:|:--------------------:|
| Commander Core | `1b1c:0c1c` | 7 | 6 | 2 |

The Commander Core is typically shipped with the Corsair iCUE Elite Capellix
AIOs.  The first two LED and temperature channels go to the EXT port, typically
in use by the AIO.

## Command formats

The Commander Core works in different modes, so ensure the proper mode has been
sent for each command.

Unless stated otherwise all multi-byte numbers used little endian.

Host -> Device: 1024 bytes

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | Command |
| 0x02 | Channel |
| 0x03-... | Data |

Device -> Host: 1024 bytes

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | Command |
| 0x02 | 0x00 |
| 0x03-... | Data |

## Global Commands

Global commands should work in any mode.

### `0x01` - Wake up/Sleep

Wakeup needs to be run every time the device has not been sent any data for a
predefined number of seconds.  
Sleep should be run when the device should return to hardware mode and
no more data will be sent.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x01 |
| 0x02 | 0x03 |
| 0x03 | 0x00 |
| 0x04 | 0x01 for sleep or 0x02 for wake up |

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

Note: the `0x01` Init/Wakeup command is exceptionally not necessary before this
command.

### `0x05` - Reset Channel

Needs to be run before changing the mode on a channel if there is a chance the
channel has already been used.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x05 |
| 0x02 | 0x01 |
| 0x03 | Channel to reset |

### `0x0d` - Set Channel Mode

Sets the mode for the channel to use.

`0x05` - Init/Wakeup will likely need to be run first.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x0d |
| 0x02 | Channel |
| 0x03 | New mode |

## Mode Commands

These are the commands that are used in each of the modes.

### `0x06` - Write

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x06 |
| 0x02 | Channel |
| 0x03, 0x04 | Data length  |
| 0x05, 0x06 | 00:00 Unknown |
| 0x07-... | Data |

### `0x08` - Read

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x08 |
| 0x02 | Channel |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | 0x08 |
| 0x02 | 0x00 |
| 0x03, 0x04 | Data type |
| 0x05-... | Data |

## Modes:

### `0x17` - Current Speeds of Pump and Fans

Data Type: `0x06 0x00`

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | Number of speed items |
| 0x01, 0x02 | Speed of AIO/EXT port |
| 0x03, 0x04 | Speed of Fan 1 |
| 0x05, 0x06 | Speed of Fan 2 |
| 0x07, 0x08 | Speed of Fan 3 |
| 0x09, 0x0a | Speed of Fan 4 |
| 0x0b, 0x1c | Speed of Fan 5 |
| 0x0d, 0x1e | Speed of Fan 6 |

### `0x20` - Connected LEDs

Data Type: `0x0f 0x00`

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | Number of RGB channels |
| 0x01, 0x02 | EXT RGB mode |
| 0x03, 0x04 | EXT LED count |
| 0x05, 0x06 | RGB Port 1 mode |
| 0x07, 0x08 | RGB Port 1 LED count |
| 0x09, 0x0a | RGB Port 2 mode |
| 0x0b, 0x0c | RGB Port 2 LED count |
| 0x0d, 0x0e | RGB Port 3 mode |
| 0x0f, 0x10 | RGB Port 3 LED count |
| 0x11, 0x12 | RGB Port 4 mode |
| 0x13, 0x14 | RGB Port 4 LED count |
| 0x15, 0x16 | RGB Port 5 mode |
| 0x17, 0x18 | RGB Port 5 LED count |
| 0x19, 0x1a | RGB Port 6 mode |
| 0x1b, 0x1c | RGB Port 6 LED count |

RGB Mode:

| Fan Mode     | Value |
| ------------ | ----- |
| Connected    | 0x02  |
| Disconnected | 0x03  |

### `0x21` - Get Temperatures

Data Type: `0x10 0x00`

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | Number of temperature sensors |
| 0x01 | 0x00 if connected or 0x01 if not connected |
| 0x02, 0x03 | Temperature in Celsius (needs to be divided by 10) |
| 0x04 | 0x00 if connected or 0x01 if not connected |
| 0x05, 0x06 | Temperature in Celsius (needs to be divided by 10) |
