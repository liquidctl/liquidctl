# Corsair Vengeance RGB DDR4 UDIMMs

Unbuffered DDR4 modules with a 4 Kbit SPD EEPROM, a temperature sensor and
non-addressable RGB LEDs.  The SPD EEPROM does *not* advertise the presence of
the temperature sensor.

These are I²C devices, connected to the host's SMBus.  Each memory module
module exposes three I²C devices, using a 4-bit Device Type Identifier Code
(DTIC) and a 3-bit Select Address (SA) to generate each I²C Bus Slave Address.

The Select Address is set by the host through the dedicated SA0, SA1 and SA2
pins on the DDR4 288-pin connector, and is shared by all I²C devices on the
module.

Because CorsairLink and iCue acquire kernel locks on the relevant I²C devices,
capturing the traffic from/to those devices with software tools is severely
limited.  Fortunately, connecting a logic analyzer to the SCL and SDA pins of a
memory slot (directly or through the use of some dummy module) is a cheap and
effective alternative.

## Device 0x50 | SA: SPD EEPROM

EE1004-compatible SPD EEPROM.  See [JEDEC 21-C 4.1.6] and
[JEDEC 21-C 4.1.2.L-5].

## Device 0x18 | SA: temperature sensor

Appears to support the same registers and features as in a TSE10004 SPD EEPROM
with temperature sensor, *except for I²C block reads.*  Instead, the registers
should be read as words, with the caveat that the temperature sensor register
values are supposed to be read in big endianess (MSB first, then LSB), but
SMBus Read Word Data assumes the data is returned in little endianess (LSB
first, then MSB).

For the register map, see [JEDEC 21-C 4.1.6].

Note: the SPD EEPROM does not advertise the presence of the temperature sensor.

## Device 0x58 | SA: RGB controller

Register map:

| Register | Size in bytes | Purpose |
| :-- | :-: | :-- |
| `0xa4` | 1 | Timing parameter 1 |
| `0xa5` | 1 | Timing parameter 2 |
| `0xa6` | 1 | Lighting mode |
| `0xa7` | 1 | Number of colors |
| `0xb0–0xc4` | 1 | Red, green and blue components (up to 7 colors) |

Lighting modes:

| Value | Animation |
| :-- | :-- |
| `0x00` | Static or breathing with a *single* color |
| `0x01` | Fading with 2–7 colors |
| `0x02` | Breathing with 2–7 colors |

Timing parameter 1 (TP1): influences the total time in the transition states:
increasing *and* decreasing brightness, or fading through from one color to the
next.  The valid range for animations appears to be from 1 to at least 63, but
a consistent conversion to seconds cannot be inferred; the special value 0
disables the animation.

Timing parameter 2 (TP2): influences the total time in the stable minimum *and*
maximum brightness states.  The valid range appears to be from 0 to at least
63, but a consistent conversion to seconds cannot be inferred.

Note: CorsairLink always sets both T2 and T1 equally.

## References

([JEDEC 21-C 4.1.6]) Definitions of the EE1004-v 4 Kbit Serial Presence Detect
(SPD) EEPROM and TSE2004av 4 Kbit SPD EEPROM with Temperature Sensor (TS) for
Memory Module Applications.

[JEDEC 21-C 4.1.6]: https://www.jedec.org/standards-documents/docs/spd416

([JEDEC 21-C 4.1.2.L-5]) Annex L: Serial Presence Detect (SPD) for DDR4 SDRAM
Modules.

[JEDEC 21-C 4.1.2.L-5]: https://www.jedec.org/standards-documents/docs/spd412l-5

[SMBus captures] in liquidctl/collected-device-data.

[SMBus captures]: https://github.com/liquidctl/collected-device-data/tree/master/Corsair%20Vengeance%20RGB

[OpenRGB wiki entry] for Corsair Vengeance RGB modules.

[OpenRGB wiki entry]: https://gitlab.com/CalcProgrammer1/OpenRGB/-/wikis/Corsair-Vengeance-RGB
