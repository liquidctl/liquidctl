# Release checklist

## Prepare system

 - [ ] Install publishing dependencies: `pip install --upgrade setuptools twine`

## Prepare repository

 - [ ] Update liquidctl/version.py
 - [ ] Update the man page last update date
 - [ ] Make sure the CHANGELOG is up to date
 - [ ] Update the link in the README to the stable executable for Windows
 - [ ] Commit "Prepare for release v<version>"

## Test

 - [ ] Run `extra/tests/v1.0.0-compatibility`
 - [ ] Run `extra/tests/asetek_*`
 - [ ] Run `extra/tests/kraken_two` and `EXTRAOPTIONS='--hid usb' extra/tests/kraken_two`
 - [ ] Run `extra/krakenduty-poc status`
 - [ ] Run `extra/krakencurve-poc control --use-psutil --fan-sensor 'coretemp:Package id 0' '(25,50),(35,100)' '(25,35),(35,60),(60,100)' --verbose`
 - [ ] Run `extra/liquiddump | jq -c .`
 - [ ] Test krakenx (git): `colctl --mode fading --color_count 2 --color0 192,32,64 --color1 246,11,21 --fan_speed "(30, 100), (40, 100)" --pump_speed "(30, 100), (40, 100)"`

## Package

 - [ ] Tag HEAD as `v<version>` with short summary annotation
 - [ ] Rebuild: `python setup.py build`
 - [ ] Make sure `liquidctl/extraversion.py` makes sense
 - [ ] Generate the source distribution: `python setup.py sdist`
 - [ ] Check that all necessary files are in `dist/liquidctl-<version>.tar.gz`
 - [ ] Push HEAD and v<version> tag
 - [ ] Check all CI statuses (doctests, flake8 linting and Windows build)

## Package tests: ArchLinux

 - [ ] Update and build python-liquidctl-rc from `local://<...>/liquidctl/dist/liquidctl-<version>tar.gz`
 - [ ] Test my personal setup: `liquidcfg`
 - [ ] Test again with `--hid usb`: `EXTRAOPTIONS='--hid usb' liquidcfg`

## Package tests: Windows

 - [ ] Test AppVeyor build of v<version> on fresh Windows VM
 - [ ] Test AppVeyor build of v<version> on my Windows system (version, status, and my custom setup)

## Release

 - [ ] Upload: `twine upload dist/liquidctl-<version>.tar.gz`
 - [ ] Upgrade the v<version> tag on GitHub to a release
 - [ ] Update the changelog with sha256sums

## Post release

 - [ ] Update AUR python-liquidctl-rc and python-liquidctl-git
 - [ ] Open PR for python-liquidctl (if it's stable release)
 - [ ] Update jonasmalacofilho/homebrew-liquidctl
