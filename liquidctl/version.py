# uses the psf/black style


def _get_version_relaxed():

    # try to get the version written by setuptools_scm during the build
    try:
        from liquidctl._version import version

        return version
    except ModuleNotFoundError:
        pass

    # if that fails, try to compute the version directly
    from setuptools_scm import get_version

    # first assuming that we are on a git checkout
    try:
        return get_version()
    except LookupError:
        pass

    # and then, if that also fails, assuming that we are on a tarball
    return get_version(parentdir_prefix_version="liquidctl-") + "-guessed"


try:
    __version__ = _get_version_relaxed()
except:
    # if everything fails, or if we couldn't import get_version(), use a
    # placeholder value that's obviously invalid
    __version__ = "0.0.0-unknown"
