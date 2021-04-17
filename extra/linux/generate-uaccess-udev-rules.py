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
    # Rules that grant unprivileged access to devices supported by liquidctl
    #
    # Users and distros are encouraged to use these if they want liquidctl to work
    # without requiring root privileges (e.g. with the use of `sudo`).
    #
    # In the case of I²C/SMBus devices, these rules also cause the loading of the
    # `i2c-dev` kernel module.  The module is required for access to I²C/SMBus
    # devices from userspace, and loading kernel modules is in itself a privileged
    # operation.
    #
    # Distros will likely want to place this file in `/usr/lib/udev/rules.d/`,
    # while users installing this manually SHOULD use `/etc/udev/rules.d/` instead.
    #
    # The suggested name for this file is `71-liquidctl.rules`.  This was chosen
    # based on the numbering of other uaccess tagging rule files in my system (not
    # very scientific, I know, but I could not find any documented policy for
    # this), as well as the need to let users overrule these rules.
    #
    # These rules assume a system with modern versions of systemd/udev, that
    # support the `uaccess` tag; on older systems the rules can be changed to set
    # GROUP="plugdev" and MODE="0660" instead.  The currently deprecated 'plugdev'
    # group is not used by default to avoid generating warnings on systems that
    # have already removed it.
    #
    # Finally, this file was automatically generated.  To update it, from a Linux
    # shell and the current directory, execute:
    #
    #     $ python generate-uaccess-udev-rules.py > 71-liquidctl.rules
    #
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
