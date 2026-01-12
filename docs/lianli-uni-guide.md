# Lian Li Uni Fan controllers
_Driver API and source code available in [`liquidctl.driver.lianli_uni`](../liquidctl/driver/lianli_uni.py)._

_New in git_<br>

This is a driver for supporting multiple Lian Li Uni fan hubs.

## Supported devices

- **Lian Li Uni SL**
- **Lian Li Uni SL v2**
- **Lian Li Uni AL**
- **Lian Li Uni AL v2**
- **Lian Li Uni SL-Infinity**

### Features

- **Fixed Speed Control**: Set a fixed speed (in percentage) for individual channels.
- **Channel Status Reporting**: Provides the current RPM of each fan channel queried directly from the controller.
- **Fan mode control toggle (in code)**: Allows toggling between auto and fixed speed control on each fan channel.

## Initialization

It is recommended to initialize before usage. During initialization, automatic fan control is explicitly enabled on all fan channels. When setting a fixed fan speed, automatic control is disabled for that channel.

```
# liquidctl initialize
Lian Li Uni SL Controller
```

## Monitoring

The device can report the current speed, in RPM, for each fan channel.

```
# liquidctl status
Lian Li Uni SL Controller
├── Channel 1    1365  rpm
├── Channel 2    1350  rpm
├── Channel 3    1350  rpm
└── Channel 4    1335  rpm
```

## Fan speeds

Fan speeds can be manually set to fixed duty values for each available channel. The channels are named `fan1` through `fan4`.

```
# liquidctl set fan1 speed 80
# liquidctl set fan2 speed 40
# liquidctl set fan3 speed 20
# liquidctl set fan3 speed 20
```

| Channel | Minimum Duty | Maximum Duty |
|---------|--------------|--------------|
| 1       | 0%           | 100%         |
| 2       | 0%           | 100%         |
| 3       | 0%           | 100%         |
| 4       | 0%           | 100%         |

## Toggling fan control mode (aka PWM Sync)

The driver supports an additional API to toggle automatic fan control (aka PWM Sync) on a per-channel basis, as an alternative to reinitializing the device. **This only avaible via the Python API**. The command line interface does not support toggling PWM synchronization.

To toggle automatic fan control from Python code:

```python
from liquidctl import find_liquidctl_devices
from liquidctl.driver.lianli_uni import ChannelMode

# Find all connected and supported devices.
devices = find_liquidctl_devices()

for dev in devices:
    # Select a Lian Li fan hub.
    if "Lian Li" in dev.description:
        # Connect to the fan hub.
        with dev.connect():
            # Set the PWM Sync; for example, enable PWM Sync for channel 1.
            dev.set_fan_control_mode(1, ChannelMode.AUTO)
```

- the first argument is the channel number (1–4);
- the second argument is the desired mode: `ChannelMode.AUTO` or `ChannelMode.FIXED`.

### Example usage

#### Reset auto mode on all channels

```
# liquidctl initialize
Lian Li Uni SL Controller
```

#### Set fixed speed for channel 1

```
# liquidctl set fan1 speed 50 -v
INFO: setting fan1 PWM duty to 50%
```

#### Check device status

```
# liquidctl status
Lian Li Uni SL Controller
├── Channel 1    1365  rpm
├── Channel 2    1350  rpm
├── Channel 3    1350  rpm
└── Channel 4    1335  rpm
```

## Acknowledgements

This driver was developed with information provided by [EightB1ts](https://github.com/EightB1ts), including device IDs, PWM commands, and speed byte calculations.
