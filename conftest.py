import sys

collect_ignore = ['setup.py']
collect_ignore.append('extra/contrib/fusion_rgb_cycle.py')  # depends on coloraide

if sys.platform != 'linux':
    collect_ignore.append('tests/test_smbus.py')

if sys.platform not in ['win32', 'cygwin']:
    collect_ignore.append('extra/windows/LQiNFO.py')
