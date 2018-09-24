# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html), using version identifiers translated to [PEP 404](https://www.python.org/dev/peps/pep-0440/#semantic-versioning)-compatible equivalents.

## [Unreleased]
### Added
 - **Add driver for the NZXT Smart Device**
 - [Kraken] Add `super-breathing`, `super-wave` and `backwards-super-wave`
 - Add `initialize` command for products like the NZXT Smart Device
 - Add device filtering options: `--vendor`, `--product`, `--usb-port` and
   `--serial`
 - Add `--debug` to complement `--verbose`
### Changed
 - No longer imply `--verbose` from `--dry-run`
 - Improve the API for external code that uses our drivers
### Deprecated
 - [Kraken] Deprecate `super`; use `super-fixed` instead
 - [Kraken] Deprecate undocumented API behavior of `initialize()` and
   `finalize()`; use `connect()` and `disconnect()` instead
### Removed
 - Remove no longer used symbols in `liquidctl.util`

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

