# Asus Aura LED (USB-based) controllers
_Driver API and source code available in [`liquidctl.driver.aura_led`](../liquidctl/driver/aura_led.py)._

__NOTE:__
Some features of this driver are still being worked on. Your use of this driver indicates that you understand and accept it is a beta release.


This driver supports Asus Aura USB-based lighting controllers that appear in Asus Z690 motherboards. These controllers operate in either (a) direct mode or (b) effect mode. _Direct_ mode is employed by Aura Crate in Windows. It requires the application to send a continuous stream of commands to the controller in order to modulate the lighting on each addressable LED in each channel. The other mode is _effect_ mode in which the controller itself modulates the lighting on each addressable LED in each channel. Effect mode requires the application to send a single set of command codes to the controller in order to initiate the given effect. The controller handles the rest until such time that the application sends a different command set.

This driver employs the _effect_ mode (fire and forget). The selected lighting mode remains in effect until it is explicitly changed. This means the selected lighting mode remains in effect (a) on cold boot, (b) on warm boot, (c) after wake-from-sleep.

The disadvantage, however, is the inability to set different lighting modes to different lighting channels. All channels remain synchronized.

There are three known variants of the Aura LED USB-based controller:

- Device `0x19AF`: found in Asus ProArt Z690-Creator WiFi
- Device `0x1939` [^1]
- Device `0x18F3`[^1]: found in Asus ROG Maximus Z690 Formula

[^1]: Support for devices `0x1939` and `0x18F3` is not properly or sufficiently developed so these devices have been commented-out in the driver. Users may uncomment the line(s) in `SUPPORTED_DEVICES` to experiment and provide feedback. Wireshark USB traffic  capture, in particular, will be very helpful.


## Initialization

Asus Aura LED controller does not need to be initialized before use. Initialization is optional and recommended.

```
# liquidctl -m Aura initialize
AsusTek Aura LED Controller
└── Firmware version    AULA3-AR32-0207
```

## Status

The `status` function currently returns a list of 6-byte values whose meanings are not fully understood. This information is provided nevertheless in the hopes of encouraging someone to interpret them properly.
```
% liquidctl -m Aura status
AsusTek Aura LED Controller
├── Device Config: 1     [30, 159, 3, 1, 0, 0]  
├── Device Config: 2     [120, 60, 0, 1, 0, 0]  
├── Device Config: 3     [120, 60, 0, 1, 0, 0]  
├── Device Config: 4     [120, 60, 0, 0, 0, 0]  
├── Device Config: 5        [0, 0, 0, 1, 4, 2]  
├── Device Config: 6      [1, 244, 0, 0, 0, 0]  
├── Device Config: 7        [0, 0, 0, 0, 0, 0]  
├── Device Config: 8        [0, 0, 0, 0, 0, 0]  
├── Device Config: 9        [0, 0, 0, 0, 0, 0]  
└── Device Config: 10       [0, 0, 0, 0, 0, 0]  
```

## RGB lighting

There is one 12V RGB channel named `rgb` and three 5V Addressable RGB channels named `argb1`, `argb2`, and `argb3`. Because the driver uses `effect` mode, all channels are synchronized. It is not possible to set different color modes to different channels except through `direct` mode.

```
# liquidctl -m Aura set rgb color static af5a2f
# liquidctl -m Aura set argb1 color breathing 350017
# liquidctl -m Aura set argb2 color rainbow
# liquidctl -m Aura set argb3 color spectrum-cycle
# liquidctl -m Aura set sync color gentle-transition
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


## Correspondence between lighting channels and physical locations

Each user may need to create a table that associates generic channel names to specific areas or headers on their motherboard. 