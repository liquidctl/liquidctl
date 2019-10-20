# Seasonic/NZXT E-series PSUs

**Support for these devices is still experimental.**

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
Device 0, NZXT E500 (experimental)
Temperature                     45.0  °C
Fan speed                        505  rpm
Firmware version          A017/40983
+12V #1 output voltage         11.89  V
+12V #1 output current          7.75  A
+12V #1 output power           14.48  W
+12V #2 output voltage         11.95  V
+12V #2 output current          0.00  A
+12V #2 output power            0.00  W
+12V #3 output voltage         11.96  V
+12V #3 output current          1.00  A
+12V #3 output power           11.95  W
+5V output voltage              4.90  V
+5V output current              0.02  A
+5V output power                0.11  W
+3.3V output voltage            3.23  V
+3.3V output current            0.01  A
+3.3V output power              0.02  W
```
