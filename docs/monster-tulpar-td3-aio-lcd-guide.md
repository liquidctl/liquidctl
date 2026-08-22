# Monster Tulpar TD3 AIO LCD

_New in git._<br>

Driver API and source code are available in `liquidctl.driver.monster_lcd`.

This is experimental, partial support for the HID LCD controller found in a
tested Monster Tulpar TD3 AIO system.  It controls the display only; it does
not expose or change fan speed, pump speed, coolant temperature, or other
cooling functions.

The implementation was independently developed from observed USB traffic and
the behavior of the tested hardware.  Different hardware or firmware revisions
may behave differently.

## Device selection

The tested controller enumerates as `1d6b:0130`.  If several HID interfaces
match the same identifiers, list the candidates and select the working one with
`--pick`:

```console
# liquidctl --vendor 1d6b --product 0130 list --verbose
# liquidctl --vendor 1d6b --product 0130 --pick 0 initialize
```

Do not copy these identifiers to an unverified system.  Check the actual HID
interfaces first.

## Initialization and wake

Initialize the controller after boot, resume, or reconnect:

```console
# liquidctl --match "Tulpar TD3" initialize
```

Initialization sends the observed synchronization sequence and a wake request.
A standalone wake request can also be sent with:

```console
# liquidctl --match "Tulpar TD3" set lcd screen wake
```

The tested firmware does not reliably return an application-level
acknowledgement.  A command that was written successfully is therefore not
reported as failed solely because no acknowledgement was received.

## Brightness and orientation

Brightness accepts a percentage from 0 to 100.  The controller's observed
firmware range starts at 10, so the driver maps the requested percentage to
that range:

```console
# liquidctl --match "Tulpar TD3" set lcd screen brightness 50
```

The supported orientations are 0, 90, 180, and 270 degrees:

```console
# liquidctl --match "Tulpar TD3" set lcd screen orientation 90
```

## Keeping the display awake

The tested controller turns the LCD off after host keep-alive traffic stops.
It needs a `resume` request and a state request approximately once per second
while the host is awake.  The one-shot CLI command for a single cycle is:

```console
# liquidctl --match "Tulpar TD3" set lcd screen keep-alive
```

A persistent service should keep one driver connection open and call the
device-specific `keep_alive()` method.  For example:

```python
import time

from liquidctl import find_liquidctl_devices

device = next(find_liquidctl_devices(match="Tulpar TD3"))
with device.connect():
    device.initialize()
    while True:
        device.keep_alive()
        time.sleep(1)
```

The loop should stop while the system is suspending and initialize the device
again after resume.

## Images and animations

Image and animation upload are not supported.  Captured traffic indicates that
media transfer uses a separate block protocol that has not yet been fully
decoded and validated.

