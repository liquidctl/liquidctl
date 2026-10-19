# XYZ Thermax air cooler temperature display
_Driver API and source code available in [`liquidctl.driver.xyz_thermax`](../liquidctl/driver/xyz_thermax.py)._

The XYZ Thermax 6 Pro Duo has a small display on top that shows a CPU temperature.  It is an
independent USB HID device (`5131:2007`); the fans and the ARGB lighting of the cooler are wired
to the motherboard and are not reachable through it.  The display measures nothing: it shows
whatever the host sends, and the vendor only provides a Windows application for that.

## Matching and permissions

`5131:2007` is a generic vendor/product pair, shared with other hardware (for example some magnetic
stripe card readers), and the device reports no manufacturer or product strings.  liquidctl has
no way of telling them apart, so use `--match thermax` together with `--vendor 0x5131` if you
have other such devices connected.  The driver never reads from the device and `initialize` does
not write to it.

## Initialization

Initialization is not required, and there is nothing to report.

## Monitoring

The device does not report any status.

## Showing a temperature

The `lcd` channel takes the unit the display should use, `celsius` or `fahrenheit`, and the CPU
temperature, optionally followed by the GPU temperature, as whole numbers of degrees Celsius
between 0 and 127.  The display converts to Fahrenheit by itself, so the values are always given
in °C.

```
# liquidctl set lcd screen celsius 54
# liquidctl set lcd screen fahrenheit 54,49
```

The Thermax 6 Pro Duo shows the first (CPU) value.  The GPU field is also part of the protocol and
is sent when given, in case other models use it.

liquidctl is not a daemon, so it sends a single report per command.  The vendor application
sends one about every second; whether the display keeps the last value or goes blank after some
time may depend on the model and firmware.  To keep it updated, run the command periodically
(for example from a systemd timer or a shell loop).

## Protocol notes

The report layout was obtained from the vendor application by static analysis, for
interoperability.  A 64-byte output report (report ID 0) is written:

| Byte | Content |
| :-- | :-- |
| 0 | `0x40` |
| 1 | CPU temperature in °C; bit `0x80` set makes the display show °F |
| 9 | GPU temperature in °C, with the same `0x80` flag |
| 29 | checksum: sum of bytes 0 to 28, modulo 256 |
| other | `0x00` (other bytes carry usage, memory, disk and clock values that no known model shows) |

More detail, and a standalone Linux daemon, in
<https://github.com/diegozpy/xyz-thermax-6-pro-duo-linux>.
