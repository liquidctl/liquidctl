# NZXT E-series PSUs
_Driver API and source code available in [`liquidctl.driver.nzxt_epsu`](../liquidctl/driver/nzxt_epsu.py)._

## Initialization

It is necessary to initialize the device once it has been powered on.

```
# liquidctl initialize
```

_Note: at the moment initialize is a no-op, but this is likely to change once more features are added to the driver._


## Monitoring

The PSU is able to report monitoring data about its own hardware and the output rails.

```
# liquidctl status
NZXT E500
├── Temperature                                    45.0  °C
├── Fan speed                                       505  rpm
├── Firmware version                         A017/40983
├── +12V peripherals output voltage               11.89  V
├── +12V peripherals output current                7.75  A
├── +12V peripherals output power                 14.48  W
├── +12V EPS/ATX12V output voltage                11.95  V
├── +12V EPS/ATX12V output current                 0.00  A
├── +12V EPS/ATX12V output power                   0.00  W
├── +12V motherboard/PCI-e output voltage         11.96  V
├── +12V motherboard/PCI-e output current          1.00  A
├── +12V motherboard/PCI-e output power           11.95  W
├── +5V combined output voltage                    4.90  V
├── +5V combined output current                    0.02  A
├── +5V combined output power                      0.11  W
├── +3.3V combined output voltage                  3.23  V
├── +3.3V combined output current                  0.01  A
└── +3.3V combined output power                    0.02  W
```
