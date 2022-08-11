# Aquacomputer protocols

Aquacomputer devices share the same HID report philosophy:

* A sensor report with ID `0x01` is sent every second to the host, detailing current sensor readings
* A control/configuration report that can be requested and sent back to the device, controlling its settings and mode of operation. Contains a CRC-16/USB checksum in the last two bytes
* A save report, which is always constant and is sent after a configuration report (the devices seem to work fine without it, but the official software always sends it)

These devices also share some substructures in their reports. All listed values are two bytes long and in big endian, unless noted otherwise.

### Sensor report details & substructures

There's one important substructure that keeps recurring in sensor reports, and it concerns fan info. The definition of fan here also includes pumps, not only 3/4 pin fans in the literal sense. Here's what it's known to contain:

| What               | Where (relative offset) |
| ------------------ | ----------------------- |
| Fan speed (0-100%) | 0x00                    |
| Fan voltage        | 0x02                    |
| Fan current        | 0x04                    |
| Fan power          | 0x06                    |
| Fan speed (RPM)    | 0x08                    |

Temperature sensors, if not connected, will report `0x7FFF` as their value.

## D5 Next pump

The D5 Next pump can, aside from itself, control and monitor an optionally connected fan.

### Sensor report

An example sensor report of the D5 Next looks like this:

```
01 00 03 0B B8 4E 20 00 01 00 00 00 64 03 FB 00 00 00 51 00 00 00 0E A4 00 00 00 45 00 10 42 C4 00 00 00 00 30 C9 00 00 00 A8 9C C2 B9 00 00 01 49 18 87 A1 3C 5C AB 04 BA 01 F8 00 00 00 52 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 00 00 00 00 00 00 00 00 0A 31 7F FF 00 00 7F FF 00 00 00 00 00 00 00 00 00 00 00 00 00 1B DC 04 B9 00 C5 00 EE 0B A8 00 00 00 1B DC 09 AA 08 4C 09 A9 08 4A 00 03 00 06 00 00 00 00 00 00 00 00 00 00 00 00 01 08 E5 00 E7 27 10 27 10 7F 7F
```

Its ID is `0x01` and its length is `0x9e`.

Here is what it's currently known to contain:

| What                               | Where/starts at (offset) |
| ---------------------------------- | ------------------------ |
| Serial number (first part)         | 0x03                     |
| Serial number (second part)        | 0x05                     |
| Firmware version                   | 0xD                      |
| Number of power cycles *[4 bytes]* | 0x18                     |
| Liquid (water) temperature         | 0x57                     |
| Pump info substructure             | 0x74                     |
| Fan info substructure              | 0x67                     |
| +5V voltage                        | 0x39                     |
| +12V voltage                       | 0x37                     |

## Farbwerk 360 RGB controller

The Farbwerk 360 exposes four temperature sensors through its sensor report.

### Sensor report

An example sensor report of the Farbwerk 360 looks like this:

```
01 00 01 41 BB DE 92 03 E8 00 00 00 64 03 FE 00 00 00 11 00 00 00 09 D3 00 00 00 5E 00 08 A4 DD 00 00 00 24 BF E6 C0 34 A2 B4 FF D7 FF D5 FF D6 5A EC 0A 1F 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 FA 01 FB 00 07 00 00 00 03 00 00 00 0B 00 00 00 00 00 15 20 1A 00 00 00 00 00 00 00 00 27 10 27 10 27 10 27 10 27 10 03 E8 00 00 03 E8 00 00 03 E8 00 00 03 E8 00 00 00 00 00 00 00 00 00 00 00 06 00 06 00 05 00 06 01 17 00 06
```

Its ID is `0x01` and its length is `0xb6`. The four temp sensor values are located in succession at `0x32`, `0x34`, `0x36`, `0x38`.

## Octo

The Octo exposes four temperature sensors and eight groups of fan sensor data (outlined in the preamble) through its sensor report.

### Sensor report

An example sensor report of the Octo looks like this:

```
01 00 02 3A 92 C9 EA 03 E8 00 01 00 65 03 FB 00 00 00 01 00 00 00 48 8E 00 00 00 C2 00 3A DF 11 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 04 9D 84 FF DB FF DC FF DD A7 B0 5B FC 10 17 7F FF 7F FF 7F FF 0F 00 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 7F FF 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 04 B9 00 02 00 02 00 00 05 5D 04 B9 00 00 00 00 00 00 00 00 08 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 21 3B 04 B9 00 02 00 02 00 00 00 00 08 00 00 00 00 03 E8 05 5D 00 00 00 00 03 E8 00 00 00 00 00 00 03 E8 00 00 00 00 00 00 03 E8 00 00 00 00 00 00 03 E8 00 00 00 00 00 00 03 E8 00 00 00 00 00 00 03 E8 00 00 00 00 00 00 03 E8 21 3B 00 00 00 00 03 E8 27 10 00 00 00 00 03 E8 27 10 00 00 00 00 00 00 00 00 15 B3 15 0A 27 10 27 10 FF FF
```

Its ID is `0x01` and its length is `0x147`.

Here is what it's currently known to contain:

| What                               | Where/starts at (offset) |
|------------------------------------|--------------------------|
| Serial number (first part)         | 0x03                     |
| Serial number (second part)        | 0x05                     |
| Firmware version                   | 0xD                      |
| Number of power cycles *[4 bytes]* | 0x18                     |
| Temp sensor 1                      | 0x3D                     |
| Temp sensor 2                      | 0x3F                     |
| Temp sensor 3                      | 0x41                     |
| Temp sensor 4                      | 0x43                     |
| Fan 1 substructure                 | 0x7D                     |
| Fan 2 substructure                 | 0x8A                     |
| Fan 3 substructure                 | 0x97                     |
| Fan 4 substructure                 | 0xA4                     |
| Fan 5 substructure                 | 0xB1                     |
| Fan 6 substructure                 | 0xBE                     |
| Fan 7 substructure                 | 0xCB                     |
| Fan 8 substructure                 | 0xD8                     |