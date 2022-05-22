import sys
from inspect import cleandoc

if __name__ == '__main__':

    # This script is meant to be executed from this directory or the project root.
    # We use that assumption to make Python pick the local liquidctl modules,
    # instead other versions that may be installed on the environment/system.
    sys.path = ['../..', ''] + sys.path

    from liquidctl.driver.base import find_all_subclasses
    from liquidctl.driver.nvidia import _NvidiaI2CDriver
    from liquidctl.driver.usb import BaseUsbDriver


    HEADER = '''
    # Rules that grant unprivileged access to devices supported by liquidctl.
    #
    # Users and distros are encouraged to use these if they want liquidctl to work
    # without requiring root privileges (e.g. without the use of `sudo`).
    #
    # In the case of I²C/SMBus devices, these rules also cause the loading of the
    # `i2c-dev` kernel module.  This module is required for access to I²C/SMBus
    # devices from userspace, and manually loading kernel modules is in itself a
    # privileged operation.
    #
    # Distros will likely want to place this file in `/usr/lib/udev/rules.d/`, while
    # users installing this manually SHOULD use `/etc/udev/rules.d/` instead.
    #
    # The suggested name for this file is `71-liquidctl.rules`.  Whatever name is
    # used, it MUST lexically appear before 73-seat-late.rules.  The suggested name
    # was chosen so that it is also lexically after systemd-provided 70-uaccess.rules.
    #
    # Once installed, reload and trigger the new rules with:
    #
    #   # udevadm control --reload
    #   # udevadm trigger
    #
    # Note that this will not change the mode of `/dev/hidraw*` devices that have
    # already been created.  In practice, this means that HIDs may continue to require
    # privileged access until, either, they are rebound to their kernel drivers, or
    # the system is rebooted.
    #
    # These rules assume a system with modern versions of systemd/udev, that support
    # the `uaccess` tag.  On older systems the rules can be changed to instead set
    # GROUP="plugdev" and MODE="0660"; other groups and modes may also be used.
    #
    # The use of the `uaccess` mechanism assumes that only physical sessions (or
    # "seats") need unprivileged access to the devices.[^1][^2]  In case headless
    # sessions are also expected to interactively run liquidctl, GROUP and MODE should
    # also be set, as a fallback.
    #
    # Finally, this file was automatically generated.  To update it, from a Linux
    # shell and the current directory, execute:
    #
    #     $ python generate-uaccess-udev-rules.py > 71-liquidctl.rules
    #
    # [^1]: https://github.com/systemd/systemd/issues/4288
    # [^2]: https://wiki.archlinux.org/title/Users_and_groups#Pre-systemd_groups
    '''

    MANUAL_RULES = r'''
        # Section: special cases

        # Host SMBus on Intel mainstream/HEDT platforms
        KERNEL=="i2c-*", DRIVERS=="i801_smbus", TAG+="uaccess", \
            RUN{builtin}="kmod load i2c-dev"
    '''


    print(cleandoc(HEADER))

    print()
    print()
    print(cleandoc(MANUAL_RULES))

    print()
    print()
    print(f'# Section: NVIDIA graphics cards')

    nvidia_devs = {}

    for driver in find_all_subclasses(_NvidiaI2CDriver):
        for did, sdid, description in driver._MATCHES:
            ids = (driver._VENDOR, did, sdid)
            if ids in nvidia_devs:
                nvidia_devs[ids].append(description)
                nvidia_devs[ids].sort()
            else:
                nvidia_devs[ids] = [description]

    nvidia_devs = [(svid, did, sdid, description) for (svid, did, sdid), description in nvidia_devs.items()]
    nvidia_devs.sort(key=lambda x: x[3][0])

    for svid, did, sdid, descriptions in nvidia_devs:
        print()
        for desc in descriptions:
            desc = desc.replace(' (experimental)', '')
            print(f'# {desc}')
        print(cleandoc(f'''
            KERNEL=="i2c-*", ATTR{{name}}=="NVIDIA i2c adapter 1 *", ATTRS{{vendor}}=="0x10de", \\
                ATTRS{{device}}=="{did:#06x}", ATTRS{{subsystem_vendor}}=="{svid:#06x}", \\
                ATTRS{{subsystem_device}}=="{sdid:#06x}", DRIVERS=="nvidia", TAG+="uaccess", \\
                RUN{{builtin}}="kmod load i2c-dev"
        '''))

    print()
    print()
    print(f'# Section: USB devices and USB HIDs')

    usb_devs = {}

    for driver in find_all_subclasses(BaseUsbDriver):
        for vid, pid, _, description, _ in driver.SUPPORTED_DEVICES:
            ids = (vid, pid)
            if ids in usb_devs:
                usb_devs[ids].append(description)
                usb_devs[ids].sort()
            else:
                usb_devs[ids] = [description]

    usb_devs = [(vid, pid, description) for (vid, pid), description in usb_devs.items()]
    usb_devs.sort(key=lambda x: x[2][0])

    for vid, pid, descriptions in usb_devs:
        print()
        for desc in descriptions:
            desc = desc.replace(' (experimental)', '')
            print(f'# {desc}')
        print(f'SUBSYSTEMS=="usb", ATTRS{{idVendor}}=="{vid:04x}", ATTRS{{idProduct}}=="{pid:04x}", TAG+="uaccess"')
