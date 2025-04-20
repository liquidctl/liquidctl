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

The Razer Hanbo is a profile driven device, there are no direct PWM modes.
The fan and pump can select from three built-in (fixed) profiles and one custom
profile. The fan and pump operate independently and have independent profile
sets. The pump profiles use the internal coolant temperature as its reference
and traverses autonomously. Fan profiles rely on an external reference
temperature being provided in order traverse its curve. Without updates, the
fans will continue using the duty cycle assigned to the previously sent
reference temperature.

A trait of the Razer Hanbo are that the temperature points in the curves are
fixed. For this reason any temperatures provided to input curves will be
ignored. Duty cycles will be processed in order and allocated to the
following temperatures:

20, 30, 40, 50, 60, 70 ,80, 90, 100.

The four profile names for the purposes of the driver are
- silent
- balance
- performance
- custom

## Initialization
[Initialization]: #initialization

No initialization is required for the Razer Hanbo. Calling this function
returns the unit serial number, firmware version and presets the reference
fan curve temperature to 30°C.


```
# liquidctl --match razer initialize
Razer Hanbo Chroma
├── Serial number                    123456789ABCDEF
└── Firmware version    [128, 0, 1, 1, 32, 0, 2, 16]
```

## Monitoring

The device reports status on the pump and the fans. The fans are monitored
collectively. The liquid temperature and currently active profile are also
reported.

```
# liquidctl --match razer status
Razer Hanbo Chroma
├── Liquid temperature       30.6  °C
├── Pump speed               1680  rpm
├── Pump duty                  49  %
├── Pump profile          balance
├── Fan speed                1290  rpm
├── Fan duty                   50  %
└── Fan profile           balance
```

## Fan and pump profiles

Like the OEM software, it is not possible to directly issue a PWM duty cycle
or speed to the fan or pump. The user can select between three preset profiles
or upload a custom fan profile. All of these utilise the Yoda API in the same
manner as the MSI MPG Coreliquid.

`set_hardware_status()` - Upload reference temperature to AIO for fan curve use.

`set_profiles()` - Upload a curve. Note that the expected format remains as per
every other device, but the temperature bytes will be ignored as these are
fixed values on the Hanbo. The curve does not take effect until custom mode
is the selected profile.

`set_speed_profile()` - Select a profile

## Interaction with Linux hwmon drivers
[Linux hwmon]: #interaction-with-linux-hwmon-drivers

These devices are supported by the [liquidtux] `razer_hanbo` driver, and status
data is provided through a standard hwmon sysfs interface.

liquidctl automatically detects when a kernel driver is bound to the device and,
whenever possible, uses it instead of directly accessing the device.
Alternatively, direct access to the device can be forced with `--direct-access`.
