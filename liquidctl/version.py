"""Interfaces to read the liquidctl version."""

# uses the psf/black style


# keep setuptools_scm parameters in sync with pyproject.toml
_SETUPTOOLS_SCM_PARAMS = {"version_scheme": "release-branch-semver"}


def _build_version():

    try:
        from liquidctl._version import version, version_tuple

        return (version, version_tuple)
    except ModuleNotFoundError:
        return None


def _runtime_version():

    try:
        from setuptools_scm import get_version
    except ModuleNotFoundError:
        return None

    # first, assume that we're a git checkout
    try:
        version = get_version(**_SETUPTOOLS_SCM_PARAMS)
        if version:
            return (version, None)
    except LookupError:
        pass

    # if that also failed, assume that we're a tarball
    try:
        guess = get_version(parentdir_prefix_version="liquidctl-", **_SETUPTOOLS_SCM_PARAMS)
        if guess:
            if "+" in guess:
                guess += "-guessed"
            else:
                guess += "+guessed"
            return (guess, None)
    except LookupError:
        pass

    return None


# - try to get the version written by setuptools_scm during the build;
# - otherwise try to compute one right now;
# - failing that too, use an obviously invalid value
#
# (_version_tuple is kept private as it's only available in some cases and
# don't want to commit to it yet)
(version, _version_tuple) = _build_version() or _runtime_version() or ("0.0.0-unknown", None)

# old field name (liquidctl.__version__ is preferred now)
__version__ = version
