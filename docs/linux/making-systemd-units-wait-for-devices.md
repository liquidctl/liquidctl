# Making systemd units wait for devices

When using a systemd service to configure devices at boot time, as suggested in [Automation and running at boot/Set up Linux using system](../../README.md#set-up-linux-using-systemd), it can sometimes happen that the hardware is not ready when the service tries to start.

A blunt solution to this is to add a small delay, but a more robust alternative is to make the service unit depend on the corresponding hardware being available at the OS level.

## Systemd device units

For this it is first necessary to set up systemd to create device units with known names.  This is done with udev rules, specifically with `TAG+="systemd"` (to create a device unit) and a memorable `SYMLINK+="<some-name>"` name.

```
# /etc/udev/rules.d/99-liquidctl-custom.rules
# Example udev rules to create device units for some specific liquidctl devices.

# create a dev-kraken.device for this third-generation Kraken X
ACTION=="add", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1e71", ATTRS{idProduct}=="170e", ATTRS{serial}=="<serial number>", SYMLINK+="kraken", TAG+="systemd"

# create a dev-clc120.device for this EVGA CLC
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="2433", ATTRS{idProduct}=="b200", SYMLINK+="clc120", TAG+="systemd"
```

Setting a custom name with `SYMLINK` is optional: just with `TAG+="systemd"` alone a device unit will be made available as `dev-bus-usb-<bus>-<device>.device`, where the `<bus>` and the `<device>` numbers can be found with the `lsusb` command.

## Setting the dependencies

The new device units can then be added as dependencies to the service unit.

```
# /etc/systemd/system/liquidcfg.service
[Unit]
Description=AIO startup service
Requires=dev-kraken.device
Requires=dev-clc120.device
After=dev-kraken.device
After=dev-clc120.device
...
```

With these changes in place, and after rebooting the system, the service should begin to wait for the devices before trying to starting.

Notes:

- the `SUBSYSTEM` value must match how liquidctl connects to the device; devices listed by liquidctl as on a `hid` bus should use the value `hidraw`, while the remaining should use `usb`
- when possible it is good to include the serial number in the match, to account for the possibility of multiple units of the same model
- on the service unit file `Requires=` is used instead of `Wants=` because we want a [strong dependency](https://www.freedesktop.org/software/systemd/man/systemd.unit.html#%5BUnit%5D%20Section%20Options)
- rebooting the system is not technically necessary, but triggering the new udev rules without a reboot is outside the scope of this document
- some devices may still not be able to response just after being discovered by udev, in which case a delay is really necessary

## Alternative approach

An alternative approach is to have systemd start the configuration service when the device is found by udev, by making the device depend on the service:

```
ACTION=="add", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1e71", ATTRS{idProduct}=="170e", ATTRS{serial}=="<serial number>" ENV{SYSTEMD_WANTS}="liquidcfg.service"
```
