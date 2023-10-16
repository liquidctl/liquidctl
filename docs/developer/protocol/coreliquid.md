# MSI coreliquid AIO protocol

### Compatible devices

| Device Name | USB ID | LED channels | Fan channels |
| ----------- | ------ | ------------ | ------------ |
| MPG Coreliquid K360 | `ODB0:B130` | 1 | 5 |

### Command formats

Most of the communication with the K360 uses 64 byte HID reports. Lighting effect control uses a 185 byte feature report.
Incoming and outgoing reports generally share the same size.
Write commands start with a prefix of `0xD0`, and multi-byte numbers are little-endian, unless stated otherwise.

| Feature report number | Description |
| ---------- | ----------- |
|  0x52 | Get or set board data, notably lighting control  |
| 0xD0 | "get all hardware monitor data" (currently unused) |

It can be noted that the feature report for the board data seems to be designed to include information about all the leds connected to the motherboard.
The driver only needs to set a small subset of the data in order to control the cpu cooler.

## Get General Information

### Get APROM Firmware version -  `0xB0`

Request:

| Byte index | Value |
| ---------- | ----------- |
|  0x00 | 0x01 |
|  0x01 | 0xB0 |
|  Fill | 0xCC |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x02 | X |

Firmware version is `(X >> 4).(X & 0x0F)`

### Get LDROM Firmware version -  `0xB6`

Request:

| Byte index | Value |
| ---------- | ----------- |
|  0x00 | 0x01 |
|  0x01 | 0xB6 |
|  Fill | 0xCC |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x02 | X |

Firmware version is `(X >> 4).(X & 0x0F)`

### Get screen Firmware version -  `0xF1`

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x02 | Version number |

### Get device model index -  `0xB1`

Request:

| Byte index | Value |
| ---------- | ----------- |
|  Fill | 0xCC |

Response:

| Byte index | Description |
| ---------- | ----------- |
| 0x02 | Version number |

## Sending system information for fan control

Fan profiles are **NOT** controlled by any internal device temperature measurement.
Instead, the device expects periodic reports of the CPU temperature, which it uses to interpolate
fan speeds and to show on the screen.

### Set CPU status -  `0x85`

| Byte index | Description |
| ---------- | ----------- |
|  0x01 | 0x85 |
|  0x02-0x03 | cpu frequency (int, MHz) |
|  0x01 | cpu temperature (int, C) |


### Set GPU status -  `0x86`

| Byte index | Description |
| ---------- | ----------- |
|  0x01 | 0x86 |
|  0x02-0x03 | gpu memory frequency (int, MHz) |
|  0x01 | gpu usage (int, %) |


## Lighting effects

### Get all board data (lighting) - Feature report `0x52`

Response:

| Byte index               | Description                                             |
|--------------------------|---------------------------------------------------------|
| 0x1F                     | **Lighting mode**                                       |
| 0x20-0x22                | **RGB values for color1 in JRainbow1 area**             |
| 0x23                     | **Bits 0-1: Speed (LOW, MEDIUM, HIGH)**                 |
| 0x24                     | **Bits 2-6: Brightness level (0-10)**                   |
| 0x24-0x26                | **RGB values for color2 in JRainbow1 area**             |
| 0x27                     | **Bit 7: Color selection (0: Rainbow, 1: User-defined)**|
| 0x29                     | Number of LEDs in JRainbow1 area                        |
| 0x34                     | Number of LEDs in JRainbow2 area                        |
| 0x3D                     | Bit 0: Stripe (0) or Fan (1) selection                  |
| 0x3D                     | Bits 1-3: Fan type (SP, HD, LL)                         |
| 0x3E                     | Bits 2-7: Corsair device quantity (0-63)                |
| 0x3F                     | Number of LEDs in JCorsair area                         |
| 0x48                     | Bit 0: LL120 outer individual mode (0 or 1)             |
| 0x4E                     | Bit 7: Combined JRGB (True or False)                    |
| 0x52                     | Bit 0: Onboard sync (True or False)                     |
| 0x52                     | Bit 1: Combine JRainbow1                                |
| 0x52                     | Bit 2: Combined JRainbow2                               |
| 0x52                     | Bit 3: Combined JCorsair                                |
| 0x52                     | Bit 4: Combined JPipe1                                  |
| 0x52                     | Bit 5: Combined JPipe2                                  |
| 0xB8                     | **Save to device (0 or 1)**                             |

Ligthing effects are sent to the device by sending the feature report `0x52` with the desired data in the above format.

| Byte Value | Lighting Effect Name     |
|------------|---------------------------|
| 0          | DISABLE                   |
| 1          | NO_ANIMATION              |
| 2          | BREATHING                 |
| 3          | FLASHING                  |
| 4          | DOUBLE_FLASHING           |
| 5          | LIGHTNING                 |
| 6          | MSI_MARQUEE               |
| 7          | METEOR                    |
| 8          | WATER_DROP                |
| 9          | MSI_RAINBOW               |
| 10         | POP                       |
| 11         | JAZZ                      |
| 12         | PLAY                      |
| 13         | MOVIE                     |
| 14         | MARQUEE                   |
| 15         | COLOR_RING                |
| 16         | PLANETARY                 |
| 17         | DOUBLE_METEOR             |
| 18         | ENERGY                    |
| 19         | BLINK                     |
| 20         | CLOCK                     |
| 21         | COLOR_PULSE               |
| 22         | COLOR_SHIFT               |
| 23         | COLOR_WAVE                |
| 24         | VISOR                     |
| 25         | RAINBOW                   |
| 26         | RAINBOW_WAVE              |
| 27         | VISOR                     |
| 28         | JRAINBOW                  |
| 29         | RAINBOW_FLASHING          |
| 30         | RAINBOW_DOUBLE_FLASHING   |
| 31         | RANDOM                    |
| 32         | FAN_CONTROL               |
| 33         | DISABLE2                  |
| 34         | COLOR_RING_FLASHING       |
| 35         | COLOR_RING_DOUBLE_FLASHING|
| 36         | STACK                     |
| 37         | CORSAIR_IQUE              |
| 38         | FIRE                      |
| 39         | LAVA                      |
| 40         | END                       |


## Fan control

### Fan temperature config - `0x33` (Get) or `0x41` (Set)

Format:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0xD0 |
| 0x01 | 0x32/0x41 (response/write)|
| 0x02-0x09 | Radiator fan 1 config |
| 0x0A-0x11 | Radiator fan 2 config |
| 0x12-0x19 | Radiator fan 3 config |
| 0x01A-0x21 | Pump speed config |
| 0x22-0x29 | Waterblock fan config |

A fan temperature config consists of 8 bit integer values:
  - Mode index
  - 7 temperature points in Celsius.

### Get fan speed config - `0x32` (Get) or `0x40` (Set)

Format:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0xD0 |
| 0x01 | 0x32/0x40 (response/write) |
| 0x02-0x09 | Radiator fan 1 config |
| 0x0A-0x11 | Radiator fan 2 config |
| 0x12-0x19 | Radiator fan 3 config |
| 0x01A-0x21 | Pump speed config |
| 0x22-0x29 | Waterblock fan config |

A fan config consists of 8 bit integer values:
  - Mode index
  - 7 duty cycle percentage values.

### Get current fan status -  `0x31`

Response:

| Byte index | Description |
| ---------- | ----------- |
|  0x00 | 0xD0 |
| 0x01 | 0x31 |
| 0x02-0x03 | Radiator fan 1 rpm |
| 0x04-0x05 | Radiator fan 2 rpm |
| 0x06-0x07 | Radiator fan 3 rpm |
| 0x08-0x09 | Pump speed rpm |
| 0x0A-0x0B | Waterblock fan rpm |
| 0x16-0x17 | Radiator fan 1 duty % |
| 0x18-0x19 | Radiator fan 2 duty % |
| 0x1A-0x1B | Radiator fan 3 duty % |
| 0x1C-0x1D | Pump speed duty % |
| 0x1E-0x01F | Waterblock fan duty % |

## Display control

### Show Hardware Monitor - `0x71`

The device is capable of displaying a maximum of 3 different parameters, which will cycle on the display.

| Byte index | Description |
| ---------- | ----------- |
|  0x01 | 0x71 |
|  0x02 | Show CPU frequency (0 or 1) |
|  0x03 | Show CPU temperature (0 or 1) |
|  0x04 | Show GPU memory frequency (0 or 1) |
|  0x05 | Show GPU usage (0 or 1) |
|  0x06 | Show pump (0 or 1)|
|  0x07 | Show radiator fan (0 or 1) |
|  0x08 | Show waterblock fan (0 or 1) |
|  0x09 | How many radiator fan speeds to show separately (1 or 3) |

### Set User Message - `0x93`

| Byte index | Description |
| ---------- | ----------- |
|  0x01 | 0x93 |
|  0x02-0x3E | Message bytes (ASCII) |
| 0x3F | 0x20 |

### Set Clock Display - `0x7A`

Sets the clock display style on the OLED screen. `clock_style` determines the visual style of the clock.

| Byte index | Description |
| ---------- | ----------- |
|  0x01 | 0x7A |
|  0x02 | `clock_style` (0, 1 or 2) |

### Set Brightness and Direction - `0x7E`

| Byte index | Description |
| ---------- | ----------- |
|  0x01 | 0x7E |
|  0x02 | brightness (0-100) |
|  0x03 | direction (0-3) |

## Image Upload Commands

### Upload Image - `0xC0` (GIF) or `0xD0` (Banner)

File uploads are initiated by a single report, after which the data is transferred in chunks of 60 bytes. Uploaded images must be 240x320 px size, and in the standard 24-bit color BMP format. A short sleep should be placed between the transfer initiation and start of the data transfer to make sure the device is ready.

**Transfer initiation report**
| Byte index | Description |
| ---------- | ----------- |
|  0x01 | 0xC0/0xD0 (GIF/Banner) |
|  0x02-0x05 | file size to be transferred in bytes (uint32) |
|  0x06 | Slot where the image is saved |

**Bulk transfer report**
| Byte index | Description |
| ---------- | ----------- |
|  0x01 | 0xC1/0xD1 (GIF/Banner) |
|  0x02-0x3D | data chunk |
|  0x3E-0x3F | 0x00 |


### Get Image Checksum - `0xC2` (GIF) or `0xD2` (Banner)

Response:

| Byte index | Description |
| ---------- | ----------- |
|  0x02-0x03 | checksum value |



