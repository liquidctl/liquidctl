# Changelog

## [1.14.0] – 2025-01-01

### Changes since 1.13.0

Added:

- Support for Corsair Hydro H110i GT (liquidctl#637)
- Support for Corsair iCue Elite H100i RGB, white version (liquidctl#735)
- Support for Corsair iCue Elite H115i RGB (liquidctl#678)
- Support for Corsair iCue Elite H150i RGB, white version (liquidctl#725)
- Support for Kraken 2023 standard and Elite models (liquidctl#605)
- Support for MSI MPG Coreliquid K360 and two similar variants (liquidctl#564)
- Support for NZXT RGB & Fan Controller with PID `201f` (liquidctl#733)
- Support for NZXT RGB & Fan Controller with PID `2020` (liquidctl@a64e73e63eb3)
- Support the ASUS Ryujin II 360, minus the screen (liquidctl#653)
- Corsair Commander Core: partial/experimental support for speed profiles (liquidctl#687)

Changed:

- Corsair RMi/HXi PSUs: enforce a 30% minimum value for user-set fan duties (liquidctl#730)
- NZXT Kraken Z?3/2023: error out when trying to set the screen is unsupported due to firmware v2.x
- extra scripts: add `.py` extension to all scripts written in Python
- extra/yoda: make `psutil` dependency optional

Deprecated:

- `experimental` fields in the `list --json` output

Removed:

- "Experimental" tags, notes and suffixes

Fixed:

- Corsair HX1000i/HX1500i: fix input power curves (liquidctl#675)
- NZXT Kraken Z?3/2023: partially support setting the screen with firmware v2.x (liquidctl#692)
- Linux: skip unreadable EEPROMs (liquidctl#731)
- Windows: replace port numbers with bus address when setting a storage key (liquidctl#703)
- extra/yoda: accept `--unsafe` flags
- extra/yoda: output CPU frequency with the correct unit of MHz
- Convert `PyUsbDevice` addresses to strings (liquidctl#743)
- Various issues with Unix file permission handling in `liquidctl.keyval` (liquidctl#659)


## [1.13.0] – 2023-07-26

### Changes since 1.12.1

Added:

- Corsair Hydro Elite RGB: add support for H100i and H150i Elite RGB (liquidctl#556, PR liquidctl#557, PR liquidctl#559)

Changed:

- NZXT H1 V2: no longer experimental
- Aura LED motherboards: no longer experimental

Fixed:

- Corsair HXi (2022): read exactly 4 bytes for timedeltas (liquidctl#575)
- Corsair Commander Pro: fix `fan_mode` (liquidctl#615, PR liquidctl#616)
- Python 3.11: fix deprecation on `locale.getDefaultLocale`
- Python 3.11.4: fix exception handling when parsing null bytes in persisted data

### Checksums

```
ee17241689c0bf3de43cf4d97822e344f5b57513d16dd160e37fa0e389a158c7  dist/liquidctl-1.13.0.tar.gz
405a55d531022082087c97ed8f4cc315b25493ad22be88ca8bd6852d49621a47  dist/liquidctl-1.13.0-py3-none-any.whl
```

*Five years ago I started liquidctl. One month after that, v1.0.0rc1 was tagged with support for the first devices.*


## [1.12.1] – 2023-01-14

### Changes since 1.12.0

Fixed:

- Corsair HXi and RMi: check that the response matches the command that was sent (liquidctl#463)

### Checksums

```
3f98b8400c9cd3e47925cafbe34b9d7a51705bf85ce1ec8d95d107a360f6f29e  dist/liquidctl-1.12.1.tar.gz
9e13d36bd9fa439ec244ea89f52ad080776406129d35db940a8343352e42dea7  dist/liquidctl-1.12.1-py3-none-any.whl
```


## [1.12.0] – 2023-01-08

### Changes since 1.11.1

Added:

- Aquacomputer D5 Next: add support for reading virtual temp sensors (PR liquidctl#510)
- Aquacomputer Octo: add support for reading virtual temp sensors (PR liquidctl#525)
- Aquacomputer Farbwerk 360: add support for reading virtual temp sensors (PR liquidctl#527)
- Aquacomputer Quadro: add support for reading virtual temp sensors (PR liquidctl#528)
- Commander Pro: add support for changing fan modes during initialization (liquidctl#472, PR liquidctl#474)
- Corsair HXi and RMi: add support for HX1500i and 2022's re-issue HX1000i PSUs
- Corsair Commander ST: extend experimental Commander Core monitoring and fan control support to the Commander ST (liquidctl#511)
- NZXT Kraken X3/Z3: add support for expanded HWMON driver capabilities (PR liquidctl#529)
- NZXT RGB & Fan Controller: add experimental support for 2022's 3+6-channel `1e71:2011` variant (liquidctl#541)
- NZXT HUE2: add accessory IDs for F120/F140 RGB fans

Changed:

- Corsair Hydro Pro: move firmware version to initialize output
- NZXT Kraken Z3: use updated winusbcdc (PR liquidctl#535)
- NZXT RGB & Fan Controller: downgrade 3+6-channel `1e71:2019` variant to experimental (liquidctl#541)
- NZXT RGB & Fan Controller: disable broken lighting support on 3+6-channel controllers (liquidctl#541)

Fixed:

- CLI: remove occasional newline when logging `sys.version`
- Corsair Hydro Pro: reduce expectations on `_CMD_READ_FAN_SPEED` responses (liquidctl#536)

Removed:

- CLI: remove long deprecated --hid option

### Checksums

```
639e62d8845cd8d3718941e7894865f9c06abfc2826546606335e30f607d6fc3  dist/liquidctl-1.12.0.tar.gz
748e7c9d49f06f885cc191278c0aa3b5da5f7623edd7f4c12a99f52b72b1cad6  dist/liquidctl-1.12.0-py3-none-any.whl
```


## [1.11.1] – 2022-10-19

### Changes since 1.11.0

Fixed:

- USB and HID: increase default timeout to 5s (liquidctl#526)

### Notes for downstream packagers

See notes for 1.11.0 release.

### Checksums

```
278c1aca8d891bfe8e0c164dfe6651261a0423b29f9c24cef060c3613f2a4fd7  dist/liquidctl-1.11.1.tar.gz
629d6e7db0eab3d6e7d0a58c23be6765d169eb2c1d29ddaef2fde60c603429e9  dist/liquidctl-1.11.1-py3-none-any.whl
```


## [1.11.0] – 2022-10-16

### Changes since 1.10.0

Added:

- Corsair Commander Core: extend experimental monitoring and fan control
  support to the Commander Core XT (PR liquidctl#478)
- Aquacomputer D5 Next: add experimental monitoring and pump/fan control
  support (PR liquidctl#482, PR liquidctl#489, PR liquidctl#499)
- Aquacomputer Farbwerk 360: add experimental monitoring support (PR
  liquidctl#491)
- Aquacomputer Octo: add experimental monitoring and fan control support (PR
  liquidctl#492, PR liquidctl#508)
- Aquacomputer Quadro: add experimental monitoring and fan control support (PR
  liquidctl#493, PR liquidctl#509)
- NZXT Kraken Z3: add experimental LCD screen support (PR liquidctl#479)
- NZXT Kraken X3: support new USB PID (liquidctl#503)
- NZXT RGB & Fan Controller: support new USB PID (liquidctl#485)

Changed:

- ASUS Aura LED: refer to as ASUS instead of AsusTek
- Corsair RMi/HXi: rename temperature sensors according to their location
- NZXT Kraken X40/X60: document that alerts are not supported (liquidctl#477)

Fixed:

- HWMON: fix Python<3.9 compatibility (PR liquidctl#483)
- Corsair Hydro Pro: fix duplicate use of second alert temperature (PR
  liquidctl#484)
- HWMON: support builtin drivers and log driver instead of module name
  (liquidctl#502)
- Corsair Commander Core: support 2.10.219 firmware (PR liquidctl#501, PR
  liquidctl#513)
- USB devices: add default timeouts to all IO methods (liquidctl#488)
- USB HIDs: add default timeouts to compatible IO methods (liquidctl#488)

Removed:

- API: make `UsbDriver.SUPPORTED_DEVICES` private

### Notes for downstream packagers

New Python dependencies: [crcmod], [pillow] and (Windows-only:) [winusbcdc].

[crcmod]: https://pypi.org/project/crcmod/
[pillow]: https://pypi.org/project/Pillow/
[winusbcdc]: https://pypi.org/project/WinUsbCDC/

### Checksums

```
a3b53e317ba9211e05be88d9158efdc02c51ae067ee974d3d9f0b79716cf7ba3  dist/liquidctl-1.11.0.tar.gz
0c59dac7bdc09d7a16da410060154dca86258d989308034a919242a4739ca8f3  dist/liquidctl-1.11.0-py3-none-any.whl
```

*In memory of Lucinda Alves Silva Malaco (1924–2021) and Peter Eckersley
(1979–2022).*


## [1.10.0] – 2022-07-03

### Changes since 1.9.1

Added:

- Add experimental support for NZXT H1 V2 case Smart Device (PR liquidctl#451)
- Add experimental driver for Asus Aura LED USB controllers (PR liquidctl#456)

Changed:

- Hydro Platinum/Pro XT: only compute packets that will be sent
- Kraken X2: report modern firmware versions in simplified form
- Smart Device (V1)/Grid+ V3: report firmware version in simplified form
- Debug: make it clear when a device is identified
- Nvidia: promote all supported cards to stable status

Fixed:

- Skip `keyval` unit test on Windows when lacking sufficient permissions to
  create symlinks (liquidctl#460)

Removed:

- API: remove deprecated firmware version from the output of
  `KrakenX2.get_status()`

### Checksums

```
f9dc1dacaf1d3a44b80000baac490b44c5fa7443159bd8d2ef4dbb1af49cc7ba  dist/liquidctl-1.10.0.tar.gz
acc65602e598dabca94f91b067ac7ad7f4d2920653b91d694ad421be6eaef172  dist/liquidctl-1.10.0-py3-none-any.whl
```


## [1.9.1] – 2022-04-05

### Changes since 1.9.0

Fixed:
- Remove excess `_input` suffix when reading `pwmN` attributes from hwmon
  (liquidctl#445, PR liquidctl#446)

### Notes for downstream packagers

Starting with 1.9.0, liquidctl now uses a PEP 517 build.  See the notes for the
1.9.0 release for more information.

### Checksums

```
b4467e842d9a6adc804317a991354db041417f4f7dcf7d76799f2b1593ed1276  dist/liquidctl-1.9.1.tar.gz
a23312c07b1ceec850e7739a2428e9fc47c95cd0650269653a9e726d53c12057  dist/liquidctl-1.9.1-py3-none-any.whl
```


## [1.9.0] – 2022-04-05

### Changes since 1.8.1

Added:
- Add support for persisting settings on modern Asetek 690LC coolers
  (liquidctl#355)
- Add support for setting fixed fan/pump speeds on the Corsair Commander Core
  (PR liquidctl#405)
- Identify some devices with a matching Linux hwmon device (liquidctl#403, PR
  liquidctl#429)
- Add `--direct-access` to force it in spite of the presence of kernel drivers
  (liquidctl#403, PR liquidctl#429)
- Add security policy: `SECURITY.md`
- Enable experimental support for EVGA GTX 1070 and 1070 Ti cards using the
  existing `EvgaPascal` driver:
    - EVGA GTX 1070 FTW \[DT Gaming|Hybrid\]
    - EVGA GTX 1070 Ti FTW2
- Enable experimental support for various ASUS GTX and RTX cards using the
  existing `RogTuring` driver:
    - ASUS Strix GTX 1050 OC
    - ASUS Strix GTX 1050 Ti OC
    - ASUS Strix GTX 1060 \[OC\] 6GB
    - ASUS Strix GTX 1070
    - ASUS Strix GTX 1070 Ti \[Advanced\]
    - ASUS Strix GTX 1080 \[Advanced|OC\]
    - ASUS Strix GTX 1080 Ti \[OC\]
    - ASUS Strix GTX 1650 Super OC
    - ASUS Strix GTX 1660 Super OC
    - ASUS Strix GTX 1660 Ti OC
    - ASUS Strix RTX 2060 \<Evo|Evo OC|OC\>
    - ASUS Strix RTX 2060 Super \[Advanced|Evo Advanced|OC\]
    - ASUS Strix RTX 2070 \[Advanced|OC\]
    - ASUS Strix RTX 2070 Super \<Advanced|OC\>
    - ASUS Strix RTX 2080 OC
    - ASUS Strix RTX 2080 Super \<Advanced|OC\>
    - ASUS Strix RTX 2080 Ti
    - ASUS TUF RTX 3060 Ti OC
- API: add `liquidctl.__version__`
- extra/contrib: add script for n-color RGB Fusion 2.0 color cycling (PR
  liquidctl#424, PR liquidctl#426)

Changed:
- Log the Python interpreter version
- If possible, log the version of all Python requirements
- Move reporting of Kraken X2 firmware version to initialization
- Move reporting of Smart Device V1/Grid+ V3 firmware version and accessories
  to initialization (PR liquidctl#429)
- Don't re-initialize devices with a Linux hwmon driver (liquidctl#403, PR
  liquidctl#429)
- If possible, read status from Linux hwmon (liquidctl#403, PR liquidctl#429)
- Switch to a PEP 517 build (liquidctl#430, PR liquidctl#431)
- Replace ah-hoc version management with `setuptools_scm` (liquidctl#430, PR
  liquidctl#431)
- Allow directly invoking the CLI with `python -m liquidctl`
- Windows: provide libsub-1.0.dll automatically with `libusb-package`
- API: improve and clarify the documentation of `BaseDriver` methods
- API: rename `CorsairAsetekProDriver` to `HydroPro`

Deprecated:
- Deprecate directly invoking the CLI with `python -m liquidctl.cli` (use
  `python -m liquidctl`)
- API: deprecate including the firmware version in the output from
  `KrakenX2.get_status()` (read it from `.initialize()`)
- API: deprecate `CorsairAsetekProDriver` alias (use `HydroPro`)

Removed:
- API: remove long deprecated support for connecting to Kraken X2 devices with
  `KrakenX2.initialize()` (use standardized `.connect()`)
- API: remove long deprecated support for disconnecting from Kraken X2 devices
  with `KrakenX2.finalize()` (use standardized `.disconnect()`)
- API: remove long deprecated `<device>.find_all_supported_devices()` (use
  `liquidctl.find_liquidctl_devices()` or `<device>.find_supported_devices()`)

Fixed:
- Let all unexpected SMBus exceptions bubble up (liquidctl#416)
- Reset Kraken X2 fan and pump profiles during initialization (possibly related
  to liquidctl#395)
- Remove redundant prefix from CLI error messages

### Notes for downstream packagers

liquidctl now uses a PEP 517 build: [PyPA/build] and [PyPA/installer] are
suggested for a typical downstream package build process:

```bash
# build
python -m build --wheel [--no-isolation]

# install
python -m installer --destdir=<dest> dist/*.whl
```

Additionally, liquidctl has switched from an ad-hoc solution to version
management to [setuptools_scm].  If the git tags aren't available,
setuptools_scm supports environment variables to externally inject the version
number.

```bash
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_LIQUIDCTL=1.9.0
python -m build [args]
python -m installer [args]
```

[PyPA/build]: https://github.com/pypa/build
[PyPA/installer]: https://github.com/pypa/installer
[setuptools_scm]: https://github.com/pypa/setuptools_scm

### Checksums

```
9e1ae595be2c3ea5899e12741c11307da27e86bc88f7f93c5ae40bb2aa03dc70  dist/liquidctl-1.9.0.tar.gz
3820c29c0fc86bd6bd601d55a593f1cd476cd563875b45488bef26fc272abf6d  dist/liquidctl-1.9.0-py3-none-any.whl
```


## [1.8.1] – 2022-01-21

### Changes since 1.8.0

Fixed:
- Strip non-determinism from sdist/egg SOURCES.txt metadata

### Checksums

```
0859dfe673babe9af10e4f431e0baa974961f0b2c973a37e64eb6c6c2fddbe73  dist/liquidctl-1.8.1.tar.gz
```


## [1.8.0] – 2022-01-06

### Changes since 1.7.2

Added:
- Add support for the Corsair Hydro H60i Pro XT

Changed:
- Support for Corsair Hydro Pro coolers is no longer considered experimental
- Support for Corsair Hydro Platinum and Pro XT coolers is no longer considered
  experimental
- Support for Corsair Hydro Pro XT coolers is no longer considered experimental
- Support for NZXT Kraken Z coolers remains incomplete (no support for the LCD
  screen), but is no longer considered experimental
- Support for Corsair Lighting Node Core and Lighting Node Pro controllers is
  no longer considered experimental
- Support for the Corsair Obsidian 1000D case is no longer considered
  experimental

Fixed:
- Read DDR4 temperature sensor by word instead of with SMBus Block Read
  (liquidctl#400)
- Fix tolerant handling of single channel name in Corsair Lighting Node Core

### Checksums

```
99b8ec4da617a01830951a8f1a37d616f50eed6d260220fe5c26d1bf90e1e91e  dist/liquidctl-1.8.0.tar.gz
```


## [1.7.2] – 2021-10-05

Changelog since 1.7.1:
### Added
 - Enable support for new variant of the NZXT Smart Device V2 (PR liquidctl#364)
### Changed
 - Default `--maximum-leds` to the maximum possible number of LEDs (liquidctl#367, PR liquidctl#368)
### Fixed
 - Fix moving flag in SD2/HUE2 `alternating` modes (liquidctl#385)
### Checksums
```
b2337e0ca3bd36de1cbf581510aacfe23183d7bb176ad0dd43904be213583de3  dist/liquidctl-1.7.2.tar.gz
```


## [1.7.1] – 2021-07-16
_Summary for the 1.7.1 release: fix a bug when colorizing the log output._

Changelog since 1.7.0:
### Fixed
 - Fix `KeyError` when logging due to colorlog<6
 - Swap DEBUG and INFO level colors
### Checksums
```
10f650b9486ddac184330940550433685ae0abc70b66fe92d994042491aab356  dist/liquidctl-1.7.1.tar.gz
5f35d4ac8ad6da374877d17c7a36bbb202b0a74bd773ebe45444f0089daba27b  dist/liquidctl-1.7.1-bin-windows-x86_64.zip
```


## [1.7.0] – 2021-07-06
_Summary for the 1.7.0 release: support for Commander Core/Capellix, Obsidian
1000D, new Smart Device V2 variant; `--json` output; improvements in
initialize/status output; colorize the log output._

Changelog since 1.6.1:
### Added
 - Add initial experimental support for the Corsair Commander Core/iCUE Elite Capellix AIOs (PR liquidctl#340)
 - Enable experimental support for Corsair Obsidian 1000D (liquidctl#346)
 - Enable support for new variant of the NZXT Smart Device V2 (liquidctl#338)
 - List experimental partial support for the NZXT Kraken Z53
 - Add machine readable output with `--json` (PR liquidctl#314)
 - Add CONTRIBUTING.md and document our development process
### Changed
 - Change Grid+ V3/Smart Device (V1) status output (PR liquidctl#326)
 - Change Commander Pro status/initialize output (PR liquidctl#326)
 - Colorize the log output (new dependency: `colorlog`; PRs liquidctl#318, liquidctl#329)
 - Mark Kraken X31, X41, X61 as no longer experimental
 - Mark Vengeance RGB and DDR4 temperature sensors as no longer experimental
 - Mark Commander pro as no longer experimental
 - Mark NZXT E500, E650, E850 as no longer experimental
 - Change main branch name to "main"
 - Improve the documentation
### Fixed
 - Make `find_supported_devices()` account for `legacy_690lc` on Asetek 690LC drivers
 - Remove accidentally inherited `downgrade_to_legacy()` (unstable) from `Hydro690Lc`
### Checksums
```
053675aca9ba9a3c14d8ef24d1a2e75c592c55a1b8ba494447bc13d3ae523d6f  dist/liquidctl-1.7.0.tar.gz
d0f8f24961a22c7664c330d286e1c63d4df753d5fbe21ac77eb6488b27508751  dist/liquidctl-1.7.0-bin-windows-x86_64.zip
```


## [1.6.1] – 2021-05-01
_Summary for the 1.6.1 release: one bug fix for HUE 2 controllers._

Changelog since 1.6.0:
### Fixed
 - Smart Device V2/HUE 2: check if fan controller before initializing fan reporting (liquidctl#331)
### Checksums
```
e3b6aa5ae55204f8d9a8813105269df7dc8f80087670e3eac88b722949b3843f  dist/liquidctl-1.6.1.tar.gz
d14a32b7c0de5a2d25bc8280c32255da25e9bc32f103d099b678810a9a1b6c9c  dist/liquidctl-1.6.1-bin-windows-x86_64.zip
```


## [1.5.2] – 2021-05-01
_Summary for the 1.5.2 release: one bug fix for HUE 2 controllers._

Changelog since 1.5.1:
### Fixed
 - Smart Device V2/HUE 2: check if fan controller before initializing fan reporting (liquidctl#331)
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
 - Handle corrupted runtime data (liquidctl#278)
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
 - Don't use report IDs when writing to NZXT E-series PSUs (liquidctl#166)
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
 - Add missing identifiers for some HUE2 accessories (liquidctl#95; liquidctl#109)
 - Fix CAM-like decoding of firmware version in NZXT E-series PSUs (liquidctl#46, comment)
 - Use a bitmask to select the lighting channel in HUE 2 devices (liquidctl#109)
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
 - Prevent reporting stale data during long lived connections to HIDs (liquidctl#87)
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
 - Use modern driver with fan profiles for Corsair H115i (liquidctl#41)
 - Claim the interface proactively when starting a transaction on any Asetek 690LC (liquidctl#42)
### Fixed
 - Rework USBXPRESS flow control in Asetek 690LC devices to allow simultaneous reads from multiple processes (liquidctl#42)
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
 - Change default Asetek 690LC `--time-per-color` for fading mode (liquidctl#29)


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
