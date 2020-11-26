import sys

collect_ignore = ['setup.py']

if sys.platform != 'linux':
    collect_ignore.append('tests/test_smbus.py')

if sys.platform not in ['win32', 'cyqwin']:
    collect_ignore.append('extra/windows/LQiNFO.py')
