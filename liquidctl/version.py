"""Interfaces to read the liquidctl version."""

# uses the psf/black style


def _get_built_version():

    try:
        from liquidctl._version import version, version_tuple

        return (version, version_tuple)
    except ModuleNotFoundError:
        return None


def _compute_version_at_runtime():

    try:
        from setuptools_scm import get_version
    except ModuleNotFoundError:
        return None

    # first, assume that we're a git checkout
    try:
        version = get_version()
        if version:
            return (version, None)
    except LookupError:
        pass

    # if that also failed, assume that we're a tarball
    try:
        guess = get_version(parentdir_prefix_version="liquidctl-")
        if guess:
            if "+" in guess:
                guess += "-guessed"
            else:
                guess += "+guessed"
            return (guess, None)
    except LookupError:
        pass

    # finally, use an obviously invalid value
    return ("0.0.0-unknown", None)


# try to get the version written by setuptools_scm during the build, otherwise
# compute one right now; _version_tuple is kept private as it's only available
# in some cases and don't want to commit to it yet
(version, _version_tuple) = _get_built_version() or _compute_version_at_runtime()

# old field name (liquidctl.__version__ is preferred now)
__version__ = version
