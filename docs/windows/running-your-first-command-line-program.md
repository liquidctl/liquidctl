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

First, there is no installer (for a number of reasons that are not very
important right now).  But there are pre-built executables so you do not need
to worry about installing Python and libraries.  It is also the easiest way for
non-programmers to use liquidctl on Windows, so it is what I am going to cover
here (see [notes] for how to install it the Pythonic way).

[notes]: #notes

Next, you should know about the concept of the `PATH` variable.  This is how
the shell, such as Windows Command Prompt or Powershell, finds executables when
you type `liquidctl`.

The idea is that PATH (this environment variable you can configure) is a list
of directories with programs that you want the shells to find; in Windows,
directories in `PATH` are separated by semicolons.

You can read more about the `PATH` variable in its [Wikipedia entry].
Unfortunately I cannot find any up-to-date guide from Microsoft on how to set
the `PATH` (apparently MS thinks you are supposed to just guess where the
setting for it is and how it works), so instead take a look at this [guide from
Aseem Kishore].

[Wikipedia entry]: https://en.wikipedia.org/wiki/PATH_(variable)
[guide from Aseem Kishore]: https://helpdeskgeek.com/windows-10/add-windows-path-environment-variable/

Anyway, getting back to running programs on a shell.  If an executable
(`liquidctl.exe`) is in a directory that is listed in your `PATH` variable,
then typing

    liquidctl

in any shell (like Windows Command Program) will just work.  You do not even
need the ".exe" suffix.

It is also possible to run programs not in the directories listed in `PATH`
(this is commonly referred to as running "programs not in PATH"): you just need
to specify the complete absolute or relative path to the executable.

So there are three ways of setting up `liquidctl.exe`:

* Place it somewhere sensible (personally I use the base `C:\Program Files\`
  directory) and make sure that directory is in the PATH (which it normally is
  not).

* Place it somewhere already in the PATH; I don't recommend this because in
  most cases you would be placing it into an internal Windows directory, or in
  the directory of some other program.

* Place it anywhere you like and either navigate to it via the shell or specify
  relative/absolute paths to it; I don't recommend this because it is annoying
  and not how command-lines/shells are supposed to be used.

The last stable version of liquidctl can be found in the [_Releases_ page].

[_Releases_ page]: https://github.com/liquidctl/liquidctl/releases

New drivers may not yet be a part of a stable release (which is the case with
the Kraken X53 as of 24 June 2020).  If that's the case, you can use one of the
automatic builds of the code we are working on.

All code in the repository is automatically tested and built for Windows.  The
executable for the latest code in the main code branch can be found at [current
build].  You can also browse all recent builds for all branches and features
been worked on in the [build history]; the executables are in the "artifacts"
tab.

[current build]: https://ci.appveyor.com/project/jonasmalacofilho/liquidctl/branch/main/artifacts
[build history]: https://ci.appveyor.com/project/jonasmalacofilho/liquidctl/history

## Final words

While you should be able to use liquidctl with just these tips, I still
recommend you take a look at the rest of the [README], the documents in [docs]
and, also, the output of:

    liquidctl --help

[README]: ../../README.md
[docs]: ..

## Notes

### The Pythonic way to install liquidctl

To install liquidctl the Pythonic way, first install Python (3.9 recommended),
with the option to add Python to PATH.  Then install liquidctl using pip:

    pip install liquidctl

Finally, install libusb, which unfortunately has to be done manually.  The
libusb DLLs can be found in [libusb/releases](https://github.com/libusb/libusb/releases)
(part of the `libusb-<version>.7z` files) and the appropriate (e.g. MS64)
`.dll` and `.lib` files should be extracted to the system or python
installation directory (e.g.  `C:\Windows\System32` or `C:\Python39`).

### About this document

This document was originally a response to a direct message:

> Hi. How are you? Hope you're staying safe and well. I just wanted to know of
> there is a windows gui for liquidctl?
> I have zero experience with command line stuff and I don't entirely understand
> it... also most of the guides are from late 2018 or early 2019.
> And i just bought a x53 kraken.
