# ASUS ROG RYUJIN II liquid cooler
_Driver API and source code available in [`liquidctl.driver.asus_rog_ryujin`](../liquidctl/driver/asus_rog_ryujin.py)._


## Retrieving the liquid temperature and fan/pump speeds

The cooler reports the liquid temperature, the speed and the set duty of the pump and embedded micro fan.

```
# liquidctl status
ASUS ROG RYUJIN II 360
├── Liquid temperature          31.4  °C
├── Pump speed                  1200  rpm
├── Pump duty                     30  %
├── Embedded Micro Fan speed    1290  rpm
└── Embedded Micro Fan duty       20  %
```
