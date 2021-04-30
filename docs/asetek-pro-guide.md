# Asetek Pro liquid coolers
_Driver API and source code available in [`liquidctl.driver.asetek_pro`](../liquidctl/driver/asetek_pro.py)._

These coolers are more commonly known as the Corsair Hydro Pro family (not to
be confused with the Platinum or Pro XT families):

- Corsair Hydro H100i Pro
- Corsair Hydro H115i Pro
- Corsair Hydro H150i Pro

**Note: a custom kernel driver is necessary on Windows (see: [Installing on
Windows](../README.md#installing-on-windows)).**

## Initialization

The coolers must be initialized sometime after the system boots.  Only then it
will be possible to query the device status and perform other operations.

```
# liquidctl initialize
```

When (re)initializing the device it is possible to select the pump mode:

```
# liquidctl initialize --pump-mode=performance
```

Allowed pump modes are: `quiet`, `balanced` and `performance`.

## Device monitoring

Similarly to other AIOs, the cooler can report fan and pump speeds as well as
the liquid temperature.

```
# liquidctl status
Corsair Hydro H100i Pro (experimental)
├── Liquid temperature        28.7  °C
├── Fan 1 speed                480  rpm
├── Fan 2 speed                476  rpm
├── Pump mode             balanced  
├── Pump speed                1890  rpm
└── Firmware version      2.10.0.0  
```

## Fan speed control

Fan speeds can be configured either to fixed duty values or profiles.  The
profiles accept up to seven (liquid temperature, duty) points, and are
interpolated by the device.

```
# liquidctl set fan speed 50
# liquidctl set fan speed 20 0 40 100
```

## Lighting modes

There's a single lighting channel `logo`.  The following table sumarizes the
available lighting modes, and the number of colors that each of them expects.

| Mode | Colors | Notes |
| :-- | :--: | :-- |
| `alert` | 3 | Good, warning and critical states |
| `shift` | 2–4 ||
| `pulse` | 1–4 ||
| `blinking` | 1–4 ||
| `fixed` | 1 ||

```
# liquidctl set logo color alert 00ff00 ffff00 ff0000
# liquidctl set logo color shift ff9000 0090ff
# liquidctl set logo color pulse ff9000
# liquidctl set logo color blinking ff9000
# liquidctl set logo color fixed ff9000
```

All modes except `alert` and `fixed` support an additional `--speed` parameter;
the allowed values are `slower`, `normal` and `faster`.

```
# liquidctl set logo color pulse ff9000 --speed faster
```
