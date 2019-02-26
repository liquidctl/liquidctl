# Installing on macOS

`liquidctl` relies on and defaults to `libusb`. There are issues with this. Apple revamped USB in 10.11 so they have a heavy reliance on ACPI. They also use kernel HID to communicate with devices in exclusive mode. Unlike Linux and Windows which can operate in shared mode. As such, you need to use `hidapi` to control water loops. The best solution for now is to use the [liquidctl/macos-extra](https://github.com/jonasmalacofilho/liquidctl/tree/macos-extra) branch. An issue pointed out on the master branch `libusb` requires unloading the kernel HID driver, which then renders all keyboards, mice, etc from working. You can reload the kext if you use a script. As in unload driver, start liquidctl then reload driver. But this came with issues. Sometimes a kernel panic happens, other times ports stopped working.

1. Clone or download the `macos-extra` branch to your user folder. Should be `/Users/username/liquidctl-macos-extra`.
2. Install [Python 3](https://www.python.org/downloads/release/python-372/). This is required.
3. Terminal `pip3 install --upgrade pip` This is required.
4. Terminal `pip3 install /Users/username/liquidctl-macos-extra`
5. You can test your device with `liquidctl list` and then `liquidctl status`

Full documentation on how to control pumps and fans [here](/docs/nzxt-kraken-x-3rd-generation.md#nzxt-kraken-x-3rd-generation)

Should you need to power cycle for any reason, you can use `launchd` to automaticlly set a pump configuration upon login. This is cleaner and more appropriate than dropping a `script.sh` file in your startup items. [Sample files here](https://github.com/icedterminal/ga-z270x-ug/tree/master/Post_Install/pump_control). 

1. Copy `liquidctlBoot.sh` to your user folder.
    * You can edit this file anytime to adjust settings.
2. Terminal `chmod +x ~/liquidctlBoot.sh` to make it executable.
3. Copy `com.jonasmalacofilho.liquidctl.plist` to `~/Library/LaunchAgents/`.
4. Terminal `launchctl load ~/Library/LaunchAgents/com.jonasmalacofilho.liquidctl.plist`.
    * To remove from startup: `launchctl unload ~/Library/LaunchAgents/com.jonasmalacofilho.liquidctl.plist`.
5. Power down so the pump forgets and defaults. Once you login, the script should run and the the lights should change.

PATH is already included since some users may not adjust their `.bash-profile`. Errors can be found in `system.log` using Console. CMD + F and search for *liquidctl*. This is a user item, so if you have more than one user this will not run for anyone else. This shouldn't be an issue since you don't need to run it for each user. You set your pump once per boot and done.

Test your cooling with terminal `yes > /dev/null &` - You need one instance per core. So if you have four cores, you enter that four times. To stop, `killall yes`.
