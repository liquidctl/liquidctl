
# Lian Li Uni Fan Controllers
_Driver API and source code available in [`liquidctl.driver.lianli_uni`](../liquidctl/driver/lianli_uni.py)._

_New in git_<br>

This is a driver for supporting multiple Lian Li Uni fan hubs.

## Supported Devices

- **Lian Li Uni SL**
- **Lian Li Uni SL v2**
- **Lian Li Uni AL**
- **Lian Li Uni AL v2**
- **Lian Li Uni SL-Infinity**

### Features

- **Fixed Speed Control**: Set a fixed speed (in percentage) for individual channels.
- **Channel Status Reporting**: Provides the current RPM of each fan channel queried directly from the controller.
- **Fan mode control toggle (in code)**: Allows toggling between Auto and fixed speed on each fan channel.

## Initialization

It is recommended to initialize before usage. During initialization, automatic fan control is explicitly enabled on all fan channels. When setting a fixed fan speed, automatic control is disabled for that channel.

```sh
# liquidctl initialize
Lian Li Uni SL Controller
├── Device                        Lian Li Uni SL Controller
└── Firmware version              N/A
```

## Monitoring

The device can report the current speed, in RPM, for each fan channel.

```sh
# liquidctl status
Lian Li Uni SL Controller
├── Channel 1                      1320 rpm
├── Channel 2                      1335 rpm
├── Channel 3                      1320 rpm
└── Channel 4                      1320 rpm
```

## Fan Speeds

Fan speeds can be manually set to fixed duty values for each available channel. The channel number is zero-based and must be between 0 and 3.

```sh
# liquidctl set 0 speed 80
# liquidctl set 2 speed 40
# liquidctl set 3 speed 20
```

| Channel | Minimum Duty | Maximum Duty |
|---------|--------------|--------------|
| 0       | 0%           | 100%         |
| 1       | 0%           | 100%         |
| 2       | 0%           | 100%         |
| 3       | 0%           | 100%         |

## Toggling Control Mode (PWM Sync)

The driver supports toggling PWM synchronization on a per-channel basis, as an alternative to reinitializing the device, **via direct code usage**. The command line interface does not support toggling PWM synchronization.

To toggle PWM synchronization in code:

```python
from liquidctl import find_liquidctl_devices

# Find all connected and supported devices.
devices = find_liquidctl_devices()

for dev in devices:
    # Select Lian Li fan hub
    if "Lian Li" in dev.description:
        # Connect to fan hub
        with dev.connect():
            # Set the PWM Sync (example: enabling PWM sync for channel 0)
            dev.set_fan_control_mode(0, True)
```

- The first argument is the zero-based index for the channel (0-3 for channels 1-4).
- The second argument is optional; if omitted, it acts as a toggle but can also be explicitly set to `True` or `False`.

### Example Usage

#### Reset Auto mode on All Channels

```sh
# liquidctl initialize
Initializing Lian Li Uni SL Controller
├── Device              Lian Li Uni SLV2 Controller  
└── Firmware version                            N/A
```

#### Set Fixed Speed for Channel 1

```sh
# liquidctl -n 0 set 0 speed 50 -v
INFO: setting 1 PWM duty to 50%
```

#### Check Device Status

```sh
# liquidctl status
Lian Li Uni SL-Infinity
├── Channel 1    1365  rpm
├── Channel 2    1350  rpm
├── Channel 3    1350  rpm
└── Channel 4    1335  rpm
```

## Acknowledgements

This driver was developed with information provided by [EightB1ts](https://github.com/EightB1ts), including device IDs, PWM commands, and speed byte calculations.
