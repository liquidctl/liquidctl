# Running your first command-line program

The command line is very straightforward: it was a precursor to the graphical
user interfaces (GUIs) we are so used to, so it is much more simple and
explicit than a GUI.

A shell/terminal like Windows Command Prompt or Powershell is just some place
were you write what you want some program to do.  And they come with a  few
build-in "special programs" like `cd` (change directory).

Unlike GUIs, command-line programs simply output their results to the terminal
they were called from.

I will get to "how to install" in a bit, but for now let us assume liquidctl
has already been set up.

If you want to list all devices, just type and hit enter:

    liquidctl list

And this will result in an output that looks similar to:

    Device ID 0: NZXT Smart Device (V1)
    Device ID 1: NZXT Kraken X (X42, X52, X62 or X72)

If you want to list all devices showing a bit more information:

    liquidctl list --verbose

If you want to initialize all devices (which you should!):

    liquidctl initialize all

If you want to show the status information:

    liquidctl status

To change say the pump speed to 42%:

    liquidctl set pump speed 42

This last command will not show any output.  This is normal: command-line
programs tend to follow a convention that simplifies chaining programs and
automating things with scripts: (unless explicitly requested otherwise), only
output useful information or error messages.

Some liquidctl commands can get slightly less English-looking than what was
showed above, but they should still be readable.  For example, to set the fans
to follow the profile defined by three points (25°C -> 10%), (30°C -> 50%), (40°C
-> 100%), execute:

    liquidctl set fan speed 25 10 30 50 40 100

While in isolation these numbers are not very self explanatory, they are simply
the pairs of temperature and corresponding duty values:

    liquidctl set fan speed 25 10 30 50 40 100
                            ^^^^^ ^^^^^ ^^^^^^
                   pairs of temperature (°C) -> duty (%)

_(The profiles run on the device, and therefore can only refer to the internal
liquid temperature sensor)._

Each device family has a guide that can be found in the
[list of _Supported Devices_], and that lists all features and attributes
that are supported by those devices, as well as examples.

[list of _Supported Devices_]: ../../README.md#supported-devices

## Setting up liquidctl

There is currently no installer for Windows, due to a number of reasons (that
are not very important right now).

But the README has an extensive section on [how to manually install] liquidctl,
and you can join our [Discord server] and ask for assistance.

[how to manually install]: ../../README.md#manual-installation
[Discord server]: https://discord.gg/GyCBjQhqCd

## Final words

While you should be able to use liquidctl with just these tips, I still
recommend you take a look at the rest of the [README], the documents in [docs]
and, also, the output of:

    liquidctl --help

[README]: ../../README.md
[docs]: ..

## Notes

### About this document

This document was originally a response to a direct message:

> Hi. How are you? Hope you're staying safe and well. I just wanted to know of
> there is a windows gui for liquidctl?
> I have zero experience with command line stuff and I don't entirely understand
> it... also most of the guides are from late 2018 or early 2019.
> And i just bought a x53 kraken.
