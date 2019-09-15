# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html), using version identifiers translated to [PEP 404](https://www.python.org/dev/peps/pep-0440/#semantic-versioning)-compatible equivalents.

## [1.2.0rc3] – 2019-09-15
### Added
 - Add experimental extra/liquiddump scrip
### Changed
 - Copy documentation for EVGA and Corsair 690LC coolers into the tree
 - [Corsair H115i] Use modern driver with fan profiles (see #41)
 - [All Asetek 690LC] Claim the interface proactively when starting a transaction (see #42)
### Fixed
 - [All Asetek 690LC] Rework USBXPRESS flow control to allow simultaneous reads from multiple processes (see #42)
 - [Legacy Asetek 690LC] Fix missing argument forwarding
 - Fix broken link to Mac OS example configuration

## [1.2.0rc2] – 2019-09-12
### Added
 - Support the EVGA CLC 360
 - Add --alert-threshold and --alert-color
### Changed
 - Mark Kraken X31, X41, X51 and X61 as no longer experimental
 - Improve supported devices list and links to documentation
 - Don't enable PyUSB tracing automatically with --debug
 - [Legacy Asetek 690LC] Cache values read from or stored on the filesystem
 - [Legacy Asetek 690LC] Prefer to save driver data in /run when OS is Linux
### Fixes
 - Force bundling of 'hid' module in Windows executable
 - [Legacy Asetek 690LC] Change default fading --time-per-color (see #29)

## [1.2.0rc1] – 2019-04-14
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
 - **Add experimental support of Corsair H80i GTX, H100i GTX and H110i GTX**
 - Document possible support of NZXT Kraken X40 and X60 coolers
### Changed
 - [internal] Revamp driver and device model in `base.py` and `usb.py`
### Removed
 - Remove `--dry-run`

## [1.1.0] – 2018-12-15
### Added
 - Add proof of concept of software-based speed control
### Changed
 - Change Kraken M22 from experimental to implemented
 - Only show exception tracebacks if -g has been set
 - Improve the documentation
### Fixes
 - Fix: use correct exception (NotImplementedError)

## [1.1.0rc1] - 2018-11-14
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

