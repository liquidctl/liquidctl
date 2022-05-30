# liquidctl – liquid cooler control

Cross-platform tool and drivers for liquid coolers and other devices.

Go to the [project homepage] for more information.

```
$ liquidctl list
Device #0: Corsair Vengeance RGB DIMM2
Device #1: Corsair Vengeance RGB DIMM4
Device #2: NZXT Smart Device (V1)
Device #3: NZXT Kraken X (X42, X52, X62 or X72)

# liquidctl initialize all
NZXT Smart Device (V1)
├── Firmware version             1.7  
├── LED accessories                2  
├── LED accessory type    HUE+ Strip  
└── LED count (total)             20  

NZXT Kraken X (X42, X52, X62 or X72)
└── Firmware version    6.2  

# liquidctl status
NZXT Smart Device (V1)
├── Fan 1 speed            1499  rpm
├── Fan 1 voltage         11.91  V
├── Fan 1 current          0.05  A
├── Fan 1 control mode      PWM  
├── Fan 2 [...]
├── Fan 3 [...]
└── Noise level              61  dB

NZXT Kraken X (X42, X52, X62 or X72)
├── Liquid temperature    34.7  °C
├── Fan speed              798  rpm
└── Pump speed            2268  rpm

# liquidctl status --match vengeance --unsafe=smbus,vengeance_rgb
Corsair Vengeance RGB DIMM2
└── Temperature    37.5  °C

Corsair Vengeance RGB DIMM4
└── Temperature    37.8  °C

# liquidctl --match kraken set fan speed  20 30  30 50  34 80  40 90  50 100
# liquidctl --match kraken set pump speed 70
# liquidctl --match kraken set sync color fixed 0080ff
# liquidctl --match "smart device" set led color moving-alternating "hsv(30,98,100)" "hsv(30,98,10)" --speed slower
```

[project homepage]: https://github.com/liquidctl/liquidctl
