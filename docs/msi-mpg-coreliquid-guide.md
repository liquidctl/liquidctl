# MSI MPG Coreliquid AIO coolers
_Driver API and source code available in [`liquidctl.driver.msi`](../liquidctl/driver/msi)._

This driver only supports reporting status. Only the K360 model is supported.

## Initialization

Initialization is not necessary.

## Monitoring

The AIO unit is able to report fan speeds, pump speed, water block "speed", and duties.

```
# liquidctl status
MSI MPG Coreliquid K360
├── Fan 1 speed          1546  rpm
├── Fan 1 duty             60  %
├── Fan 2 speed          1562  rpm
├── Fan 2 duty             60  %
├── Fan 3 speed          1530  rpm
├── Fan 3 duty             60  %
├── Water block speed    2400  rpm
├── Water block duty       50  %
├── Pump speed           2777  rpm
├── Pump duty             100  %
├── Temperature inlet      25  °C
├── Temperature outlet     25  °C
├── Temperature sensor 1   25  °C
└── Temperature sensor 2   25  °C
```
