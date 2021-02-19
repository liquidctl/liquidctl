# Release checklist

## Prepare system

 - [ ] Install publishing dependencies: twine

## Prepare repository

 - [ ] Update liquidctl/version.py
 - [ ] Update last update data in the man page
 - [ ] Make sure the CHANGELOG is up to date
 - [ ] Update the link in the README to the stable executable for Windows
 - [ ] Remove "U/Starting with upcoming..." notes from the table of supported devices
 - [ ] Commit "release: prepare for v<version>"

## Test

With `"$(liquidctl --version) = "liquidclt v<version>"`:

 - [ ] Run unit and doc tests: `pytest`
 - [ ] Run my setup scripts: `liquidcfg && liquiddyncfg`
 - [ ] Run old HW tests: `extra/old-tests/asetek_*` and `extra/old-tests/kraken_two`
 - [ ] Test krakenduty: `extra/krakenduty-poc train && extra/krakenduty-poc status`
 - [ ] Test krakencurve: `extra/krakencurve-poc control --fan-sensor coretemp.package_id_0 --pump '(25,50),(35,100)' --fan '(25,35),(35,60),(60,100)' --verbose`
 - [ ] Test yoda: `extra/yoda --match kraken control pump with '(20,50),(50,100)' on coretemp.package_id_0 and fan with '(20,25),(34,100)' on _internal.liquid --verbose`
 - [ ] Test liquiddump: `extra/liquiddump | jq -c .`
 - [ ] Test krakenx (git): `colctl --mode fading --color_count 2 --color0 192,32,64 --color1 246,11,21 --fan_speed "(30, 100), (40, 100)" --pump_speed "(30, 100), (40, 100)"`

## Source distribution

 - [ ] Tag HEAD with `git tag -as v<version>` and short summary annotation (signed)
 - [ ] Push HEAD and `v<version>` tag
 - [ ] Check all CI statuses (pytest, flake8 linting, and `list --verbose`)
 - [ ] Generate the source distribution: `python setup.py sdist`
 - [ ] Check that all necessary files are in `dist/liquidctl-<version>.tar.gz` and that generated `extraversion.py` makes sense
 - [ ] Sign the source distribution: `gpg --detach-sign -a dist/liquidctl-<version>.tar.gz`

## Binary distribution for Windows

 - [ ] Download and check artifact built by AppVeyor
 - [ ] Sign the artifact: `gpg --detach-sign -a dist/liquidctl-<version>-bin-windows-x86_64.zip`

## Release

 - [ ] Upload: `twine upload dist/liquidctl-<version>.tar.gz{,.asc}`
 - [ ] Upgrade the `v<version>` tag on GitHub to a release (with sdist, Windows artifact, and corresponding GPG signatures)
 - [ ] Update the HEAD changelog with the release file SHA256 sums

## Post release

 - [ ] Update ArchLinux `liquidctl-git`
