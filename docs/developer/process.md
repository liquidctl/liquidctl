# Development process

## Branches and tags

The main branch is `main`, and it tracks the changes that will be included in
the next release.  This branch is kept functional (barring the occasional bug),
and its history is never rewritten.  Pull requests and patches should generally
be developed for it (i.e. using it as base).

Releases are tagged as `v<release>` (e.g. `v1.6.0`).  Updates to past minor
releases are managed in branches following the naming scheme
`<major>.<minor>.x-branch` (e.g. `1.5.x-branch`).

Other branches and tags are generally for internal use, and may be deleted or
rewritten at any time.

## Release cycle and pre-release freeze periods

Besides unscheduled patch releases, a new minor release is expected once every
13 weeks.

In the four weeks before a scheduled release, major changes, like new buses or
large refactorings, stop being merged into the main branch.  This period is
referred to as the _major change freeze._  New drivers on existing buses can
still be merged during the major change freeze.

Then, in the two weeks before the release, only bug fixes and documentation
improvements are merged into the main branch.  This period is referred to as
the _minor change freeze._

Occasionally, scheduled releases may be anticipated (if the activity is low and
the freeze periods can be retroactively respected), downgraded (if it only
contains bug fixes and documentation improvements) or skipped (if there are no
changes).

## Stability and backward compatibility

This project adheres to Semantic Versioning, version 2.0, and there are no
plans for a new major version release of the project.  Because of this,
liquidctl releases (minor or patch) retain backward compatibility with previous
versions.

The stability guarantee that we try to uphold can be better defined by:

1. No breaking changes to the *effect* of CLI commands *on the device,*
2. and no breaking changes to *documented* behavior of *public* APIs,
3. except when required by a bug fix.

In particular:

4. The output from CLI commands is *not* guaranteed to be stable,
5. and neither are the items returned from `get_status()` or `initialize()`.

Additionally:

6. We occasionally provide backward compatibility for undocumented behavior or
   private APIs, on a (use) case by case basis;
7. Even when a change is allowed by the policy above, we still try to weight in
   the possible disruption versus their benefit (e.g. when changing an existing
   item in `get_status()`);
8. If a tree falls in the forest and no one is around to hear it, it does not
   make a sound: breaking changes that will not observed by any real users (at
   the time of the change ) may be ok, on the condition that they be reversed
   should one of those users come forward;
9. Some APIs are documented to be *unstable* and, thus, are exempt from the
   stability guarantee.

The use of deprecated features is discouraged, but deprecation is not directly
correlated with (eventual) removal.  Feature removal depends on whether the
feature is no longer useful and whether its removal is allowed by the stability
guarantee.

## License and copyright

Liquidctl is licensed under the GPL, either version 3 or, at the option of
those receiving the program, any later version.  Changes must be licensed under
the same license, but their authors retain the copyright of their individual
changes.

Each module contains the copyright notice and a [short SPDX license identifier]
to unambiguously yet concisely indicate the applicable license.  The
copyright notice should explicitly list the most important contributors to the
module, and then end with "and contributors".  Contributors are encouraged to
update these notices when submitting major changes to modules.

The project's copyright notice explicitly lists the major contributors the
project – in this context, a major contributor is someone who has authored at
least one non-trivial module of the `liquidctl` package (e.g. a driver) – and
then end with "and contributors".  Only project maintainers are allowed to
update the project's copyright notice; contributors should contact the
maintainers if they want to ask to be included among the explicitly listed
names.

[short SPDX license identifier]: https://spdx.github.io/spdx-spec/appendix-V-using-SPDX-short-identifiers-in-source-files/
