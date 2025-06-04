# Lian Li GA II LCD AIO Liquid Cooler
_Driver API and source code available in [`liquidctl.driver.ga2_lcd`](../liquidctl/driver/ga2_lcd.py)

## Initialization
[Initialization]: #initialization

The AIO does not need to be initialized. It will set the fan speed to fixed `1320rpm` (about 50%), and the pump to fixed `2580 rpm` (about 70%).

```
# liquidctl initialize
Lian Li GA II LCD
└── Firmware version    N9,01,HS,SQ,CA_II-Vision,V2.01.02E,1.4Oct 22 2024,10:39:15
```

## Device monitoring

The AIO reports fan and pump speed in rpms, and the liquid temperature.

```
# liquidctl status
Lian Li GA II LCD
├── Coolant temperature    34.5  °C
├── Fan speed              1260  rpm
├── Pump speed             2100  rpm
└── Pump duty                58  %
```

## Fan speed control

Both, the fan and the pump appear to only support fixed duty values.

```
# liquidctl set fan speed 50
# liquidctl set pump speed 50
```

## Lighting

The AIO supports two different kinds of lighting: fan lighting and pump lighting.

The fans support following lighting modes:

- meteor
- runway
- breathing
- static
- rainbow-move
- rainbow

The pump supports following lighting modes:

- bounce
- color-morph
- burst
- big-bang
- static-starry-night
- colorful-starry-night
- transmit
- fluctuation
- ticker-tape
- meteor
- runway
- breathing
- static
- rainbow-move
- rainbow

For both types of lightings, the AIO will accept up to four different colors.

It is also possible to specify animation speed (`slowest`, `slower`, `normal`, `faster`, `fastest`) and direction (`down`, `up`, `left`, `right`).

## Screen

Not supported yet.

It appears that the AIO relies on the host to continuously provide an H.264 stream through the HID channel. However, all other features function correctly even without screen configuration.
