# Changelog

## [1.7.0] – 2021-07-06

### Added
 - Add initial experimental support for the Corsair Commander Core/iCUE Elite Capellix AIOs (PR #340)
 - Enable experimental support for Corsair Obsidian 1000D (#346)
 - Enable support for new variant of the NZXT Smart Device V2 (#338)
 - List experimental partial support for the NZXT Kraken Z53
 - Add machine readable output with `--json` (PR #314)
 - Add CONTRIBUTING.md and document our development process
### Changed
 - Change Grid+ V3/Smart Device (V1) status output (PR #326)
 - Change Commander Pro status/initialize output (PR #326)
 - Colorize the log output (new dependency: `colorlog`; PRs #318, #329)
 - Mark Kraken X31, X41, X61 as no longer experimental
 - Mark Vengeance RGB and DDR4 temperature sensors as no longer experimental
 - Mark Commander pro as no longer experimental
 - Mark NZXT E500, E650, E850 as no longer experimental
 - Change main branch name to "main"
 - Improve the documentation
### Fixed
 - Make `find_supported_devices()` account for `legacy_690lc` on Asetek 690LC drivers
 - Remove accidentally inherited `downgrade_to_legacy()` (unstable) from `Hydro690Lc`


## [1.6.1] – 2021-05-01
_Summary for the 1.6.1 release: one bug fix for HUE 2 controllers._

Changelog since 1.6.0:
### Fixed
 - Smart Device V2/HUE 2: check if fan controller before initializing fan reporting (#331)
### Checksums
```
e3b6aa5ae55204f8d9a8813105269df7dc8f80087670e3eac88b722949b3843f  dist/liquidctl-1.6.1.tar.gz
d14a32b7c0de5a2d25bc8280c32255da25e9bc32f103d099b678810a9a1b6c9c  dist/liquidctl-1.6.1-bin-windows-x86_64.zip
```


## [1.5.2] – 2021-05-01
_Summary for the 1.5.2 release: one bug fix for HUE 2 controllers._

Changelog since 1.5.1:
### Fixed
 - Smart Device V2/HUE 2: check if fan controller before initializing fan reporting (#331)
### Checksums
```
5738fda03f1d7bfb4416461a70351a5e040f1b57229674dd0f1f6f81d3750812  dist/liquidctl-1.5.2.tar.gz
```


## [1.6.0] – 2021-04-06
_Summary for the 1.6.0 release: support for Corsair Lighting Node Core, Hydro
H150i Pro XT, and all Hydro Pro coolers; estimate input power and efficiency
for Corsair HXi and RMi PSUS; enable support for ASUS Strix GTX 1070 and new
NZXT RGB & Fan Controller variant; formally deprecate `-d`/`--device`._

_Note for Linux package maintainers: the i2c-dev kernel module may now be
loaded automatically because of `extra/linux/71-liquidctl.rules`; this
substitutes the use of `extra/linux/modules-load.conf`, which has been
removed._

Changelog since 1.5.1:
### Added
 - Add experimental support for the Corsair Lighting Node Core
 - Add experimental support for the Corsair Hydro H150i Pro XT
 - Add experimental support for the Corsair Hydro H100i Pro, H115i Pro and H150i Pro coolers
 - Enable support for the ASUS Strix GTX 1070
 - Enable support for new variant of the NZXT RGB & Fan Controller
 - Add `sync` pseudo lighting channel to Commander/Lighting Node Pro devices
 - Add duty cycles to Hydro Platinum and Pro XT status output
 - Add input power and efficiency estimates to the status output of Corsair HXi and RMi PSUs
 - Add the Contributor Covenant, version 1.4 as our code of conduct 
### Changed
 - Remove `pro_xt_lighting` unsafe feature guard
 - Enforce correct casing of constants in driver APIs
 - Use udev rules for automatic loading of kernel modules (replaces previous `modules-load.d` configuration)
 - Remove warnings when reporting or setting the OCP mode of Corsair HXi and RMi PSUs
 - Rename Corsair HXi and RMi "Total power" status item to "Total power output"
 - Handle both US and UK spellings of `--direction` values
 - Improve the documentation
### Fixed
 - Replace "ID" with "#" when listing all devices
 - Add `keyval.load_store` method, atomic at the filesystem level
 - Add "Hydro" to Platinum and Pro XT device descriptions
### Removed
 - Remove modules-load configuration file for Linux (use the supplied udev rules instead)
 - [extra] remove `krakencurve-poc`, use `yoda` instead
### Deprecated
 - Deprecate `-d`/`--device`; prefer `--match` or other selection options
### Checksums
```
486dc366f10810a4efb301f3ceda10657a09937e9bc936cecec792ac26c2f186  dist/liquidctl-1.6.0.tar.gz
9b2e144c1fa63aaf41dc3d6a264b2e78e14a5f424b86e3a5f4b80396677000e6  dist/liquidctl-1.6.0-bin-windows-x86_64.zip
```


## [1.5.1] – 2021-02-19
_Summary for the 1.5.1 release: fixes to error reporting, handling of runtime
data, and other bugs._

Changelog since 1.5.0:
### Fixed
 - Handle corrupted runtime data (#278)
 - Fix item prefixes in list output when `--match` is passed
 - Remove caching of temporarily stored data
 - Append formated exception to "unknown error" messages
 - Only attempt to disconnect from a device if already connected
 - Only attempt to set the USB configuration if no other errors have been detected
 - Return the context manager when overriding `connect()`
 - Fix construction of fallback search paths for runtime data
### Checksums
```
e2d97be0319501bcad9af80c837abdbfd820620edcf9381068a443ad971327eb  liquidctl-1.5.1-bin-windows-x86_64.zip
9480e2dfbb0406fa8d57601a43a0f7c7573de1f5f24920b0e4000786ed236a8b  liquidctl-1.5.1.tar.gz
```


## [1.5.0] – 2021-01-27
_Summary for the 1.5.0 release: Corsair Commander Pro and Lighting Node Pro
support; EVGA GTX 1080 FTW and ASUS Strix RTX 2080 Ti OC support on Linux;
Corsair Vengeance RGB and TSE2004-compatible DDR4 modules support on Intel on
Linux; `--direction` flag, replacing previous "backwards-" modes; improved
error handling and reporting; new project home; other improvements and fixes._

_Note for Linux package maintainers: this release introduces a new dependency,
Python 'smbus' (from the i2c-tools project); additionally, since trying to
access I²C/SMBus devices without having the i2c-dev kernel module loaded will
result in errors, `extra/linux/modules-load.conf` is provided as a suggestion;
finally, `extra/linux/71-liquidctl.rules` will now (as provided) give
unprivileged access to i801_smbus adapters._

Changelog since 1.4.2:
### Added
 - Add SMBus and I²C support on Linux
 - Add support for EVGA GTX 1080 FTW on Linux
 - Add support for ASUS Strix RTX 2080 Ti OC on Linux
 - Add experimental support for DIMMs with TSE2004-compatible temperature sensors on Intel/Linux
 - Add experimental support for Corsair Vengeance RGB on Intel/Linux
 - Add experimental support for the Corsair Commander Pro
 - Add experimental support for the Corsair Lighting Node Pro
 - Add `--direction` modifier to animations
 - Add `--non-volatile` to control persistence of settings (NVIDIA GPUs)
 - Add `--start-led`, `--maximum-leds` and `--temperature-sensor` options (Corsair Commander/Lighting Node devices)
 - Add support for CSS-style hexadecimal triples
 - Implement the context manager protocol in the driver API
 - Export `find_liquidctl_devices` from the top-level `liquidctl` package
 - Add modules-load configuration file for Linux
 - Add completion script for bash
 - [extra] Add `LQiNFO.py` exporter (liquidctl -> HWiNFO)
 - [extra] Add `prometheus-liquidctl-exporter` exporter (liquidctl -> Prometheus)
### Changed
 - Move GitHub project into liquidctl organization
 - Improve error handling and reporting
 - Make vendor and product IDs optional in drivers
 - Mark Kraken X53, X63, X73 as no longer experimental
 - Mark NZXT RGB & Fan Controller as no longer experimental
 - Mark RGB Fusion 2.0 controllers as no longer experimental
 - Change casing of "PRO" device names to "Pro"
 - Improve the documentation
### Fixed
 - Fix potential exception when a release number is not available
 - Enforce USB port filters on HID devices
 - Fix backward `rainbow-pulse` mode on Kraken X3 devices
 - Fix compatibility with hidapi 0.10 and multi-usage devices (RGB Fusion 2.0 controllers)
 - Fix lighting settings in Platinum SE and Pro XT coolers
 - Generate and verify the checksums of zip and exe built on AppVeyor
### Deprecated
 - Deprecate `backwards-` pseudo modes; use `--direction=backward` instead
### Checksums
```
370eb9c662111b51465ac5e2649f7eaf423bd22799ef983c4957468e9d957c15  liquidctl-1.5.0-bin-windows-x86_64.zip
762561a8b491aa98f0ccbbab4f9770813a82cc7fd776fa4c21873b994d63e892  liquidctl-1.5.0.tar.gz
```


## [1.4.2] – 2020-11-01
_Summary for the 1.4.2 release: standardized hexadecimal parsing in the CLI;
fixes for Windows and mac OS; improvements to Hydro Platinum/Pro XT and Kraken
X3 drivers._

Changelog since 1.4.1:
### Added
 - Add `Modern690Lc.downgrade_to_legacy` (unstable API)
### Changed
 - Accept hexadecimal inputs regardless of a `0x` prefix
 - Warn on faulty temperature readings from Kraken X3 coolers
 - Warn on Hydro Platinum/Pro XT firmware versions that are may be too old
 - Update PyInstaller used for the Windows executable
 - Update PyUSB version bundled with the Windows executable
 - Improve the documentation
### Fixed
 - Fix data path on mac OS
 - Only set the sticky bit for data directories on Linux
 - Fix check of maximum number of colors in Hydro Platinum super-fixed mode
 - Fix HID writes to Corsair HXi/RMi power supplies on Windows
 - Ensure Hydro Platinum/Pro XT is in static LEDs hardware mode
### Checksums
```
83517ccb06cfdda556bc585a6a45edfcb5a21e38dbe270454ac97639d463e96d  dist/liquidctl-1.4.2-bin-windows-x86_64.zip
39da5f5bcae1cbd91e42e78fdb19f4f03b6c1a585addc0b268e0c468e76f1a3c  dist/liquidctl-1.4.2.tar.gz
```


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
 - Use a mocked device to test backward compatibility with liquidctl 1.1.0
### Checksums
```
895e55fd70e1fdfe3b2941d9139b91ffc4e902a469b077e810c35979dbe1cfdf  liquidctl-1.4.1-bin-windows-x86_64.zip
59a3bc65b3f3e71a5714224401fe6e95dfdee591a1d6f4392bc4e6d6ad72ff8d  liquidctl-1.4.1.tar.gz
```


## [1.4.0] – 2020-07-31
_Summary for the 1.4.0 release: fourth-generation NZXT Kraken coolers, Corsair
Platinum and Pro XT coolers, select Gigabyte RGB Fusion 2.0 motherboards,
additional color formats, improved fan and pump profiles in third-generation
Krakens, and other improvements._

Changelog since 1.3.3:
### Added
 - Add experimental support for NZXT Kraken X53, X63 and X73 coolers
 - Add experimental partial support for NZXT Kraken Z63 and Z73 coolers
 - Add experimental support for Corsair H100i, H100i SE and H115i Platinum coolers
 - Add experimental partial support for Corsair H100i and H115i Pro XT coolers
 - Add experimental support for Gigabyte motherboards with RGB Fusion 2.0 5702 and 8297 controllers
 - Enable experimental support for the NZXT RGB & Fan Controller
 - Add support for HSV, HSL and explicit RGB color representations
 - Add `sync` lighting channel to HUE 2 devices
 - Add tentative names for the different +12 V rails of NZXT E-series PSUs
 - Add +uaccess udev rules for Linux distributions and users
 - Add `--pump-mode` option to `initialize` (Corsair Platinum/Pro XT coolers)
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
 - Switch to a consistent module, driver and guide naming scheme (aliases are kept for backward compatibility)
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
