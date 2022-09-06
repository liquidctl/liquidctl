Interacting with devices with Linux hwmon drivers
=================================================

The Linux kernel has being gaining drivers for the devices that we support, and
these drivers generally include a hwmon interface.

It is useful to detect the presence of a hwmon driver and, if possible, to
leverage it for improved performance and/or to prevent racing with the kernel
driver.

This document presents some guidelines on how to work with hwmon-enabled
devices in liquidctl.


Defining some terms
-------------------

_Operation:_ a method call like `initialize()` or `set_fixed_speed()`, or its
equivalent CLI command.


Detect and log the presence of a hwmon driver
---------------------------------------------

This is done automatically for HIDs being accessed through hidraw: a `_hwmon`
field with be present and not `None` when a hwmon interface has been detected.
The value is an instance of `liquidctl.driver.hwmon.HwmonDevice`.

Detection has not yet been implemented for other devices.  However, at the time
of writing this, all liquidctl devices with hwmon support are HIDs, and using
hidraw is the default (although its available depends on how cython-hidapi was
compiled).


Delegate to hwmon if possible
-----------------------------

This generally improves performance and/or prevents races with the kernel
driver.

It can be acceptable to slightly reduce the feature set in order to still use
the hwmon interface.  Especially if the lost features are minor.

Delegating to hwmon can be done on API-by-API basis.


Log (INFO) when an operation is delegated to hwmon
--------------------------------------------------

Example:

```py
_LOGGER.info('bound to %s kernel driver, assuming it is already initialized', self._hwmon.driver)
_LOGGER.info('bound to %s kernel driver, reading status from hwmon', self._hwmon.driver)
```


Warn when an operation is degraded while delegated to hwmon
-----------------------------------------------------------

Example:

```py
_LOGGER.warning('some attributes cannot be read from %s kernel driver', self._hwmon.driver)
```


Allow forced direct access despite hwmon
----------------------------------------

Operations should accept a `direct_access` argument, equivalent to a
`--direct-access` option on the command line.


Warn when directly accessing through force
------------------------------------------

Even if the operation does not (currently) cause an access race, we want to
encourage users to rely on hwmon, when possible.

Example:

```py
_LOGGER.warning('forcing re-initialization despite %s kernel driver', self._hwmon.driver)
_LOGGER.warning('directly reading the status despite %s kernel driver', self._hwmon.driver)
```


Do not warn if hwmon does not (yet) support an operation
--------------------------------------------------------

Logging in those case is optional, but not especially encouraged.


Useful resources
----------------

[(linux/doc) Naming and data format standards for sysfs files](https://www.kernel.org/doc/html/latest/hwmon/sysfs-interface.html)

[(linux/doc) Hardware Monitoring Kernel Drivers](https://www.kernel.org/doc/html/latest/hwmon/index.html#hardware-monitoring-kernel-drivers)

[(linux/doc) `/sys/class/hwmon/` ABI](https://www.kernel.org/doc/html/latest/admin-guide/abi-testing.html#file-srv-docbuild-lib-git-linux-testing-sysfs-class-hwmon)
