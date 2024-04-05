# ASUS Aura LED (USB-based) controllers
_Driver API and source code available in [`liquidctl.driver.aura_led`](../liquidctl/driver/aura_led.py)._

_New in 1.10.0._<br>

This driver supports ASUS Aura USB-based lighting controllers that appear in various ASUS Z490, Z590, and Z690 motherboards. These controllers operate in either (a) direct mode or (b) effect mode. _Direct_ mode is employed by Aura Crate in Windows. It requires the application to send a continuous stream of commands to the controller in order to modulate lighting effects on each addressable LED. The other mode is _effect_ mode in which the controller itself modulates lighting effects on each addressable LED. Effect mode requires the application to issue a single set of command codes to the controller in order to initiate the given effect. The controller continues to process that effect until the application sends a different command.

This driver employs the _effect_ mode (fire and forget). The selected lighting mode remains in effect until it is explicitly changed. This means the selected lighting mode remains in effect (a) on cold boot, (b) on warm boot, (c) after wake-from-sleep.

The disadvantage, however, is the inability to set different lighting modes to different lighting channels. All channels remain synchronized.

There are three known variants of the Aura LED USB-based controller:

- Device `0x19AF`: found in ASUS ProArt Z690-Creator WiFi
- Device `0x1939` [^1]
- Device `0x18F3`[^1]: found in ASUS ROG Maximus Z690 Formula

[^1]: Support for devices `0x1939` and `0x18F3` may not be sufficiently developed so users are asked to experiment and provide feedback. [Wireshark USB traffic capture](./developer/capturing-usb-traffic.md), in particular, will be very helpful.


## Initialization

ASUS Aura LED controller does not need to be initialized before use. Initialization is optional.

```
# liquidctl initialize
ASUS Aura LED Controller
└── Firmware version    AULA3-AR32-0207
```

## Status

The `status` function returns the number of ARGB and RGB channels detected by the controller. If the command is invoked with `--debug` flag, the entire reply from the controller will be displayed in groups of 6 bytes. This information has not been fully decoded, but is provided in the event that someone is able to decipher it.

On ASUS ProArt Z690-Creator WiFi the following is returned:

```
# liquidctl status
ASUS Aura LED Controller
├── ARGB channels: 2
└──  RGB channels: 1
```

To display the set of 6-byte status values, use `--debug` on the command line. The following will be returned:

```
# liquidctl --debug status
ASUS Aura LED Controller
├── ARGB channels: 2
├──  RGB channels: 1
├── Device Config: 1     0x1e, 0x9f, 0x02, 0x01, 0x00, 0x00
├── Device Config: 2     0x78, 0x3c, 0x00, 0x01, 0x00, 0x00
├── Device Config: 3     0x78, 0x3c, 0x00, 0x00, 0x00, 0x00
├── Device Config: 4     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 5     0x00, 0x00, 0x00, 0x01, 0x03, 0x02
├── Device Config: 6     0x01, 0xf4, 0x00, 0x00, 0x00, 0x00
├── Device Config: 7     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 8     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 9     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
└── Device Config: 10    0x00, 0x00, 0x00, 0x00, 0x00, 0x00
```

On ASUS ROG Strix Z690-i Gaming WiFi (mini-ITX) the following is returned:

```
# liquidctl --debug status
ASUS Aura LED Controller
├── ARGB channels: 2
├──  RGB channels: 1
├── Device Config: 1     0x1e, 0x9f, 0x02, 0x01, 0x00, 0x00
├── Device Config: 2     0x78, 0x3c, 0x00, 0x01, 0x00, 0x00
├── Device Config: 3     0x78, 0x3c, 0x00, 0x00, 0x00, 0x00
├── Device Config: 4     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 5     0x00, 0x00, 0x00, 0x01, 0x03, 0x02
├── Device Config: 6     0x01, 0xf4, 0x00, 0x00, 0x00, 0x00
├── Device Config: 7     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 8     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 9     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
└── Device Config: 10    0x00, 0x00, 0x00, 0x00, 0x00, 0x00
```

On some ASUS Z490 boards (controller ID 0x18F3) the following is returned:

```
# liquidctl --debug status
ASUS Aura LED Controller
├── ARGB channels: 1
├──  RGB channels: 1
├── Device Config: 1     0x1e, 0x9f, 0x01, 0x01, 0x00, 0x00
├── Device Config: 2     0x78, 0x3c, 0x00, 0x00, 0x00, 0x00
├── Device Config: 3     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 4     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 5     0x00, 0x00, 0x00, 0x06, 0x07, 0x02
├── Device Config: 6     0x01, 0xf4, 0x00, 0x00, 0x00, 0x00
├── Device Config: 7     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 8     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
├── Device Config: 9     0x00, 0x00, 0x00, 0x00, 0x00, 0x00
└── Device Config: 10    0x00, 0x00, 0x00, 0x00, 0x00, 0x00
```

## RGB lighting

The driver supports one 12V RGB channel named `led1` and three 5V Addressable RGB channels named `led2`, `led3`, and `led4`. Because the driver uses `effect` mode, all channels are synchronized. It is not possible at this time to set different color modes to different channels (`direct` mode is used for that). Nevertheless, independent channel names are provided in case a future BIOS update provides more flexibility in `effect` mode.

```
# liquidctl set led1 color static af5a2f
# liquidctl set led2 color breathing 350017
# liquidctl set led3 color rainbow
# liquidctl set led4 color spectrum-cycle
# liquidctl set sync color gentle-transition
```

Colors can be specified in RGB, HSV or HSL (see [Supported color specification formats](../README.md#supported-color-specification-formats)), and each animation mode supports zero or one color.


| Mode | Colors | Notes |
| --- | --- | --- |
| `off` | None |
| `static` | One |
| `breathing` | One |
| `flashing` | One |
| `spectrum_cycle` | None |
| `rainbow` | None |
| `spectrum_cycle_breathing` | None |
| `chase_fade` | One |
| `spectrum_cycle_chase_fade` | None |
| `chase` | One |
| `spectrum_cycle_chase` | None |
| `spectrum_cycle_wave` | None |
| `chase_rainbow_pulse` | None |
| `rainbow_flicker` | None |
| `gentle_transition` | None | name given by us |
| `wave_propagation` | None | name given by us |
| `wave_propagation_pause` | None | name given by us |
| `red_pulse` | None | name given by us |

In addition to these, it is also possible to use the `sync` pseudo-channel to apply a setting to all lighting channels.
