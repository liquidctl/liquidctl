"""Simple key-value based storage for liquidctl drivers.

Copyright (C) 2019–2019  Jonas Malaco
Copyright (C) 2019–2019  each contribution's author

This file is part of liquidctl.

liquidctl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

liquidctl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import os
import sys

LOGGER = logging.getLogger(__name__)
XDG_RUNTIME_DIR = os.getenv('XDG_RUNTIME_DIR')


def get_runtime_dirs(appname='liquidctl'):
    """Return base directories for application runtime data.

    Directories are returned in order of preference.
    """
    if sys.platform == 'win32':
        dirs = [os.path.join(os.getenv('ProgramData'), appname)]
    elif sys.platform == 'darwin':
        dirs = [os.path.join('/Library/Application Support', appname)]
    else:
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
    return dirs


class RuntimeStorage:
    """Unstable API."""

    def __init__(self, key_prefixes):
        for prefix in key_prefixes:
            assert not '..' in prefix
            assert not os.path.isabs(prefix)
        self._cache = {}
        # compute read and write dirs from base runtime dirs: the first base
        # dir is selected for writes and prefered for reads
        self._read_dirs = [os.path.join(x, *key_prefixes) for x in get_runtime_dirs()]
        self._write_dir = self._read_dirs[0]
        # prepare the write dir
        os.makedirs(self._write_dir, exist_ok=True)
        if XDG_RUNTIME_DIR and os.path.commonpath([XDG_RUNTIME_DIR, self._write_dir]):
            # set the sticky bit to prevent removal during cleanup
            os.chmod(self._write_dir, 0o1700)
            LOGGER.debug('data in %s (within XDG_RUNTIME_DIR)', self._write_dir)
        else:
            LOGGER.debug('data in %s', self._write_dir)

    def load_int(self, key, default=None):
        """Unstable API."""
        if key in self._cache:
            value = self._cache[key]
            LOGGER.debug('loaded %s=%s (from cache)', key, str(value))
            return value if value is not None else default
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
                        value = int(data)
                    LOGGER.debug('loaded %s=%s (from %s)', key, str(value), path)
            except OSError as err:
                LOGGER.warning('%s exists but cannot be read: %s', path, err)
                continue
            self._cache[key] = value
            return value if value is not None else default
        LOGGER.debug('no data (file) found for %s', key)
        return default

    def store_int(self, key, value):
        """Unstable API."""
        path = os.path.join(self._write_dir, key)
        with open(path, mode='w') as f:
            if value is None:
                f.write('')
            else:
                f.write(str(value))
            self._cache[key] = value
            LOGGER.debug('stored %s=%s (in %s)', key, str(value), path)
