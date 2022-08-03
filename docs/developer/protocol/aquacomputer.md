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