# Corsair Commander Core Protocol

## Compatible devices

| Device Name | USB ID | LED channels | Fan channels | Temperature channels | AIO |
|:-----------:|:------:|:------------:|:------------:|:--------------------:|:---:|
| Commander Core | `1b1c:0c1c` | 7 | 6 | 2 | Yes |
| Commander Core XT | `1b1c:0c2a` | 7 | 6 | 2 | No |
| Commander ST | `1b1c:0c32` | 7 | 6 | 2 | No |

The Commander Core is typically shipped with the Corsair iCUE Elite Capellix
AIOs.  The first two LED and temperature channels go to the EXT port, typically
in use by the AIO. Newer releases of these AIOs may instead come with the
Commander ST.

The Commander Core XT is a standalone product that shares the same protocol, but
does not include support for an AIO, and as a result channel numbers are offset down by 1.

## Command formats

The Commander Core works in different modes, so ensure the proper mode has been
sent for each command.

Unless stated otherwise all multi-byte numbers used little endian.

Host -> Device: 96 bytes for firmware v2.x.x | 1024 bytes for firmware v1.x.x

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | Command |
| 0x02 | Channel |
| 0x03-... | Data |

Device -> Host: 96 bytes for firmware v2.x.x | 1024 bytes for firmware v1.x.x

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

### `0x0d` - Open Endpoint

Sets the mode for the channel to use.
Needs to be run **before** a read or write operation.

`0x05` - Init/Wakeup will likely need to be run first.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x0d |
| 0x02 | Channel |
| 0x03 | New mode |

### `0x05` - Close Endpoint

Needs to be run **after** a read or write operation to close a previously opened endpoint.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x05 |
| 0x02 | 0x01 |
| 0x03 | Channel to close |

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
| 0x05, 0x06 | 00:00 Unknown (Before data length starts) |
| 0x07, 0x08 | Data Type (Included in data length) |
| 0x09-... | Data |

### `0x07` - Write More
For writing data that does not fit in a single 96 byte Host->Device packet.

Can be sent multiple times consecutively until data is completely written.

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x07 |
| 0x02 | Channel |
| 0x03-... | Data |

### `0x08` - Read Initial/More/Final

Read More and Read Final are used to read data larger than the 96 byte device->host packet size.

Byte index 0x03 must incremented as each piece of the data is read (i.e. 0x01 first, 0x02 second, and 0x03 third).

Command:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x08 |
| 0x01 | 0x08 |
| 0x02 | 0x00 |
| 0x03 | 0x01 for Read Initial or 0x02 for Read More or 0x03 for Read Final |


Read Initial Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | 0x08 |
| 0x02 | 0x00 |
| 0x03, 0x04 | Data type |
| 0x05-... | Data |


Read More/Final Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x00 | 0x00 |
| 0x01 | 0x08 |
| 0x02 | 0x00 |
| 0x03-... | Data |

## Modes:

### `0x17` - Current Speeds of Pump and Fans

Data Type: `0x06 0x00`

| Byte index | Description (Core) | Description (Core XT) |
| ---------- | ------------------ | --------------------- |
| 0x00 | Number of speed items | Number of speed items |
| 0x01, 0x02 | Speed of AIO/EXT port | Speed of Fan 1 |
| 0x03, 0x04 | Speed of Fan 1 | Speed of Fan 2 |
| 0x05, 0x06 | Speed of Fan 2 | Speed of Fan 3 |
| 0x07, 0x08 | Speed of Fan 3 | Speed of Fan 4 |
| 0x09, 0x0a | Speed of Fan 4 | Speed of Fan 5 |
| 0x0b, 0x0c | Speed of Fan 5 | Speed of Fan 6 |
| 0x0d, 0x0e | Speed of Fan 6 | |

### `0x1a` - Connected Speed Devices

Data Type: `0x09 0x00`

Connection State: 0x07 if connected or 0x01 if not connected

| Byte index | Description (Core) | Description (Core XT) |
| ---------- | ------------------ | --------------------- |
| 0x00 | Number of Ports | Number of Ports |
| 0x01 | AIO/EXT Connection State | Fan 1 Connection State |
| 0x02 | Fan 1 Connection State | Fan 2 Connection State |
| 0x03 | Fan 2 Connection State | Fan 3 Connection State |
| 0x04 | Fan 3 Connection State | Fan 4 Connection State |
| 0x05 | Fan 4 Connection State | Fan 5 Connection State |
| 0x06 | Fan 5 Connection State | Fan 6 Connection State |
| 0x07 | Fan 6 Connection State | |


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
| 0x02, 0x03 | Temperature in Celsius with 10ths decimal (3b:01 = 315 = 31.5C) |
| 0x04 | 0x00 if connected or 0x01 if not connected |
| 0x05, 0x06 | Temperature in Celsius with 10ths decimal (3b:01 = 315 = 31.5C) |

### `0x60 0x6d` - Hardware Speed Device Mode

Data Type: `0x03 0x00`

| Byte index | Description (Core) | Description (Core XT) |
| ---------- | ------------------ | --------------------- |
| 0x00 | Number of Ports | Number of Ports |
| 0x01 | AIO/EXT Speed Mode | Fan 1 Speed Mode |
| 0x02 | Fan 1 Speed Mode | Fan 2 Speed Mode |
| 0x03 | Fan 2 Speed Mode | Fan 3 Speed Mode |
| 0x04 | Fan 3 Speed Mode | Fan 4 Speed Mode |
| 0x05 | Fan 4 Speed Mode | Fan 5 Speed Mode |
| 0x06 | Fan 5 Speed Mode | Fan 6 Speed Mode |
| 0x07 | Fan 6 Speed Mode | |

Speed Modes:

| Mode | Description |
| ---- | ----------- |
| 0x00 | Fixed percentage |
| 0x02 | Fan percentage fan curve |

Note: This list is not complete and currently only contains what has been confirmed so far

### `0x61 0x6d` - Hardware Fixed Speed (Percentage)

Data Type: `0x04 0x00`

| Byte index | Description (Core) | Description (Core XT) |
| ---------- | ------------------ | --------------------- |
| 0x00 | Number of Ports | Number of Ports |
| 0x01, 0x02 | Speed as percentage for AIO/EXT port | Speed as percentage for Fan 1 |
| 0x03, 0x04 | Speed as percentage for Fan 1 | Speed as percentage for Fan 2 |
| 0x05, 0x06 | Speed as percentage for Fan 2 | Speed as percentage for Fan 3 |
| 0x07, 0x08 | Speed as percentage for Fan 3 | Speed as percentage for Fan 4 |
| 0x09, 0x0a | Speed as percentage for Fan 4 | Speed as percentage for Fan 5 |
| 0x0b, 0x0c | Speed as percentage for Fan 5 | Speed as percentage for Fan 6 |
| 0x0d, 0x0e | Speed as percentage for Fan 6 | |

### `0x62 0x6d` - Hardware Speed Curve (Percentage)

Data Type: `0x05 0x00`

| Byte index | Description (Core) |
| ---------- | ----------- |
| 0x00 | Number of Ports |
| 0x01-0x1e | Speed Curve for AIO/EXT |
| 0x1f-0x3c | Speed Curve for Fan 1 |
| 0x3d-0x5a | Speed Curve for Fan 2 |
| 0x5b-0x78 | Speed Curve for Fan 3 |
| 0x79-0x96 | Speed Curve for Fan 4 |
| 0x97-0xb4 | Speed Curve for Fan 5 |
| 0xb5-0xd2 | Speed Curve for Fan 6 |

Speed Curve:

| Byte index | Description (Core) |
| ---------- | ----------- |
| 0x00 | Temperature sensor to use 0x00 for water 0x01 for plugged in sensor |
| 0x01 | Number of speed curve points |
| 0x02-0x05 | Speed curve point 1 |
| 0x06-0x09 | Speed curve point 2 |
| 0x0a-0x0d | Speed curve point 3 |
| 0x0e-0x11 | Speed curve point 4 |
| 0x12-0x15 | Speed curve point 5 |
| 0x16-0x19 | Speed curve point 6 |
| 0x1a-0x1d | Speed curve point 7 |

Speed Point:

| Byte index | Description (Core) |
| ---------- | ----------- |
| 0x00, 0x01 | Temperature in Celsius with 10ths decimal (3b:01 = 315 = 31.5C) |
| 0x02, 0x03 | Point speed (%) |
