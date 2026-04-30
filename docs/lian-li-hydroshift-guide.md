# Lian Li HydroShift LCD AIO Liquid Coolers
_Driver API and source code available in [`liquidctl.driver.hydroshift_lcd`](../liquidctl/driver/hydroshift_lcd.py)._

_New in git._<br>

This driver covers the Lian Li HydroShift LCD family, which mounts a 480×480
round LCD on the pump head and exposes its fan/pump controllers and LEDs over
USB HID:

- Lian Li HydroShift LCD 360S (`0416:7398`)
- Lian Li HydroShift LCD RGB (`0416:7399`)
- Lian Li HydroShift LCD TL (`0416:739a`)

Only the 360S has been verified on real hardware so far; the other variants are
listed based on Lian Li's product line and protocol affinity.

## Initialization

The cooler does not strictly require initialization for sensor reads, but the
driver uses `initialize` to read the firmware version and select the
appropriate LCD transport (older firmware uses 1024-byte HID reports, firmware
≥ 1.2 uses 512-byte reports).

```
# liquidctl initialize
Lian Li HydroShift LCD 360S
├── Firmware version    N9,01,HS,SQ,HydroShift,V3.0B.02C,0.7
├── Liquid temperature                                  28.4  °C
├── Fan speed                                           1320  rpm
└── Pump speed                                          2520  rpm
```

## Device monitoring

Reports liquid temperature, pump and fan RPM, and the corresponding duty
percentages computed against the device's published max RPMs (3600 pump,
2520 fan).

```
# liquidctl status
Lian Li HydroShift LCD 360S
├── Liquid temperature    28.4  °C
├── Fan speed             1320  rpm
├── Fan duty                52  %
├── Pump speed            2520  rpm
└── Pump duty              70  %
```

## Fan and pump speed control

The AIO firmware owns the temperature curves; only fixed duty values are
settable from the host.

```
# liquidctl set fan speed 60
# liquidctl set pump speed 80
```

Speed *profiles* are not supported and will raise `NotSupportedByDevice`.

## Lighting

The fan ring exposes the following modes through the `fan` lighting channel:

- `rainbow`, `rainbow-morph`, `static`, `breathing`, `runway`, `meteor`,
  `color-cycle`, `staggered`, `tide`, `mixing`, `ripple`, `reflect`,
  `tail-chasing`, `paint`, `ping-pong`

Up to four RGB colors can be supplied. The animation speed
(`slowest`, `slower`, `normal`, `faster`, `fastest`) and direction
(`forward`, `backward`) are also configurable.

```
# liquidctl set fan color static ff8000
# liquidctl set fan color rainbow-morph 000000 --speed faster
# liquidctl set fan color paint ff0000 00ff00 0000ff ffff00 --direction backward
```

Pump-head lighting is not currently exposed by the driver.

## Screen

The LCD on the pump head supports static images, animated GIFs, and video
playback over USB. Brightness and orientation can be configured independently.

```
# liquidctl [options] set lcd screen brightness <value>
# liquidctl [options] set lcd screen orientation (0|90|180|270)
# liquidctl [options] set lcd screen static <path to image>
# liquidctl [options] set lcd screen gif <path to gif>
# liquidctl [options] set lcd screen video <path to video>
# liquidctl [options] set lcd screen lcd
```

Images, GIFs and videos are resized to 480×480 and rotated client-side
according to the configured orientation, which is persisted via
`RuntimeStorage` so it survives across invocations.

Video playback uses `ffmpeg` (decoded externally and streamed frame-by-frame
at 24 fps) and runs as a long-lived foreground command — terminate the
liquidctl process to stop playback and revert to the firmware's default
screen by sending `set lcd screen lcd`.

## Notes and limitations

- Pump-head lighting and any sensor/time/text overlays configured through
  L-Connect 3 are not yet exposed.
- The fan curve owned by the AIO controller cannot be modified from the host;
  use L-Connect 3 once to configure a profile that the firmware will retain.
- Video playback requires `ffmpeg` to be available on `PATH`.
