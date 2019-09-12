# Asetek 690LC liquid coolers from Corsair, EVGA and NZXT

Several products are available that are based on the same Asetek 690LC base design:

 - Current models: EVGA CLC 120 (CLC12), 240, 280 and 360
 - Legacy designs:
    * NZXT Kraken X40, X60, X31, X41, X51 and X61
    * Corsair H80i GTX, H100i GTX, H110i GTX, H80i v2, H100i v2 and H115i

Fan speed profiles and the 'rainbow' lighting mode are currently only supported on the modern EVGA units.

**Additionally, with legacy Krakens it is necessary to pass the `--legacy-690lc` flag on all invocations of liquidctl.**

## Initialization

All of these devices must be initialized at every boot.  Only after that it is possible to query the device status and perform other operations.

```
# liquidctl initialize
```

## Device monitoring

The device can report the fan and pump speed, as well as the liquid temperature.

```
# liquidctl status
Device 0, Asetek 690LC (assuming EVGA CLC)
Liquid temperature          29.3  °C
Fan speed                    480  rpm
Pump speed                  1860  rpm
Firmware version        2.10.0.0
```

## Fan and pump speed control

Fan speeds can be configured either by fixed duty values or (temperature, duty) profiles.  The profiles accept up to six points, and are interpolated by the device.

```
# liquidctl set fan speed 50
# liquidctl set fan speed 20 0 40 100
```

Pump speeds, on the other hand, only accept fixed duty values.

```
# liquidctl set pump speed 75
```

## Lighting modes

There's a single lighting channel; no particular name is enforced yet, but I'll use 'logo' in these examples.  The first light mode – 'rainbow' – supports an abstract `--speed` parameter, varying from 1 to 6.

```
# liquidctl set logo color rainbow
# liquidctl set logo color rainbow --speed 1
# liquidctl set logo color rainbow --speed 6
```

The 'fading' mode supports specifying the `--time-per-color` in seconds (the defaults are 1 and 5 seconds per color, for modern and legacy coolers respectively).

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

It is also possible to configure the visual alert for high liquid temperatures.  For that, the following options are available:

`--alert-threshold <number>`: threshold temperature in Celsius for a visual alert  
`--alert-color <color>`: color used by the visual high temperature alert

Note that, regardless of the use of these options, alerts are always enabled (unless suppressed by the 'blackout' mode): the default threshold and color is, respectively, 45°C and red.
