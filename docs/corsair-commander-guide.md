# Corsair Commander Pro, Obsidian 1000D and Lighting Node Pro/Core
_Driver API and source code available in [`liquidctl.driver.commander_pro`](../liquidctl/driver/commander_pro.py)._


## Initializing the device

The device should be initialized every time it is powered on, including when
the system resumes from suspending to memory.

The initialization command is needed in order to detect what temperature
sensors and fan types are currently connected.

```
# liquidctl initialize
Corsair Commander Pro
├── Firmware version       0.9.212  
├── Bootloader version         0.5  
├── Temperature probe 1        Yes  
├── Temperature probe 2        Yes  
├── Temperature probe 3         No  
├── Temperature probe 4         No  
├── Fan 1 control mode         PWM  
├── Fan 2 control mode         PWM  
├── Fan 3 control mode          DC  
├── Fan 4 control mode         N/A  
├── Fan 5 control mode         N/A  
└── Fan 6 control mode         N/A  
```

```
# liquidctl initialize
Corsair Lighting Node Pro (experimental)
├── Firmware version       0.10.4  
└── Bootloader version        3.0  
```


## Retrieving the fan speeds, temperatures and voltages

The Lighting Node Pro and Lighting Node Core do not have a status message.

The Commander Pro and Obsidian 1000D are able to retrieve the current fan
speeds as well as the current temperature of any connected temperature probes.
They are also able to retrieve the voltages from the 3.3, 5, and 12 volt buses.

If a fan or temperature probe is not connected then a value of 0 is shown.

```
# liquidctl status
Corsair Commander Pro
├── Temperature 1     26.4  °C
├── Temperature 2     27.5  °C
├── Fan 1 speed        927  rpm
├── Fan 2 speed        927  rpm
├── Fan 3 speed       1195  rpm
├── +12V rail        12.06  V
├── +5V rail          4.96  V
└── +3.3V rail        3.36  V
```


## Programming the fan speeds

The Lighting Node Pro and Lighting Node Core do not have any fans to control.

Each fan can be set to either a fixed duty cycle, or a profile consisting of up
to six (temperature, rpm) pairs.  Temperatures should be given in Celsius and
rpm values as a valid rpm for the fan that is connected.

*NOTE: you must ensure that the rpm value is within the min, max range for your
hardware.*

Profiles run on the device and are always based one the specified temp probe.
If a temperature probe is not specified number 1 is used. The last point should
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

Only fans that have been connected and identified by `liquidctl initialize` can
be set.

Behaviour is unspecified if the specified temperature probe is not connected.

_Note: pass `--verbose` to see the raw settings being sent to the cooler._

After normalization of the profile and enforcement of the (60°C, 5000)
fail-safe.  This temperature failsafe can be over-ridden by using the
`--unsafe=high_temperature` flag.  This will use a maximum temperature of 100
degrees.


## Controlling the LEDs

The Commander Pro and Lighting Node Pro devices have two physical lighting
channels, specified as either `led1` or `led2`.  A third `sync` pseudo channel
is provided for convenience.

On the other hand, the Lighting Node Core has a single `led` channel.

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


_¹ This is not a real mode but it will remove all saved effects_  
_² This is not a real mode but it is fixed with RGB values of 0_

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

All of the effects support specifying a `--direction=forward` or
`--direction=backward`.

There are also 3 speeds that can be specified for the `--speed` flag.
`fast`, `medium`, and `slow`.

Each color can be specified using any of the'
[supported formats](../README.md#supported-color-specification-formats).

Currently the device can only accept hardware effects, and the specified
configuration will persist across power offs. The changes take a couple of
seconds to take effect.
