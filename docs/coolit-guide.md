# Corsair Hydro H110i GT AIO liquid cooler
_Driver API and source code available in [`liquidctl.driver.coolit`](../liquidctl/driver/coolit.py)._

_New in 1.14.0._<br>

## Initialization
[Initialization]: #initialization

The AIO does not need to be initialized prior to use, but it will set the pump
mode to `quiet`.

```
# liquidctl initialize
Corsair H110i GT
└── Firmware version    2.0.0
```

When (re)initializing the device, it is possible to select the pump mode:

```
# liquidctl initialize --pump-mode extreme
Corsair H110i GT
└── Firmware version      2.0.0
```

Allowed pump modes are:
- `quiet`
- `extreme`

## Device monitoring

Similarly to other AIOs, the cooler can report fan and pump speeds as well as
the liquid temperature.

```
# liquidctl status
Corsair H110i GT
├── Liquid temperature    32.6  °C
├── Fan 1 speed           1130  rpm
├── Fan 2 speed           1130  rpm
└── Pump speed            2831  rpm
```

## Fan speed control

Fan speeds can be configured either to fixed duty values or profiles. The
profiles accept up to seven (liquid temperature, duty) points, and are
interpolated by the device.

```
# liquidctl set fan speed 50
# liquidctl set fan speed 20 0 40 100
```
