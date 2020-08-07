# Changelog

## [1.4.1] – 2020-08-07
_Summary for the 1.4.1 release: fix a regression with NZXT E-series PSUs, an
unreliable test case, and some ignored Hidapi errors; also make a few other
small improvements to the documentation and test suite._

Changelog since 1.4.0:
### Changed
 - Improve the documentation
 - Improve the test suite
### Fixed
 - Don't use report IDs when writing to NZXT E-series PSUs (#166)
 - Recognize and raise Hidapi write errors
 - Use a mocked device to test backwards compatibility with liquidctl 1.1.0


## [1.4.0] – 2020-07-31
_Summary for the 1.4.0 release: fourth-generation NZXT Kraken coolers, Corsair
Platinum and PRO XT coolers, select Gigabyte RGB Fusion 2.0 motherboards,
additional color formats, improved fan and pump profiles in third-generation
Krakens, and other improvements._

Changelog since 1.3.3:
### Added
 - Add experimental support for NZXT Kraken X53, X63 and X73 coolers
 - Add experimental partial support for NZXT Kraken Z63 and Z73 coolers
 - Add experimental support for Corsair H100i, H100i SE and H115i Platinum coolers
 - Add experimental partial support for Corsair H100i and H115i PRO XT coolers
 - Add experimental support for Gigabyte motherboards with RGB Fusion 2.0 5702 and 8297 controllers
 - Enable experimental support for the NZXT RGB & Fan Controller
 - Add support for HSV, HSL and explicit RGB color representations
 - Add `sync` lighting channel to HUE 2 devices
 - Add tentative names for the different +12 V rails of NZXT E-series PSUs
 - Add +uaccess udev rules for Linux distributions and users
 - Add `--pump-mode` option to `initialize` (Corsair Platinum/PRO XT coolers)
 - Add `--unsafe` option to enable additional bleeding-edge features
 - Add a test suite
 - [extra] Add more general `yoda` script for software-based fan/pump control (supersedes `krakencurve-poc`)
### Changed
 - Increase resolution of fan and pump profiles in Kraken X42/X52/X62/X72 coolers
 - Use hidapi to communicate with HIDs on Windows
 - Use specific errors when features are not supported by the device or the driver
 - Store runtime data on non-Linux systems in `~/Library/Caches` (macOS), `%TEMP%` (Windows) or `/tmp` (Unix)
 - Mark Corsair HXi/RMi PSUs as no longer experimental
 - Mark Smart Device V2 and HUE 2 controllers as no longer experimental
 - Switch to a consistent module, driver and guide naming scheme (aliases are kept for backwards compatibility)
 - Improve the documentation
 - [extra] Refresh `krakencurve-poc` syntax and sensor names, and get CPU temperature on macOS with iStats
### Fixed
 - Add missing identifiers for some HUE2 accessories (#95; #109)
 - Fix CAM-like decoding of firmware version in NZXT E-series PSUs (#46, comment)
 - Use a bitmask to select the lighting channel in HUE 2 devices (#109)
 - Close the underlying cython-hidapi `device`
 - Don't allow `HidapiDevice.clear_enqueued_reports` to block
 - Don't allow `HidapiDevice.address` to fail with non-Unicode paths
 - Store each runtime data value atomically
### Deprecated
 - Deprecate and ignore `--hid` override for API selection
### Removed
 - Remove the PyUsbHid device backend for HIDs
### Checksums
```
250b7665b19b0c5d9ae172cb162bc920734eba720f3e337eb84409077c582966  liquidctl-1.4.0-bin-windows-x86_64.zip
b35e6f297e67f9e145794bb57b88c626ef2bfd97e7fbb5b098f3dbf9ae11213e  liquidctl-1.4.0.tar.gz
```


## [1.3.3] – 2020-02-18
_Summary for the 1.3.3 release: fix possibly stale data with HIDs and other minor issues._

Changelog since 1.3.2:
### Fixed
 - Add missing identifiers for HUE+ accessories on HUE 2 channels
 - Forward hid argument from `UsbHidDriver.find_supported_devices`
 - Prevent reporting stale data during long lived connections to HIDs (#87)
### Checksums
```
1422a892f9c2c69f5949cd831083c6fef8f6a1f6e3215e90b696bfcd557924b4  liquidctl-1.3.3-bin-windows-x86_64.zip
d13180867e07420c5890fe1110e8f45fe343794549a9ed7d5e8e76663bc10c24  liquidctl-1.3.3.tar.gz
```


## [1.3.2] – 2019-12-11
_Summary for the 1.3.2 release: fix fan status reporting from Smart Device V2._

Changelog since 1.3.1:
### Fixed
 - Parse Smart Device V2 fan info from correct status message
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
 - Enable experimental support for the NZXT HUE 2
 - Enable experimental support for the NZXT HUE 2 Ambient
 - Add `-m, --match <substring>` to allow filtering devices by description
 - Add `-n` short alias for `--pick`
### Changed
 - Allow `initialize` methods to optionally return status tuples
 - Conform to XDG basedir spec and prefer `XDG_RUNTIME_DIR`
 - Improve directory names for internal data
 - Ship patched PyUSB and libusb 1.0.22 on Windows
 - Improve the documentation
### Fixed
 - Release the USB interface of NZXT E-series PSUs as soon as possible
 - Fix assertion in retry loops with NZXT E-series PSUs
 - Fix LED blinking when executing `status` on a Smart Device V2
 - Add missing identifier for 250 mm HUE 2 LED strips
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
 - Add experimental support for Corsair HX750i, HX850i, HX1000i and HX1200i power supplies
 - Add experimental support for Corsair RM650i, RM750i, RM850i and RM1000i power supplies
 - Add experimental support for NZXT E500, E650 and E850 power supplies
 - Add experimental support for the NZXT Smart Device V2
 - Add liquidctl(8) man page
 - Add `initialize all` variant/helper
 - Add `--pick <result>` device selection option
 - Add `--single-12v-ocp` option to `initialize` (Corsair HXi/RMi PSUs)
### Changed
 - Reduce the number of libusb and hidapi calls during device discovery
 - Improve the visual hierarchy of the output `list` and `status`
 - Allow `list --verbose` to run without root privileges (Linux) or special drivers (Windows)
 - Change the default API for HIDs on Linux to hidraw
 - Consider stable: Corsair H80i v2, H100i v2, H115i; NZXT Kraken X31, X41, X61; NZXT Grid+ V3
### Fixed
 - Don't try to reattach the kernel driver more than once
 - Fixed Corsair H80i GT device name throughout the program
 - Fixed Corsair H100i GT device name in listing
### Deprecated
 - Use `liquidctl.driver.find_liquidctl_devices` instead of `liquidctl.cli.find_all_supported_devices`
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
 - Enable modern features for all Asetek 690LC coolers from Corsair
 - Include version information in `--debug`
 - Make docs and code consistent on which devices are only experimentally supported
 - Revert "Mark Kraken X31, X41, X51 and X61 as no longer experimental"
 - Improve the documentation


## [1.2.0rc3] – 2019-09-15

Changelog since 1.2.0rc2:
### Added
 - [extra] Add experimental `liquiddump` script
### Changed
 - Copy documentation for EVGA and Corsair 690LC coolers into the tree
 - Use modern driver with fan profiles for Corsair H115i (#41)
 - Claim the interface proactively when starting a transaction on any Asetek 690LC (#42)
### Fixed
 - Rework USBXPRESS flow control in Asetek 690LC devices to allow simultaneous reads from multiple processes (#42)
 - Fix missing argument forwarding to legacy Asetek 690LC coolers
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
 - Cache values read from or stored on the filesystem
 - Prefer to save driver data in /run when OS is Linux
### Fixes
 - Force bundling of `hid` module in Windows executable
 - Change default Asetek 690LC `--time-per-color` for fading mode (#29)


## [1.2.0rc1] – 2019-04-14

Changelog since 1.1.0:
### Added
 - Add support for EVGA CLC 120 CL12, 240 and 280 coolers
 - Add experimental support for NZXT Kraken X31, X41 and X61 coolers
 - Add experimental support for Corsair H80i v2, H100i v2 and H115i
 - Add experimental support for Corsair H80i GT, H100i GTX and H110i GTX
 - Add support for macOS
 - Make automatic bundled builds for Windows with AppVeyor
 - Add support for hidapi for HIDs (default/required on macOS)
 - Add release number, bus and address listing
 - Add `sync` pseudo channel for setting all Smart Device/Grid+ V3 fans at once
 - Add `--hid <module>` override for HID API selection
 - Add `--release`, `--bus`, `--address` device filters
 - Add `--time-per-color` and `--time-off` animation options
 - Add `--legacy-690lc` option for Asetek 690LC devices
 - Document possible support of NZXT Kraken X40 and X60 coolers
### Changed
 - Revamp driver and device model in `liquidctl.driver.{base,usb}` modules
### Removed
 - Remove `--dry-run`


## [1.1.0] – 2018-12-15
_Summary for the 1.1.0 release: support for NZXT Smart Device, Grid+ V3 and Kraken M22._

Changelog since 1.1.0rc1:
### Added
 - [extra] Add proof of concept `krakencurve-poc` script for software-based speed control
### Changed
 - Change Kraken M22 from experimental to implemented
 - Only show exception tracebacks if -g has been set
 - Improve the documentation
### Fixes
 - Use standard NotImplementedError exception


## [1.1.0rc1] - 2018-11-14

Changelog since 1.0.0:
### Added
 - Add support for the NZXT Smart Device
 - Add experimental support for the NZXT Grid+ V3
 - Add experimental support for the NZXT Kraken M22
 - Add `initialize` command for the NZXT Smart Device, NZXT Grid+ V3 and similar products
 - Add device filtering options: `--vendor`, `--product`, `--usb-port` and `--serial`
 - Add `super-breathing`, `super-wave` and `backwards-super-wave` modes for Krakens
 - Add `--debug` to complement `--verbose`
 - Add special Kraken `set_instantaneous_speed(channel, speed)` API
 - Expose Kraken `supports_lighting`, `supports_cooling` and `supports_cooling_profiles` properties
 - [extra] Add proof of concept `krakenduty-poc` script for status-duty translation
### Changed
 - Lower the minimum pump duty to 50%
 - No longer imply `--verbose` from `--dry-run`
 - Improve the API for external code that uses our drivers
 - Switch to the standard Python `logging` module
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
 - Add helper color mode: `off`
 - Add backward variant of `moving-alternating` color mode
### Changed
 - Improve the documentation
 - Allow covering marquees with only one color
### Fixes
 - Fix mentions to incorrect Kraken generation
 - Correct the modifier byte for the `moving-alternating` mode


## [1.0.0rc1] - 2018-08-26

### Added
 - Add driver for NZXT Kraken X42, X52, X62 and X72 coolers


## About the changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html) and [PEP 404](https://www.python.org/dev/peps/pep-0440/#semantic-versioning).
