# Corsair HXi and RMi series PSUs

**Support for these devices is still experimental.**

## Initialization

These devices should operate and be accessible without any explicit initialization.

However, the driver is still under development and future versions could implement additional features that might depend on device state.  Because of this, it is still recommended to call `initialize` after booting the system.


```
# liquidctl initialize
```


## Monitoring

The PSU is able to report monitoring data about its own hardware and basic electrical variables for the input and output sides.

```
# liquidctl status
```
