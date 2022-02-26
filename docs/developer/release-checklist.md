# Release checklist

## Prepare system

 - [ ] Ensure publishing dependencies are installed:
       `pacman -S twine`

## Prepare repository

 - [ ] Update liquidctl/version.py
 - [ ] Update last update date in the man page
 - [ ] Make sure the CHANGELOG is up to date
 - [ ] Remove "N/New driver, ..." notes from the table of supported devices (and merge lines if appropriate)
 - [ ] Regenerate the udev rules:
       `(cd extra/linux && python generate-uaccess-udev-rules.py > 71-liquidctl.rules)`
 - [ ] Commit:
       `git commit -m "release: prepare for v$VERSION"`

## Test

 - [ ] Run unit and doc tests:
       `python -m pytest`

Then install locally and:

 - [ ] Run my personal setup scripts:
       `liquidcfg && liquiddyncfg`
 - [ ] Test yoda:
       `extra/yoda --match kraken control pump with '(20,50),(50,100)' on coretemp.package_id_0 and fan with '(20,25),(34,100)' on _internal.liquid --verbose`
 - [ ] Test krakenduty:
       `extra/krakenduty-poc train && extra/krakenduty-poc status`
 - [ ] Test liquiddump:
       `extra/liquiddump | jq -c .`
 - [ ] Test krakenx (git):
       `colctl --mode fading --color_count 2 --color0 192,32,64 --color1 246,11,21 --fan_speed "(30, 100), (40, 100)" --pump_speed "(30, 100), (40, 100)"`

## Source distribution

 - [ ] Build the source distribution and wheel:
       `python -m build`
 - [ ] Check that all necessary files are in the `dist/liquidctl-$VERSION.tar.gz` sdist
 - [ ] Check the `dist/liquidctl-$VERSION.whl` wheel
 - [ ] Tag HEAD with changelog and PGP signature:
       `git tag -as "v$VERSION"`
 - [ ] Push HEAD and vVERSION tag:
       `git push origin HEAD "v$VERSION"`
 - [ ] Check all CI statuses (pytest, flake8 linting, and `list --verbose`)
 - [ ] Sign the source distribution:
       `gpg --detach-sign -a "dist/liquidctl-$VERSION.tar.gz"`

## Release

 - [ ] Upload:
       `twine upload dist/liquidctl-$VERSION.tar.gz{,.asc}`
 - [ ] Upgrade the vVERSION tag on GitHub to a release (with sdist and corresponding GPG signatures)
 - [ ] Update the HEAD changelog with the release file SHA256 sums:
       `sha256sum dist/liquidctl-$VERSION.tar.gz | tee "dist/liquidctl-$VERSION.sha256sums"`

## Post release

 - [ ] Merge the release branch into the main branch (if appropriate)
 - [ ] Update the HEAD release-checklist with this checklist
 - [ ] Update ArchLinux `liquidctl-git`
