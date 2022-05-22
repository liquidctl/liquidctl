# Release checklist

## Prepare system

 - [ ] Ensure publishing dependencies are installed: twine
 - [ ] Export helper enviroment variable: `export VERSION=<version>`

## Prepare repository

 - [ ] Update last update date in the man page
 - [ ] Update the CHANGELOG
 - [ ] Remove "N/New driver, ..." notes from the table of supported devices (and merge lines if appropriate)
 - [ ] Update version in pip install liquidctl==version examples
 - [ ] Regenerate the udev rules:
       `(cd extra/linux && python generate-uaccess-udev-rules.py > 71-liquidctl.rules)`
 - [ ] Commit:
       `git commit -m "release: prepare for v$VERSION"`

## Test locally

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

## Test in CI

 - [ ] Push HEAD:
       `git push origin HEAD`
 - [ ] Check all CI statuses (pytest, flake8 linting, and `list --verbose`)

## Build source distribution and wheel

 - [ ] Tag HEAD with changelog and PGP signature:
       `git tag -as "v$VERSION"`
 - [ ] Build the source distribution and wheel (stash any changes to this file beforehand):
       `python -m build`
 - [ ] Check that all necessary files are in the `dist/liquidctl-$VERSION.tar.gz` sdist
 - [ ] Check the contents of the `dist/liquidctl-$VERSION.whl` wheel
 - [ ] Sign both sdist and wheel:
       `gpg --detach-sign -a "dist/liquidctl-$VERSION.tar.gz"`
       `gpg --detach-sign -a "dist/liquidctl-$VERSION-py3-none-any.whl"`

## Release

 - [ ] Push vVERSION tag:
       `git push origin "v$VERSION"`
 - [ ] Upload sdist and wheel to PyPI:
       `twine upload dist/liquidctl-$VERSION{.tar.gz,-py3-none-any.whl}{,.asc}`
 - [ ] Generate SHA256 checksums for the release files:
       `sha256sum dist/liquidctl-$VERSION{.tar.gz,-py3-none-any.whl} | tee "dist/liquidctl-$VERSION.sha256sums"`
 - [ ] Upgrade the vVERSION tag on GitHub to a release (with sdist, wheel, and corresponding GPG signatures)
 - [ ] Update the HEAD changelog with the SHA256 checksums

## Post release

 - [ ] Merge the release branch into the main branch (if appropriate)
 - [ ] Update the HEAD release-checklist with this checklist
 - [ ] Update ArchLinux `liquidctl-git`
