# Asetek 690LC liquid coolers
_Driver API and source code available in [`liquidctl.driver.asetek`](../liquidctl/driver/asetek.py)._

Several products are available that are based on the same Asetek 690LC base design:

- Current models:
  * EVGA CLC 120 (CLC12), 240, 280 and 360
  * Corsair Hydro H80i v2, H100i v2 and H115i
  * Corsair Hydro H80i GT, H100i GTX and H110i GTX
- Legacy designs:
  * NZXT Kraken X40, X60, X31, X41, X51 and X61

**Note: a custom kernel driver is necessary on Windows (see: [Installing on Windows](../README.md#installing-on-windows)).**

**Note: when dealing with legacy Krakens the `--legacy-690lc` flag should be supplied on all invocations of liquidctl.**

## Initialization

All 690LC devices must be initialized sometime after the system boots.  Only then it will be possible to query the device status and perform other operations.

```
# liquidctl initialize
```

## Device monitoring

Similarly to other AIOs, the cooler can report fan and pump speeds as well as the liquid temperature.

```
# liquidctl status
Asetek 690LC (assuming EVGA CLC)
├── Liquid temperature        28.7  °C
├── Fan speed                  480  rpm
├── Pump speed                1890  rpm
└── Firmware version      2.10.0.0  
```

## Fan and pump speed control

Fan speeds can be configured either to fixed duty values or profiles.  The profiles accept up to six (liquid temperature, duty) points, and are interpolated by the device.

```
# liquidctl set fan speed 50
# liquidctl set fan speed 20 0 40 100
```

*Note: fan speed profiles are only supported on non-legacy models.*

Pump speeds, on the other hand, only accept fixed duty values.

```
# liquidctl set pump speed 75
```

## Lighting modes

There's a single lighting channel `logo`.  The first light mode – 'rainbow' – supports an abstract `--speed` parameter, varying from 1 to 6.

```
# liquidctl set logo color rainbow
# liquidctl set logo color rainbow --speed 1
# liquidctl set logo color rainbow --speed 6
```

*Note: the 'rainbow' lighting mode is currently only supported by EVGA units.*

The 'fading' mode supports specifying the `--time-per-color` in seconds.  The defaults are 1 and 5 seconds per color for, respectively, modern and legacy coolers.

```
# liquidctl set logo color fading ff8000 00ff80
# liquidctl set logo color fading ff8000 00ff80 --time-per-color 2
```

The 'blinking' mode accepts both `--time-per-color` and `--time-off` (also in seconds).  The default is 1 second for each, and whenever unspecified `--time-off` will equal `--time-per-color`.

```
# liquidctl set logo color blinking 8000ff
# liquidctl set logo color blinking 8000ff --time-off 2
# liquidctl set logo color blinking 8000ff --time-per-color 2
# liquidctl set logo color blinking 8000ff --time-per-color 2 --time-off 1
```

The coolers support two more lighting modes: 'fixed' and 'blackout'.  The latter is the only one to completely turn off the LED; however, it also inhibits the visual high-temperature alert.

```
# liquidctl set logo color fixed 00ff00
# liquidctl set logo color blackout
```

It is possible to configure the visual alert for high liquid temperatures:

`--alert-threshold <number>`: set the threshold temperature in Celsius for a visual alert  
`--alert-color <color>`: set the color used by the visual high temperature alert

Note that, regardless of the use of these options, alerts are always enabled (unless suppressed by the 'blackout' mode): the default threshold and color are, respectively, 45°C and red.
