# Razer Hanbo Chroma
_Driver API and source code available in [`liquidctl.driver.razer_hanbo`](../liquidctl/driver/razer_hanbo.py)._

The Razer Hanbo Chroma are a pair of AIO liquid coolers coming in 360mm and
240mm radiator varieties. Other than the lack of a third fan on the 240mm
version, they should be identical.

_Testing and development so far has occurred only on the 360mm variant_

This driver supports
- General monitoring
- Pump profile support
- Fan profile support
- Hwmon read offloading and direct-mode.

All configuration is done through USB. In the event of a power cycle the AIO
firmware will automatically restore fan and pump channels to their previously
commanded state.

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

The device reports status on the pump and the fans. For the fans, only one is
monitored for the purposes of RPM measurement. The specific fan is based
on how the AIO was assembled by the user. The liquid temperature and active
profile for each channel are also reported.

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

The Razer Hanbo is a profile driven device with no direct PWM modes.
The fan and pump channels can select from three built-in (fixed) profiles and
one custom profile. Each channel's profiles operate independently.

The four profile names for the purposes of the driver are
- quiet
- balanced
- extreme
- custom

The quiet, balanced and extreme profiles have nominal PWMs of 20%, 50% and 80%
respectively but will go to 100% if the reference temperature threshold is 
reached (85 degrees C) or the USB interface is disconnected. If one channel
thresholds, all channels go to 100%. The AIO remains in this state until 65
degrees C or lower is reported, at which point control is restored.

The custom profile is implemented as a 9 point curve. Each point is associated
with monotonically increasing temperatures from 20C-100C in 10C steps.
The user allocates a PWM duty cycle with each point, the firmware will
interpolate points as required using the channel's reference temperature. PWM
duty cycles must be equal to or greater than the previous value, the first
value sets the baseline but must be at least 20%.

As each channel is independent, each reference is independent. Pump profiles
use the internal coolant temperature as its reference and will traverse its
curve autonomously. Fan profiles rely on user updates to its reference
temperature in order traverse its curve. Without updates, the fans will stay put
on the curve using the point's duty cycle. It must be noted that this applies
to all fan profiles not just custom. It is expected that a program external to
liquidctl will provide these updates. As the user specifies the reference
temperature, this is an indirect way of setting a desired PWM for the fans.

The following functions implement fan and pump profile control:

`set_hardware_status()` - Update the reference temperature on the AIO for fan
curve use. Temperature is resolved in 1 degree steps as degrees Celsius, clamped
to values between 0 and 100. This is mapped to `set <channel> reftemp <temp>`
on the CLI.

`set_speed_profile()` - Defines the custom profile curve. The standard 
argument ordering is used but the temperature values are ignored as these are
set in firmware. The curve does not take effect until the `custom` profile is
set in `set_profiles()`. Each curve has 9 points, all need be defined and must
be equal to or greater than the previous value with the first being the
baseline and a minimum value of 20%.
This is mapped to `set <channel> speed (<temperature> <percentage>)` on the CLI.

`set_profiles()` - Sets a rotor channel to a particular profile.
This is mapped to `set <channel> tprofile <profile>` on the CLI.

## Interaction with Linux hwmon drivers
[Linux hwmon]: #interaction-with-linux-hwmon-drivers

_Note: razer_hanbo is not merged yet_

These devices are supported by the [liquidtux] `razer_hanbo` driver with status
provided through the hwmon sysfs interface.

liquidctl automatically detects when a kernel driver is bound to the device.
As with other devices direct access can be forced on with the `--direct-access`
switch to bypass the kernel driver. When the driver is used read operations
will be offloaded but write operations will remain managed by liquidctl. This
is due to some commands requiring elevation when implemented using sysfs
semantics e.g. fan curve control which is undesirable.

The `razer_hanbo` sysfs interface independently tracks the AIO state. When
the kernel driver is loaded it will monitor transactions from the bound AIO to
passively update sysfs in the event that a userland application (liquidctl)
has made changes directly. This allows sysfs aware applications to remain
up to date and liquidctl to operate without elevation whilst being the primary
controller for the AIO.

[liquidtux]: https://github.com/liquidctl/liquidtux
