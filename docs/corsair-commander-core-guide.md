# Corsair Commander Core, Core XT and ST
_Driver API and source code available in [`liquidctl.driver.commander_core`](../liquidctl/driver/commander_core.py)._

_Changed in 1.11.0: the Corsair Commander Core XT is now supported._<br>
_Changed in 1.12.0: the Corsair Commander ST is now supported._<br>

Currently, functionality implemented is listed here. More is planned to be added.

## Initializing the device

The device should be initialized every time it is powered on.

```
# liquidctl initialize
Corsair Commander Core
├── Firmware version            2.6.201
├── AIO LED count                    29
├── RGB port 1 LED count              8
├── RGB port 2 LED count              8
├── RGB port 3 LED count            N/A
├── RGB port 4 LED count            N/A
├── RGB port 5 LED count            N/A
├── RGB port 6 LED count            N/A
├── AIO port connected              Yes
├── Fan port 1 connected            Yes
├── Fan port 2 connected            Yes
├── Fan port 3 connected             No
├── Fan port 4 connected             No
├── Fan port 5 connected             No
├── Fan port 6 connected             No
├── Water temperature sensor        Yes
└── Temperature sensor 1             No
```

## Retrieving the pump speed, fan speeds, and temperatures

_Changed in git: Core XT temperature labels consistently number external probes from 1._<br>

The Commander Core and ST currently can retrieve the pump speed, fan speeds, temperature of the water, and
the temperature measured by the probe.

```
# liquidctl status
Corsair Commander Core
├── Pump speed           2356  rpm
├── Fan speed 1           810  rpm
├── Fan speed 2           791  rpm
├── Fan speed 3             0  rpm
├── Fan speed 4             0  rpm
├── Fan speed 5             0  rpm
├── Fan speed 6             0  rpm
├── Water temperature    35.8  °C
└── Temperature 1        40.5  °C
```

The Core XT variant of the device is not meant for use with an AIO, so parameters relating to the pump are
not present.

```
Corsair Commander Core XT
├── Fan speed 1    2737  rpm
├── Fan speed 2    2786  rpm
├── Fan speed 3       0  rpm
├── Fan speed 4       0  rpm
├── Fan speed 5       0  rpm
└── Fan speed 6       0  rpm
```


## Programming the pump and fan speeds

### Speed curve profiles

_New in 1.14.0._<br>
_Changed in git: select water or an external probe with `--temperature-sensor`._<br>

The pump or fans speeds can be configured using a speed curve profile with a minimum of 2 or up to 7 curve points.

Each curve point consists of both a temperature (in celsius) and a duty (percentage).


```
liquidctl set fans speed 28 0  35 50  40 75  41 85  42 90  43 95  44 100
              |          |  |
           channel       |  duty
                      temp
```

Use `--temperature-sensor` to select the temperature source for the curve:

| Device | Sensor 0 | Sensor 1 | Sensor 2 |
| --- | --- | --- | --- |
| Commander Core / ST | Water temperature (default) | External probe 1 | Not available |
| Commander Core XT | Not available | External probe 1 (default) | External probe 2 |

For example, to control fan 1 using external probe 1:

```
liquidctl --temperature-sensor 1 set fan1 speed 25 35  30 50  35 75  40 100
```

The selected sensor must be connected; otherwise the command fails before changing
the fan settings. Each channel can use a different sensor, and the device runs the
curve after liquidctl exits. Omitting the option selects water on the Core/ST and
probe 1 on the Core XT. Use `--temperature-sensor 0` to explicitly select water;
the Core XT rejects sensor 0. In `status`, water is labeled `Water temperature`,
and external probes are labeled `Temperature 1`, `Temperature 2`, and so on.


### Fixed duty cycle

_New in 1.9.0._<br>

The pump or fan speeds can be set to a fixed duty cycle.

```
# liquidctl set fan1 speed 70
                ^^^^       ^^
               channel    duty
```


In iCUE the pump can be set to different modes that correspond to a fixed percent that can be used in liquidctl.
Quiet is 75%, Balanced is 85% and Extreme is 100%.

### Device channels

Valid channel values on the Core (non-XT) and ST are `pump`, `fanN`, where 1 <= N <= 6 is the fan number.
On the Core XT, the `pump` channel is not present. The `fans` channel can be used to simultaneously
configure all fans.

### Notes

- A channel may only be configured with a single fixed duty cycle or a single fan curve profile
  (independently from the other channel configurations).
- The pump and some fans have a limit to how slow they can go and will not stop when set to zero.
  This is a hardware limitation that cannot be changed.
- The cooler's lights flash with every update. Due to limitations in both the device hardware and
  liquidctl, there currently is no way to solve this problem. For more information, see: [#448].

[#448]: https://github.com/liquidctl/liquidctl/issues/448
