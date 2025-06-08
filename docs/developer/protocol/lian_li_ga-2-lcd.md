# Lian Li GA II LCD AIO protocol

The device is controlled by USB HID based custom protocol. In this protocol host submits a PDU to the device, and depending on type of the PDU sent device may return a response. The device never submits a PDU to host on its own.

The first bit in any PDU indicates the type of PDU, either `0x01` or `0x02`. From now on we will call them type `A` and type `B` respectively. The type `A` is used for most operations. The type `B` PDUs only appear to be used to submit H.264 frames for the AIO screen.

All bytes are big endian.

## Type A PDU bytes

```txt
1     :  Fixed 0x01
2     :  Command ID
3     :  Unknown
4-5   :  PDU number
6     :  Payload size
rest  :  Payload
```

## Commands

### Get fimrwamre version

Request: `0x01 0x86`

| Byte         | Value    |
|--------------|----------|
| Type         | 0x01 (A) |
| Command      | 0x86     |

Response: Two part type A PDUS with ASCII encoded payload. The first PDU appears to contain some hardware information and a firmware version. The other PDU appears to contain fimrware build timestamp.

Example response:

- Part 1: `N9,01,HS,SQ,CA_II-Vision,V2.01.02E,1.4`
- Part 2: `Oct 22 2024,10:39:15`

### Handshake

The handshake command is used to check status of the device. It will return RPM nubmers of the fan and the pump, and the coolant temperature.

Request: `0x01 0x81`

| Byte         | Value    |
|--------------|----------|
| Type         | 0x01 (A) |
| Command      | 0x81     |

Response payload:

```txt
1-2  :  Fan RPM
3-4  :  Pump RPM
5    :  Unknown
7    :  Coolant temperature in celsius. Fraction part
```

Example response payload:

```txt
1-2: 0x05 0xa0 - Fan speed (1440 RPM)
3-4: 0x0a 0x64 - Pump speed (2660 RPM)
5  : 0x01
6  : 0x25      - Temperature integer part (37°C)
7  : 0x08      - Temperature fraction part (.8°C)

```

### Set pump speed

Request: `0x01 0x8a`

| Byte         | Value    |
|--------------|----------|
| Type         | 0x01 (A) |
| Command      | 0x8a     |
| Payload size | 0x02     |

Command sets the pump duty cycle. Payload is an integer between 0-100.

No response from device.

### Set fan speed

Request: `0x01 0x8b`

| Byte         | Value    |
|--------------|----------|
| Type         | 0x01 (A) |
| Command      | 0x8b     |
| Payload size | 0x02     |

Command sets the fan duty cycle. Payload is an integer between 0-100.

No response for this type of request.

### Set pump lighting

| Byte         | Value    |
|--------------|----------|
| Type         | 0x01 (A) |
| Command      | 0x83     |
| Payload size | 0x13     |

Payload:

```txt
1      :  Unknown. Set 0x00
2      :  Mode
3      :  Brightness. Set 0x00-0x04
4      :  Speed. Set 0x00-0x04
5-7    :  Color 1 RGB
8-10   :  Color 2 RGB
11-13  :  Color 3 RGB
14-16  :  Color 4 RGB
17     :  Direction. 0x00: Default; 0x02: Down; 0x03: Up
18-19  :  Unknown
```

No response for this type of request.

### Set fan lighting

| Byte         | Value    |
|--------------|----------|
| Type         | 0x01 (A) |
| Command      | 0x84     |
| Payload size | 0x14     |

Payload:

```txt
1      :  Mode
2      :  Brightness. Set 0x00-0x04
3      :  Speed. Set 0x00-0x04
4-6    :  Color 1 RGB
7-9    :  Color 2 RGB
10-12  :  Color 3 RGB
13-15  :  Color 4 RGB
16     :  Direction. 0x00: Default; 0x02: Down; 0x03: Up
18-19  :  Unknown
20     :  Unknown. Set 0x18.
```

No response for this type of request.
<!-- 
## Type B PDU bytes

```txt
1      :  Fixed 0x02
2      :  Command ID
3-6    :  Data size
7-9    :  Part number
10-11  :  Payload size
rest   :  Payload
``` -->
