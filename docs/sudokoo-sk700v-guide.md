# Sudokoo SK700V CPU cooler

_Driver API and target audience: standard, generic users_<br>
_New in git._

The SK700V is a CPU air cooler with an integrated LCD display that shows
system metrics (temperature, CPU load, frequency, and power consumption).

## Initializing the device

The device can be initialized by calling `initialize`, which establishes
communication with the display:

```
# liquidctl initialize
Sudokoo SK700V
├── Device             Sudokoo SK700V
└── Status             Connected
```

## Sending metrics to the display

The display is designed to show real-time CPU metrics. Since liquidctl does not
continuously monitor system metrics, this driver is best used with an external
monitoring daemon that periodically calls the driver API.

The driver exposes the `set_status_display` method for this purpose:

```python
from liquidctl.driver import find_liquidctl_devices

for dev in find_liquidctl_devices():
    if 'SK700V' in dev.description:
        with dev.connect():
            dev.initialize()
            dev.set_status_display(
                temp=55,      # Temperature in degrees
                load=25,      # CPU load percentage (0-100)
                freq=4500,    # Frequency in MHz
                power=65,     # Power in Watts
                temp_scale='C'  # 'C' for Celsius, 'F' for Fahrenheit
            )
```

A companion daemon script, [sk700v-monitor], can be used to automatically read
CPU metrics and send them to the display.

[sk700v-monitor]: https://github.com/fpelliccioni/sk700v-monitor

## Temperature scale

The display supports both Celsius and Fahrenheit temperature scales. The scale
is set per-update via the `temp_scale` parameter.

## Limitations

- The device is write-only; it cannot report status information.
- Metrics must be sent continuously (~1 second intervals) to keep the display
  active.
- The display turns off automatically if no data is received.

## Protocol

The protocol was reverse-engineered from the Windows MasterCraft software.
See the [protocol documentation] for technical details.

[protocol documentation]: developer/protocol/sudokoo.md
