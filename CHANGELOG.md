# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html) and [PEP 404](https://www.python.org/dev/peps/pep-0440/#semantic-versioning).


## [1.3.3] – 2020-02-18
_Summary for the 1.3.3 release: fix possibly stale data with HIDs and other minor issues._

Changelog since 1.3.2:
### Fixed
 - [HUE 2] Add missing identifiers for HUE+ accessories
 - Forward hid option from UsbHidDriver.find_supported_devices
 - Prevent reporting stale data during long lived connections to HIDs (#87)


## [1.3.2] – 2019-12-11
_Summary for the 1.3.2 release: fix fan status reporting from Smart Device V2._

Changelog since 1.3.1:
### Fixed
 - [Smart Device V2] Parse fan info from correct status message
### Checksums
```
acf44a491567703c109c03f446c3c0761e5f9b97098613f8ecb4366a1d2afd50  liquidctl-1.3.2-bin-windows-x86_64.zip
bb742947c15f4a3987685641c0dd73184c4a40add5ad818ced68e5ace3631b6b  liquidctl-1.3.2.tar.gz
```


## [1.3.1] – 2019-11-23
_Summary for the 1.3.1 release: fix parsing of `--verbose` and documentation improvements._

Changelog since 1.3.0:
### Changed
 - List included dependencies and versions in Windows' bundle
 - Improve the documentation
### Fixed
 - Fix parsing of `--verbose` in commands other than `list`
### Checksums
```
de272dad305dc6651265640a280bedb21bc680a62117e625004c6aad2104da63  liquidctl-1.3.1-bin-windows-x86_64.zip
6092a6fae477908c80adc825b290e39f0b26e604593884da23d40e892e553309  liquidctl-1.3.1.tar.gz
```


## [1.3.0] – 2019-11-17
_Summary for the 1.3.0 release: man page, Corsair RXi/HXi and NZXT E power supplies, Smart Device V2 and HUE 2 family, improved device discovery and selection._

Changelog since 1.3.0rc1:
### Added
 - Enable **experimental support for the NZXT HUE 2** with the Smart Device V2 driver
 - Enable **experimental support for the NZXT HUE 2 Ambient** with the Smart Device V2 driver
 - Add `-m, --match <substring>` to allow filtering devices by description
 - Add `-n` short alias for `--pick`
### Changed
 - [API] Allow initialize methods to optionally return status tuples
 - [Legacy 690LC] Conform to XDG basedir spec and prefer XDG_RUNTIME_DIR
 - [Legacy 690LC] Improve directory names for internal data
 - [Windows] Ship patched PyUSB and libusb 1.0.22
 - Improve the documentation
### Fixed
 - [NZXT E] Release the device once done
 - [NZXT E] Fix assertion of valid responses in retry loops
 - [HUE 2] Fix LED blinking during `status`
 - [HUE 2] Add missing identifier for 250 mm HUE 2 LED strips
 - Restore experimental tag for the NZXT Kraken X31/X41/X61 family
### Removed
 - Remove dependency on appdirs
### Checksums
```
ff935fd3d57dead4d5218e02f834a825893bc6716f96fc9566a8e3989a7c19fe  liquidctl-1.3.0-bin-windows-x86_64.zip
ce0483b0a7f9cf2618cb30bdf3ff4195e20d9df6c615f69afe127f54956e42ce  liquidctl-1.3.0.tar.gz
```


## [1.3.0rc1] – 2019-11-03

Changelog since 1.2.0:
### Added
 - **Add experimental support for Corsair HX750i, HX850i, HX1000i and HX1200i power supplies**
 - **Add experimental support for Corsair RM650i, RM750i, RM850i and RM1000i power supplies**
 - **Add experimental support for NZXT E500, E650 and E850 power supplies**
 - **Add experimental support for the NZXT Smart Device V2**
 - Add liquidctl(8) man page
 - Add `--single-12v-ocp` option to `initialize` (Corsair HXi/RMi PSUs)
 - Add `--pick <result>` device selection option
 - Add `initialize all` variant/helper
### Changed
 - Reduce the number of libusb and hidapi calls during device discovery
 - Improve the visual hierarchy of the output `list` and `status`
 - Allow `list --verbose` to run without root privileges (Linux) or special drivers (Windows)
 - Change the default API for HIDs on Linux to hidraw
 - Consider stable: Corsair H80i v2, H100i v2, H115i; NZXT Kraken X31, X41, X61; NZXT Grid+ V3
### Fixed
 - Don't try to reattach the kernel driver more than once
 - [Corsair H80i GT] Fixed device name throughout
 - [Corsair H110i GT] Fixed device name in listing
### Deprecated
 - [API] Use `liquidctl.driver.find_liquidctl_devices` instead of `liquidctl.cli.find_all_supported_devices`
### Checksums
```
$ sha256sum liquidctl-1.3.0rc1*
7a16a511baf5090c34cd3dfc5c21068a298515f31315be63e9b991ea17654671  liquidctl-1.3.0rc1-bin-windows-x86_64.zip
1ef517ba33e366167f9a225c6a6afcc4899d01cbd7853bd5852ac15ae81d5005  liquidctl-1.3.0rc1-py3-none-any.whl
15583d6ebecad722e1562164cef7097a358d6a57aa33a1a5e25741690548dbfa  liquidctl-1.3.0rc1.tar.gz
```


## [1.2.0] – 2019-09-27
_Summary for the 1.2.0 release: support for Asetek "5-th gen." 690LC coolers and improvements for HIDs and Mac OS._

Changelog since 1.2.0rc4:
### Changed
 - Include extended version information in pre-built executables for Windows
### Fixed
 - Improve handling of USB devices with no active configuration


## [1.2.0rc4] – 2019-09-18

Changelog since 1.2.0rc3:
### Added
 - Add support for adding git commit and tree cleanliness information to `--version`
 - Add support for adding distribution name and package information to `--version`
### Changed
 - [Corsair Asetek 690LC] Enable modern features for all Corsair coolers
 - Include version information in `--debug`
 - Make docs and code consistent on which devices are only experimentally supported
 - Revert "Mark Kraken X31, X41, X51 and X61 as no longer experimental"
 - Improve the documentation


## [1.2.0rc3] – 2019-09-15

Changelog since 1.2.0rc2:
### Added
 - Add experimental extra/liquiddump script
### Changed
 - Copy documentation for EVGA and Corsair 690LC coolers into the tree
 - [Corsair H115i] Use modern driver with fan profiles (see #41)
 - [All Asetek 690LC] Claim the interface proactively when starting a transaction (see #42)
### Fixed
 - [All Asetek 690LC] Rework USBXPRESS flow control to allow simultaneous reads from multiple processes (see #42)
 - [Legacy Asetek 690LC] Fix missing argument forwarding
 - Fix broken link to Mac OS example configuration


## [1.2.0rc2] – 2019-09-12

Changelog since 1.2.0rc1:
### Added
 - Support the EVGA CLC 360
 - Add `--alert-threshold` and `--alert-color`
### Changed
 - Mark Kraken X31, X41, X51 and X61 as no longer experimental
 - Improve supported devices list and links to documentation
 - Don't enable PyUSB tracing automatically with `--debug`
 - [Legacy Asetek 690LC] Cache values read from or stored on the filesystem
 - [Legacy Asetek 690LC] Prefer to save driver data in /run when OS is Linux
### Fixes
 - Force bundling of 'hid' module in Windows executable
 - [Legacy Asetek 690LC] Change default fading `--time-per-color` (see #29)


## [1.2.0rc1] – 2019-04-14

Changelog since 1.1.0:
### Added
 - Make automatic bundled builds for Windows with AppVeyor
 - [Smart Device/Grid+ V3] Add option to set all fans at once with virtual 'sync' channel
 - Add support for hidapi for HIDs
 - Support HIDs on Mac OS with hidapi
 - Add `--hid <module>` override for HID API selection
 - Add release number, bus and address listing
 - Add `--release`, `--bus`, `--address` device filters
 - Add `--time-per-color` and `--time-off` animation options
 - **Add driver for EVGA CLC 120 CL12, 240 and 280 coolers**
 - Add `--legacy-690lc` option for Asetek 690LC devices
 - **Add experimental legacy driver for NZXT Kraken X31, X41 and X61 coolers**
 - **Add experimental support of Corsair H80i v2, H100i v2 and H115i**
 - **Add experimental support of Corsair H80i GT, H100i GTX and H110i GTX**
 - Document possible support of NZXT Kraken X40 and X60 coolers
### Changed
 - [internal] Revamp driver and device model in `base.py` and `usb.py`
### Removed
 - Remove `--dry-run`


## [1.1.0] – 2018-12-15
_Summary for the 1.1.0 release: support for NZXT Smart Device, Grid+ V3 and Kraken M22._

Changelog since 1.1.0rc1:
### Added
 - Add proof of concept of software-based speed control
### Changed
 - Change Kraken M22 from experimental to implemented
 - Only show exception tracebacks if -g has been set
 - Improve the documentation
### Fixes
 - Fix: use correct exception (NotImplementedError)


## [1.1.0rc1] - 2018-11-14

Changelog since 1.0.0:
### Added
 - [Kraken] Add `super-breathing`, `super-wave` and `backwards-super-wave`
 - **Add driver for the NZXT Smart Device**
 - Add `initialize` command for the NZXT Smart Device, NZXT Grid+ V3 and similar products
 - Add device filtering options: `--vendor`, `--product`, `--usb-port` and `--serial`
 - Add `--debug` to complement `--verbose`
 - **Add experimental support for the NZXT Grid+ V3**
 - **Add experimental support for the NZXT Kraken M22**
 - [Kraken][API] Add `set_instantaneous_speed(channel, speed)`
 - [Kraken][API] Expose `supports_lighting`, `supports_cooling` and `supports_cooling_profiles` properties
 - Add proof of concept of status-duty translation
### Changed
 - [API] Improve the API for external code that uses our drivers
 - [API] Switch to the standard Python `logging` module
 - No longer imply `--verbose` from `--dry-run`
 - [Kraken] Lower the minimum pump duty to 50%
 - Improve the documentation
### Fixes
 - Fix standalone module entry point for the CLI
 - [Kraken] Fix fan and pump speed configuration on firmware v2.1.8 or older
### Deprecated
 - [Kraken] Deprecate `super`; use `super-fixed` instead
 - [Kraken] Deprecate undocumented API behavior of `initialize()` and `finalize()`; use `connect()` and `disconnect()` instead
### Removed
 - Remove unused symbols in `liquidctl.util`


## [1.0.0] - 2018-08-31
_Summary for the 1.0.0 release: support for NZXT Kraken X42/X52/X62/X72 coolers._

Changelog since 1.0.0rc1:
### Added
 - [Kraken] Add helper color mode: `off`
 - [Kraken] Add backward variant of `moving-alternating` color mode
### Changed
 - Improve the documentation
 - [Kraken] Allow covering marquees with only one color
### Fixes
 - Fix mentions to incorrect Kraken generation
 - [Kraken] Correct the modifier byte for the `moving-alternating` mode


## [1.0.0rc1] - 2018-08-26

### Added
 - **Add driver for NZXT Kraken X42, X52, X62 and X72 coolers**
