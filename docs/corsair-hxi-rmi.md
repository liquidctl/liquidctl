# Corsair HXi and RMi series PSUs

**Support for these devices is still experimental.**

## Initialization

It is necessary to initialize the device it has been powered on.


```
# liquidctl initialize
```


## Monitoring

The PSU is able to report monitoring data about its own hardware and basic electrical variables for the input and output sides.

```
# liquidctl status
Device 0, Corsair RM650i (experimental)
Current uptime                        3:43:54
Total uptime                 9 days, 11:43:54
Temperature 1                            50.0  °C
Temperature 2                            40.8  °C
Fan speed                                   0  rpm
Input voltage                          230.00  V
Total power                            110.00  W
+12V output voltage                     12.12  V
+12V output current                      7.75  A
+12V output power                       92.00  W
+5V output voltage                       4.97  V
+5V output current                       2.88  A
+5V output power                        14.00  W
+3.3V output voltage                     3.33  V
+3.3V output current                     1.56  A
+3.3V output power                       5.00  W
```
