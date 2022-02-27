"""Interfaces to read the liquidctl version."""

# uses the psf/black style


def _get_version_relaxed():

    # try to get the version written by setuptools_scm during the build
    try:
        from liquidctl._version import version, version_tuple

        return (version, version_tuple)
    except ModuleNotFoundError:
        pass

    # if that failed, try to compute the version directly
    from setuptools_scm import get_version

    # first assuming that we're a git checkout
    try:
        version = get_version()
        if version:
            return (version, None)
    except LookupError:
        pass

    # and then, if that also failed, assuming that we're a tarball
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

    # finally, use a obviously invalid value
    return ("0.0.0-unknown", None)


# keep _version_tuple private for now, as it's only available in some cases and
# don't want to commit to it yet

(version, _version_tuple) = _get_version_relaxed()

# old field name (liquidctl.__version__ is preferred now)
__version__ = version
