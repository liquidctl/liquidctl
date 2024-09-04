# Corsair HXi and RMi series PSUs
_Driver API and source code available in [`liquidctl.driver.corsair_hid_psu`](../liquidctl/driver/corsair_hid_psu.py)._

_Changed in 1.12.0: HX1500i and HX1000i 2022 re-issue are now also supported._<br>

## Initialization

It is necessary to initialize the device once it has been powered on.

```
# liquidctl initialize
```

The +12V rails normally functions in multiple-rail mode, and `initialize` will
by default reset the PSU to that behavior.  Single-rail mode can be optionally
selected by passing `--single-12v-ocp` to `initialize`.

_Changed in 1.9.0: changing the OCP mode or resetting to hardware fan control
is not available when the device was initialized by the [Linux hwmon] driver._<br>

## Monitoring

_Changed in 1.9.0: OCP and fan control modes, as well current and total uptime,
are not available when data is read from [Linux hwmon]._<br>

The PSU is able to report monitoring data about its own hardware and basic
electrical variables for the input and output sides.

```
# liquidctl status
Corsair RM650i
├── Current uptime                    3:43:54
├── Total uptime             9 days, 11:43:54
├── VRM temperature                      50.0  °C
├── Case temperature                     40.8  °C
├── Fan control mode                 Hardware
├── Fan speed                               0  rpm
├── Input voltage                      230.00  V
├── +12V OCP mode                  Multi rail
├── +12V output voltage                 12.12  V
├── +12V output current                  7.75  A
├── +12V output power                   92.00  W
├── +5V output voltage                   4.97  V
├── +5V output current                   2.88  A
├── +5V output power                    14.00  W
├── +3.3V output voltage                 3.33  V
├── +3.3V output current                 1.56  A
├── +3.3V output power                   5.00  W
├── Total power output                 110.00  W
├── Estimated input power              124.00  W
└── Estimated efficiency                   89  %
```

Input power and efficiency are estimated from efficiency data advertised by
Corsair in the respective HXi and RMi PSU user manuals.

These estimates are not accurate at load levels bellow 10%, in particular with
the HX1500i and the 2022 re-issue of the HX1000i.

_Changed in 1.11.0: temperature sensors 1 and 2 have been renamed to VRM and
case, respectively._<br>

## Fan speed

The fan speed is normally controlled automatically by the PSU.  It is possible to override this and set the fan to a fixed duty value using the `fan` channel.

```
# liquidctl set fan speed 90
```

This changes the fan control mode to software control; to revert back to hardware control,
re-`initialize` the device. While in software control mode, a minimum allowed duty value of 30% is
enforced, for safety, by liquidctl.

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

_<sup>1</sup> See comments in [issue #300](https://github.com/liquidctl/liquidctl/issues/300)._<br>
_<sup>2</sup> Available at [80 PLUS® Certified Power Supplies and Manufacturers](https://www.clearesult.com/80plus/manufacturers/115V-Internal)._<br>


## Interaction with Linux hwmon drivers
[Linux hwmon]: #interaction-with-linux-hwmon-drivers

_New in 1.9.0._<br>

These devices are supported by the mainline Linux kernel with its
[`corsair-psu`] driver, and status data is provided through a standard hwmon
sysfs interface.

Starting with version 1.9.0, liquidctl automatically detects when a kernel
driver is bound to the device and, whenever possible, uses it instead of
directly accessing the device.  Alternatively, direct access to the device can
be forced with `--direct-access`.

[`corsair-psu`]: https://www.kernel.org/doc/html/latest/hwmon/corsair-psu.html
