# Corsair HXi and RMi series PSUs
_Driver API and source code available in [`liquidctl.driver.corsair_hid_psu`](../liquidctl/driver/corsair_hid_psu.py)._

## Initialization

It is necessary to initialize the device once it has been powered on.

```
# liquidctl initialize
```

The +12V rails normally functions in multiple-rail mode, and `initialize` will by default reset the PSU to that behavior.  Single-rail mode can be optionally selected by passing `--single-12v-ocp` to `initialize`.

## Monitoring

The PSU is able to report monitoring data about its own hardware and basic
electrical variables for the input and output sides.

```
# liquidctl status
Corsair RM650i
├── Current uptime                        3:43:54
├── Total uptime                 9 days, 11:43:54
├── Temperature 1                            50.0  °C
├── Temperature 2                            40.8  °C
├── Fan control mode                     Hardware
├── Fan speed                                   0  rpm
├── Input voltage                          230.00  V
├── +12V OCP mode                      Multi rail
├── +12V output voltage                     12.12  V
├── +12V output current                      7.75  A
├── +12V output power                       92.00  W
├── +5V output voltage                       4.97  V
├── +5V output current                       2.88  A
├── +5V output power                        14.00  W
├── +3.3V output voltage                     3.33  V
├── +3.3V output current                     1.56  A
├── +3.3V output power                       5.00  W
├── Total power output                     110.00  W
├── Estimated input power                  124.00  W
└── Estimated efficiency                       89  %
```

Input power and efficiency are estimated from efficiency data advertised by
Corsair in the respective HXi and RMi PSU user manuals.

## Fan speed

The fan speed is normally controlled automatically by the PSU.  It is possible to override this and set the fan to a fixed duty value using the `fan` channel.

```
# liquidctl set fan speed 90
```

This changes the fan control mode to software control and sets the minimum allowed duty value to 30%.  To revert back to hardware control, re-`initialize` the device.

## Appendix: differences in efficiency data

HXi and RMi power supply units do not report input power or current to the
host.  Yet, the efficiency data in the user manuals can sometimes result in
more conservative estimates that the input power and efficiency values iCue and
CorsairLink display.<sup>1</sup>

We believe that this is the result of the use, in those programs, of a
different set of efficiency curves, based on internal and unpublished testing.
Additionally, the manuals also do not match publicly available data submitted
for the 80 Plus certification of these PSUs.<sup>2</sup> Unfortunately, the
latter is only available for 115 V input.

At this point it is important to remember that efficiency, and consequently
power draw, are functions of more than just the total power output.  Thus, the
data in the user manuals is probably significantly less precise than it appears
to be, and we believe the same could be true for the values displayed by iCue
and CorsairLink.

Still, we encourage Corsair to make more of its efficiency data public, which
would hopefully allow liquidctl to present more precise estimates.

_<sup>1</sup> See comments in [issue #300](https://github.com/liquidctl/liquidctl/issues/300)._  
_<sup>2</sup> Available at [80 PLUS® Certified Power Supplies and Manufacturers](https://www.clearesult.com/80plus/manufacturers/115V-Internal)._  
