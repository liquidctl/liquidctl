import logging
import os
import sys

def get_config_files(file=None, appname='liquidctl', **kwargs):
    """
    This will get all the potential file paths on the system for where the config file
    can be

    This will also handle the --config overrides
    """
    files = []
    if file:
        files.append(file)

    if sys.platform == 'win32':
        files.append(os.path.join(os.getenv('APPDATA'), appname, 'config.toml'))
        files.append(os.path.join(os.getenv('LOCALAPPDATA'), appname, 'config.toml'))   # not on XP
        files.append(os.path.join(os.getenv('PROGRAMDATA'), appname, 'config.toml'))    # not on XP
    elif sys.platform == 'darwin':
        files.append(os.path.expanduser(os.path.join('~', f'.{appname}.toml')))
        files.append(os.path.expanduser(os.path.join('~/Library/Application Support', appname, 'config.toml')))
        files.append(os.path.expanduser(os.path.join('/Library/Application Support', appname, 'config.toml')))
    elif sys.platform == 'linux':
        XDG_CONFIG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.expanduser(os.path.join('~', '.config')))
        XDG_CONFIG_DIRS = os.getenv('XDG_CONFIG_DIRS', '/etc/xdg')

        # treat all other platforms as *nix and conform to XDG basedir spec
        files.append(os.path.expanduser(os.path.join('~', f'.{appname}.toml')))
        files.append(os.path.join(XDG_CONFIG_HOME, appname, 'config.toml'))
        files.append(os.path.join(XDG_CONFIG_DIRS, appname, 'config.toml'))
    else:
        files.append(os.path.expanduser(os.path.join('~', f'.{appname}.toml')))

    return files

def filter_config_files(files=[], ignore_config=False, **kwargs):
    """
    This will take a list of file paths and return the first one that exists from the list.
    If the ignore config option is set then it will return None even if files do exist.
    """
    if ignore_config:
        return None

    file = None
    for f in files:
        if os.path.isfile(f):
            file = f
            break

    return file
