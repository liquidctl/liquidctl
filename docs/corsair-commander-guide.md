# Corsair Commander Pro
_Driver API and source code available in [`liquidctl.driver.commander_pro`](../liquidctl/driver/commander_pro.py)._

This driver will also work for the Corsair Lighting Node Pro Devices.

## Initializing the device

The device should be initialized every time it is powered on, including when
the system resumes from suspending to memory.

The initialization command is needed in order to detect what temperature sensors
and fan types are currently connected.

```
# liquidctl initialize
Corsair Commander Pro (experimental)
├── Firmware version                0.9.212  
├── Bootloader version                  0.5  
├── Temp sensor 1                 Connected  
├── Temp sensor 2                 Connected  
├── Temp sensor 3                 Connected  
├── Temp sensor 4                 Connected  
├── Fan 1 Mode                           DC  
├── Fan 2 Mode                           DC  
├── Fan 3 Mode                           DC  
├── Fan 4 Mode            Auto/Disconnected  
├── Fan 5 Mode            Auto/Disconnected  
└── Fan 6 Mode            Auto/Disconnected  
```

```
# liquidctl initialize
Corsair Lighting Node Pro (experimental)
├── Firmware version                 0.10.4  
└── Bootloader version                  3.0  
```

## Retrieving the fan speeds, temperatures and voltages

The Lighting Node Pro does not have a status message.


The Commander Pro is able to retrieve the current fan speeds as well as
the current temperature of any connected temperature probes. Additionally
the Commander Pro is able to retrieve the voltages from the 3.3, 5, and 12
volt buses.

If a fan or temperature probe is not connected then a value of 0 is shown.

```
# liquidctl status
Corsair Commander Pro (experimental)
├── 12 volt rail     12.06  V
├── 5 volt rail       4.96  V
├── 3.3 volt rail     3.36  V
├── Temp sensor 1     26.4  °C
├── Temp sensor 2     27.5  °C
├── Temp sensor 3     21.7  °C
├── Temp sensor 4     25.3  °C
├── Fan 1 speed        927  rpm
├── Fan 2 speed        927  rpm
├── Fan 3 speed       1195  rpm
├── Fan 4 speed          0  rpm
├── Fan 5 speed          0  rpm
└── Fan 6 speed          0  rpm
```



## Programming the fan speeds

The Lighting Node Pro Does not have any fans to control.


Each fan can be set to either a fixed duty cycle, or a profile consisting of up
to six (temperature, rpm) pairs.  Temperatures should be given in Celsius
and rpm values as a valid rpm for the fan that is connected.
*NOTE: you must ensure that the rpm value is within the min, max range for your hardware.*

Profiles run on the device and are always based one the specified temp probe. If a
temperature probe is not specified number 1 is used. The last point should
set the fan to 100% fan speed, or be omitted; in the latter case the fan will
be set to 5000 rpm at 60°C (this speed may not be appropriate for your device).

```
# liquidctl set fan1 speed 70
                ^^^^       ^^
               channel    duty

# liquidctl set fan2 speed 20 800 40 900 50 1000 60 1500
                           ^^^^^ ^^^^^ ^^^^^^
                   pairs of temperature (°C) -> duty (%)

# liquidctl set fan3 speed 20 800 40 900 50 1300 --temp-probe 2
```

Valid channel values are `fanN`, where 1 <= N <= 6 is the fan number, and
`sync`, to simultaneously configure all fans.

Only fans that have been connected and identified by `liquidctl initialize` can be set.

Behaviour is unspecified if the specified temperature probe is not connected.

_Note: pass `--verbose` to see the raw settings being sent to the cooler._

After normalization of the profile and enforcement of the (60°C, 5000) fail-safe.
This temperature failsafe can be over-ridden by using the `--unsafe=high_temperature` flag.
This will use a maximum temperature of 100 degrees.

## Controlling the LEDs


The devices have 2 lighting channels that can have up to 96 leds connected to each.
LED channels are specified as either `led1` or `led2` with channel 1 being the default.

The table bellow summarizes the available modes, and their associated
maximum number of colors. Note that for any effect if no colors are specified then
random colors will be used.

| Mode          | Num colors |
| ------------- | ---------- |
| `clear` _¹_   |          0 |
| `off` _²_     |          0 |
| `fixed`       |          1 |
| `color_shift` |          2 |
| `color_pulse` |          2 |
| `color_wave`  |          2 |
| `visor`       |          2 |
| `blink`       |          2 |
| `marquee`     |          1 |
| `sequential`  |          1 |
| `rainbow`     |          0 |
| `rainbow2`    |          0 |


_¹: This is not a real mode but it will remove all saved effects_  
_²: This is not a real mode but it is fixed with RGB values of 0_


To specify which LED's on the channel the effect should apply to the
`--start-led` and `--maximum-leds` flags must be given.

If you have 3 Corsair LL fans connected to channel one and you want to set
the first and third to green and the middle to blue you can use the following
commands:

```
# liquidctl set led1 color fixed 00ff00 --start-led 1 --maximum-leds 48
# liquidctl set led1 color fixed 0000ff --start-led 16 --maximum-leds 16
```

This will first set all 48 leds to green then will set leds 16-32 to blue.
Alternatively you could do:

```
# liquidctl set led1 color fixed 00ff00 --start-led 1 --maximum-leds 16
# liquidctl set led1 color fixed 0000ff --start-led 16 --maximum-leds 16
# liquidctl set led1 color fixed 00ff00 --start-led 32 --maximum-leds 16
```


This allows you to compose more complex led effects then just the base modes.
The different commands need to be sent in order that they should be applied.
In the first example if the order were reversed then all of the LED's would
be green.

All of the effects support specifying a `--direction=forward` or `--direction=backward`.  

There are also 3 speeds that can be specified for the `--speed` flag.
`fast`, `medium`, and `slow`.


Each color can be specified using any of the [supported formats](../README.md#supported-color-specification-formats).

Currently the device can only accept hardware effects, and the specified
configuration will persist across power offs. The changes take a couple of
seconds to take effect.
