# Coolit Protocol

## Compatible devices

| Device Name | USB ID | LED channels | Fan channels | Temperature channels | AIO |
|:-----------:|:------:|:------------:|:------------:|:--------------------:|:---:|
| Corsair Hydro H110i GT | `1b1c:0c04` | 0 | 2 + pump | 1 (internal) | Yes |

This device also features a pump channel, controlled with the appropriate command (see below).

## Command format

Unless stated otherwise all multi-byte numbers used little endian.

The device expect packets in the following order/format:

1. Request ID byte (usually a counter that rolls over)
2. Opcode byte
3. Command byte
4. Optional arguments

See the `_build_data_package` function for data package construction.

Multiple "data packages" can be merged into a single command, i.e. one single TX to the device. To do so,
simply create a list with data packages, and send the list altogether with `_send_commands`. See `get_status`
for a usage example.

## Opcodes

The device can be read or written to, in 1/2/3 byte(s).

|Opcode|Description|Name in driver|
|-|-|-|
|0x06|Write 1 byte|`_OP_CODE_WRITE_ONE_BYTE`|
|0x08|Write 2 byte|`_OP_CODE_WRITE_TWO_BYTES`|
|0x0A|Write 3 byte|`_OP_CODE_WRITE_THREE_BYTES`|
|0x07|Read 1 byte|`_OP_CODE_READ_ONE_BYTE`|
|0x09|Read 2 byte|`_OP_CODE_READ_TWO_BYTES`|
|0x0B|Read 3 byte|`_OP_CODE_READ_THREE_BYTES`|

## Modes and speeds

Fan modes:
- Fixed duty = 0x02
- Fixed RPM = 0x04
- Custom curve = 0x0E

Pump modes:
- Quiet = 0x2E
- Extreme = 0x0C

Pump speeds:
- Quiet = 0x2E09
- Extreme = 0x860B

## Commands

|Command|Name in driver|Description|Opcode to use|Arguments|
|-|-|-|-|-|
|0x01|`_COMMAND_FIRMWARE_ID`|Get firmware ID|`_OP_CODE_READ_TWO_BYTES`|n/a|
|0x0E|`_COMMAND_TEMP_READ`|Read temperature|`_OP_CODE_READ_TWO_BYTES`|n/a|
|0x10|`_COMMAND_FAN_SELECT`|Select fan channel|`_OP_CODE_WRITE_ONE_BYTE`|0x0 to 0x2 (fan1/fan2/pump)|
|0x12|`_COMMAND_FAN_MODE`|Set fan mode|`_OP_CODE_WRITE_ONE_BYTE`|See fan/pump modes|
|0x13|`_COMMAND_FAN_FIXED_PWM`|Set fan channel duty|`_OP_CODE_WRITE_ONE_BYTE`|duty as RPM|
|0x14|`_COMMAND_FAN_FIXED_RPM`|Set fan channel RPM|`_OP_CODE_WRITE_TWO_BYTES`|pump speed|
|0x16|`_COMMAND_FAN_READ_RPM`|Get fan channel RPM|`_OP_CODE_READ_TWO_BYTES`|n/a|
|0x17|`_COMMAND_FAN_MAX_RPM`|Get max fan channel RPM|`_OP_CODE_READ_TWO_BYTES`|n/a|
|0x19|`_COMMAND_FAN_RPM_TABLE`|Set fan channel RPM curve|`_OP_CODE_WRITE_THREE_BYTES`|duty encoded as RPM|
|0x1A|`_COMMAND_FAN_TEMP_TABLE`|Set fan channel temperature curve|`_OP_CODE_WRITE_THREE_BYTES`|temperature data|

## Custom curves

Fan curves are written in the following order:

1. Fan select
2. Fan mode set
3. Fan RPM curve set
4. Fan temperature curve set

Temperature is encoded as (0x00, temperature) pairs.

RPM is encoded as (A, B) pairs, where:

- A = rpm % 255
- B = rpm - (rpm % 255) >> 8
- rpm = duty * max_rpm / 100

`max_rpm` is read from the device for each channel.