
# Lian Li Uni Fan Controller Protocol

_New in git_<br>

## Compatible Devices

| Device Name             | USB ID                   | Fan Channels |
|-------------------------|--------------------------|--------------|
| Lian Li Uni SL          | 0CF2:7750, 0CF2:A100     | 4            |
| Lian Li Uni AL          | 0CF2:A101                | 4            |
| Lian Li Uni SL-Infinity | 0CF2:A102                | 4            |
| Lian Li Uni SL v2       | 0CF2:A103, 0CF2:A105     | 4            |
| Lian Li Uni AL v2       | 0CF2:A104                | 4            |

## Command Formats

### Host to Device
Commands are typically 4 bytes long.

### Device to Host
No specific response for commands.

## Set Commands

### Set Fixed Fan Speed
To set a fixed fan speed for a specific channel.

**Command Structure:**

```
[0xE0, Channel Number, 0x00, Speed Byte]
```

- `0xE0`: Command code for setting fixed speed.
- `Channel Number`: `0x20 + channel_index` (where `channel_index` ranges from 0 to 3 for channels 1 to 4).
- `0x00`: Reserved, always set to `0x00`.
- `Speed Byte`: Calculated based on device type and desired speed percentage (0–100%).

**Example**  
To set the speed of Channel 1 to 80% on an SLV2 device:

- Channel Index: `0` (since Channel 1 corresponds to index 0).
- Channel Number: `0x20 + 0 = 0x20`.
- Calculate Speed Byte using the formula for SLV2 devices (see Speed Byte Calculation).
- Construct Command: `[0xE0, 0x20, 0x00, Speed Byte]`.

### Toggle PWM Synchronization
Enable or disable PWM synchronization (hardware PWM control) for manual speed control on a channel.

**Command Structure:**

```
[Command Prefix] + [Channel Byte]
```

- **Command Prefix**: Device-specific command:

| Device Type     | Command Prefix       |
|-----------------|----------------------|
| SL              | `[0xE0, 0x10, 0x31]` |
| AL              | `[0xE0, 0x10, 0x42]` |
| SLI, SLV2, ALV2 | `[0xE0, 0x10, 0x62]` |

- **Channel Byte**:

  - To disable PWM synchronization (enable manual control): `0x10 << channel_index`
  - To enable PWM synchronization: `0x11 << channel_index`

**Example**  
To disable PWM synchronization on Channel 2 on an SL device:

- Channel Index: `1` (since Channel 2 corresponds to index 1).
- Command Prefix: `[0xE0, 0x10, 0x31]`.
- Channel Byte: `0x10 << 1 = 0x20`.
- Construct Command: `[0xE0, 0x10, 0x31, 0x20]`.

## Speed Calculation

### Speed Byte Calculation
The Speed Byte is calculated differently depending on the device type:

**SL and AL Devices:**

- If speed percentage is 0%:

```
Speed Byte = 0x28 (decimal 40)
```

- If speed percentage is greater than 0%:

```
Speed Byte = floor((800 + (11 × speed_percentage)) / 19)
```

**SLI Devices:**

- If speed percentage is 0%:

```
Speed Byte = 0x0A (decimal 10)
```

- If speed percentage is greater than 0%:

```
Speed Byte = floor((250 + (17.5 × speed_percentage)) / 20)
```

**SLV2 and ALV2 Devices:**

- If speed percentage is 0%:

```
Speed Byte = 0x07 (decimal 7)
```

- If speed percentage is greater than 0%:

```
Speed Byte = floor((200 + (19 × speed_percentage)) / 21)
```

**Example**  
Calculate the Speed Byte for an SLV2 device at 80% speed:

```
Speed Byte = floor((200 + (19 × 80)) / 21)
           = floor((200 + 1520) / 21)
           = floor(1720 / 21)
           = floor(81.90)
           = 81 (0x51 in hexadecimal)
```

## Notes

- Channels are zero-indexed (e.g., Channel 1 corresponds to index 0).
- PWM Synchronization must be disabled on a channel to set a fixed fan speed.
- Initialization: The device disables PWM synchronization on all channels by default upon initialization.
- The device does not provide feedback or responses to commands sent from the host.

## Acknowledgements
Special thanks to EightB1ts for identifying device IDs, PWM commands, and speed byte calculations.
