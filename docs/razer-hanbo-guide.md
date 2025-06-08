# Razer Hanbo Chroma
_Driver API and source code available in [`liquidctl.driver.razer_hanbo`](../liquidctl/driver/razer_hanbo.py)._

The Razer Hanbo Chroma are a pair of AIO liquid coolers coming in 360mm and
240mm radiator varieties. Other than the lack of a third fan on the 240mm
version, they should be otherwise identical.

This driver supports
- General monitoring
- Pump profile support
- Fan profile support
- Hwmon read offloading with direct-mode fallback

All configuration is done through USB. In the event of a power cycle the
AIO firmware will automatically restore to its previously commanded state.

## Initialization
[Initialization]: #initialization

No initialization is required for the Razer Hanbo. Calling this function
returns the unit serial number, firmware version and presets the reference
fan curve temperature to 30°C.

```
# liquidctl --match razer initialize
Razer Hanbo Chroma
├── Serial number                    123456789ABCDEF
└── Firmware version                          V1.2.0
```

## Monitoring

The device reports status on the pump and the fans. For fans, only one is
monitored for the purposes of RPM measurement. The specific fan is based
on how the AIO was assembled by the user. The liquid temperature and active
curve profile for each channel are also reported.

```
# liquidctl --match razer status
Razer Hanbo Chroma
├── Liquid temperature       30.6  °C
├── Pump speed               1680  rpm
├── Pump duty                  49  %
├── Pump profile          balanced
├── Fan speed                1290  rpm
├── Fan duty                   50  %
└── Fan profile           balanced
```

## Fan and pump profiles

The Razer Hanbo is a profile driven device, there are no direct PWM modes.
The fan and pump can select from three built-in (fixed) profiles and one custom
profile. The fan and pump operate independently and have independent profile
sets.

The four profile names for the purposes of the driver are
- quiet
- balanced
- extreme
- custom

The custom curve is defined by 9 points. Each point is associated with a fixed
temperature: 20C, 30C, 40C, 50C, 60C, 70C ,80C, 90C & 100C. The user can
associate a PWM duty cycle with each point, the firmware will interpolate as
required. PWM duty cycles must be equal to or monotonically increasing the
previous value, the first value sets the baseline.

The pump profiles use the internal coolant temperature as its reference
and traverses its curve autonomously. Fan profiles rely on updates
to the reference temperature in order traverse its curve. Without updates,
the fans will remain on the duty cycle assigned to its location on the curve.
It must be noted that this applies to all fan profiles not just the custom
curve. It is expected that a program external to liquidctl will provide
these updates.

The following functions implement fan and pump profile control:

`set_hardware_status()` - Upload reference temperature to AIO for fan curve use.
This is mapped to `set <channel> reftemp <temp>` on the CLI. Temperature is
resolved in degrees Celsius in 1 degree steps, clamped to values between 0
and 100.

`set_speed_profile()` - Defines a custom curve. Note that the format remains as
per every other device, but the temperature values will be ignored as these are
fixed in firmware. The curve does not take effect until `custom` mode is set in
`set_profiles()`. Each curve has 9 points, all need be defined and must be equal
to the previous value, if not increasing monotonically.
This is mapped to `set <channel> speed (<temperature> <percentage>)` on the CLI.

`set_profiles()` - Sets a rotor to a particular profile.
This is mapped to `set <channel> tprofile <profile>` on the CLI.

## Interaction with Linux hwmon drivers
[Linux hwmon]: #interaction-with-linux-hwmon-drivers

These devices are supported by the [liquidtux] `razer_hanbo` driver, and status
data is provided through a standard hwmon sysfs interface.

liquidctl automatically detects when a kernel driver is bound to the device and,
whenever possible, uses it instead of directly accessing the device. This will
happen for all read operations. Write operations will remain managed by liquidctl.
Alternatively, direct access to the device can be forced with `--direct-access`.

[liquidtux]: https://github.com/liquidctl/liquidtux
