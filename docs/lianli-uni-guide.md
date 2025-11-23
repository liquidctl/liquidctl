
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

- **Fixed Speed Control**: Set fixed speed (in percentage) for individual channels after disabling PWM synchronization.
- **Channel Status Reporting**: Provides the last set duty percentage of each fan channel. (resets after disconnect)
- **PWM Synchronization Toggle (in code)**: Allows toggling PWM synchronization on each fan channels via direct code usage.

## Initialization

It is recommended to initialize before usage. During initialization, PWM synchronization is explicitly disabled on all fan channels, allowing for fixed speed adjustments.

```sh
# liquidctl initialize
Lian Li Uni SL Controller
├── Device                        Lian Li Uni SL Controller
└── Firmware version              N/A
```

This initialization ensures that the device is ready for manual fan control operations.

## Monitoring

The device can report the last set fan speed for each fan channel. Do note, this resets when `disconnect` is triggered, so it will not work in the terminal, for example.
This has mainly been implemented for programs like CoolerControl.

```sh
# liquidctl status
Lian Li Uni SL Controller
├── Channel 1                      0 %
├── Channel 2                      0 %
├── Channel 3                      0 %
└── Channel 4                      0 %
```

## Fan Speeds

Fan speeds can be manually set to fixed duty values for each available channel. The channel name can be anything, as long as it ends with the channel number you want to adjust.

```sh
# liquidctl set channel1 speed 80
# liquidctl set fan2 speed 40
# liquidctl set 3 speed 20
```

| Channel  | Minimum Duty | Maximum Duty |
|----------|--------------|--------------|
| channel1 | 0%           | 100%         |
| channel2 | 0%           | 100%         |
| channel3 | 0%           | 100%         |
| channel4 | 0%           | 100%         |

**Important**: Always ensure that PWM synchronization is disabled on the desired channel before attempting to set a fixed speed. If PWM is enabled, the fixed speed command will not take effect, and an appropriate log message will indicate this.

## Toggling PWM Synchronization

The driver supports toggling PWM synchronization on a per-channel basis, **via direct code usage**. The command line interface does not support toggling PWM synchronization.

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
            dev.toggle_pwm_sync(0, True)
```

- The first argument is the zero-based index for the channel (0-3 for channels 1-4).
- The second argument is optional; if omitted, it acts as a toggle but can also be explicitly set to `True` or `False`.

### Example Usage

#### Disable PWM Sync on All Channels

```sh
# liquidctl initialize
Initializing Lian Li Uni SL Controller
├── Device              Lian Li Uni SLV2 Controller  
└── Firmware version                            N/A
```

#### Set Fixed Speed for Channel 2

```sh
# liquidctl -n 0 set channel1 speed 50 -v
INFO: Initialized LianLiUni driver for device type: SLV2
INFO: Fan speed for Channel 1 set to 50%
INFO: Disconnecting from device
```

#### Check Device Status

```sh
# liquidctl status
Lian Li Uni SL Controller
├── Channel 1                      0 %
├── Channel 2                      0 %
├── Channel 3                      0 %
└── Channel 4                      0 %
```

## Notes

- If PWM sync is enabled on a channel, manual speed adjustments will not take effect. Use the `toggle_pwm_sync` function in code to disable it first or use `initialize` to disable PWM on all channels.
- The reported speed values reset once the device disconnects, which happens automatically when using terminal commands.

## Acknowledgements

This driver was developed with information provided by [EightB1ts](https://github.com/EightB1ts), including device IDs, PWM commands, and speed byte calculations.
