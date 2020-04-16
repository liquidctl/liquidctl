"""Run functions with elevated privileges.

Copyright (C) 2020–2020  Jonas Malaco
Copyright (C) 2020–2020  each contribution's author

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
import pickle
import sys


LOGGER = logging.getLogger(__name__)


def run_elevated(data):
    """Run (fun, params) in data.

    Should only be called from already elevated process.

    Unstable API.
    """
    try:
        fun, params = pickle.loads(bytes.fromhex(data))
        fun(*params)
        return 0
    except Exception:
        LOGGER.exception('Unexpected error')
        input('Press Enter To Exit')  # show errors in win32/uac
        return 1


def call(fun, params):
    """Call function, elevating privileges if necessary.

    Unstable API.
    """
    if sys.platform == 'win32':
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            fun(*params)
        else:
            cmd = sys.argv[0]
            data = pickle.dumps((fun, params)).hex()
            params = f'reserved run-elevated {data}'
            ctypes.windll.shell32.ShellExecuteW(None, 'runas', cmd, params, None, 1)
    else:
        raise NotImplementedError()