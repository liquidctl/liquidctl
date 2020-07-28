"""Simple key-value based storage for liquidctl drivers.

Copyright (C) 2019–2020  Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging
import os
import sys
import tempfile

from ast import literal_eval

LOGGER = logging.getLogger(__name__)
XDG_RUNTIME_DIR = os.getenv('XDG_RUNTIME_DIR')


def get_runtime_dirs(appname='liquidctl'):
    """Return base directories for application runtime data.

    Directories are returned in order of preference.
    """
    if sys.platform == 'win32':
        dirs = [os.path.join(os.getenv('TEMP'), appname)]
    elif sys.platform == 'darwin':
        dirs = [os.path.join('~/Library/Caches', appname)]
    elif sys.platform == 'linux':
        # threat all other platforms as *nix and conform to XDG basedir spec
        dirs = []
        if XDG_RUNTIME_DIR:
            dirs.append(os.path.join(XDG_RUNTIME_DIR, appname))
        # regardless whether XDG_RUNTIME_DIR is set, fallback to /var/run if it
        # is available; this allows a user with XDG_RUNTIME_DIR set to still
        # find data stored by another user as long as it is in the fallback
        # path (see #37 for a real world use case)
        if os.path.isdir('/var/run'):
            dirs.append(os.path.join('/var/run', appname))
        assert dirs, 'Could not get a suitable place to store runtime data'
    else:
        dirs = [os.path.join('/tmp', appname)]
    return dirs


class _FilesystemBackend:
    def _sanitize(self, key):
        if not isinstance(key, str):
            raise TypeError('key must str')
        if not key.isidentifier():
            raise ValueError('key must be valid Python identifier')
        return key

    def __init__(self, key_prefixes):
        key_prefixes = map(self._sanitize, key_prefixes)
        # compute read and write dirs from base runtime dirs: the first base
        # dir is selected for writes and prefered for reads
        self._read_dirs = [os.path.join(x, *key_prefixes) for x in get_runtime_dirs()]
        self._write_dir = self._read_dirs[0]
        os.makedirs(self._write_dir, exist_ok=True)
        if XDG_RUNTIME_DIR and os.path.commonpath([XDG_RUNTIME_DIR, self._write_dir]):
            # set the sticky bit to prevent removal during cleanup
            os.chmod(self._write_dir, 0o1700)
            LOGGER.debug('data in %s (within XDG_RUNTIME_DIR)', self._write_dir)
        else:
            LOGGER.debug('data in %s', self._write_dir)

    def load(self, key):
        for base in self._read_dirs:
            path = os.path.join(base, key)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, mode='r') as f:
                    data = f.read().strip()
                    if len(data) == 0:
                        value = None
                    else:
                        value = literal_eval(data)
                    LOGGER.debug('loaded %s=%r (from %s)', key, value, path)
            except OSError as err:
                LOGGER.warning('%s exists but cannot be read: %s', path, err)
                continue
            return value
        LOGGER.debug('no data (file) found for %s', key)
        return None

    def store(self, key, value):
        data = repr(value)
        assert literal_eval(data) == value, 'encode/decode roundtrip fails'
        path = os.path.join(self._write_dir, key)
        fd, tmp = tempfile.mkstemp(dir=self._write_dir, text=True)
        with open(fd, mode='w') as f:
            f.write(data)
            f.flush()
        os.replace(tmp, path)
        LOGGER.debug('stored %s=%r (in %s)', key, value, path)


class RuntimeStorage:
    """Unstable API."""

    def __init__(self, key_prefixes):
        self._backend = _FilesystemBackend(key_prefixes)
        self._cache = {}

    def load(self, key, of_type=None, default=None):
        """Unstable API."""
        if key in self._cache:
            value = self._cache[key]
        else:
            value = self._backend.load(key)
            self._cache[key] = value
        if value is None:
            return default
        elif of_type and not isinstance(value, of_type):
            return default
        else:
            return value

    def store(self, key, value):
        """Unstable API."""
        self._backend.store(key, value)
        self._cache[key] = value
        return value

    def load_int(self, key, default=None):
        """Unstable API.  Soon to be removed."""
        return self.load(key, of_type=int, default=default)

    def store_int(self, key, value):
        """Unstable API.  Soon to be removed."""
        self.store(key, value)
