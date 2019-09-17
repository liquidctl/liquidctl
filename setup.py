import os
import setuptools
import subprocess

from setuptools.command.develop import develop

def get_static_version():
    with open('liquidctl/version.py', 'r') as fv:
        vals = {}
        exec(fv.read(), vals)
    return vals['__version__']


def make_pypi_long_description(doc_url):
    with open('README.md', 'r', encoding='utf-8') as fh:
        continuation = ('For which devices are supported, installation instructions, '
                        'a guide to the CLI and device specific details, check the '
                        'complete [Documentation]({}).').format(doc_url)
        long_description = (fh.read().split('<!-- stop here for PyPI -->', 1)[0]
                            + continuation)
    return long_description


def get_git_version():
    try:
        return subprocess.check_output(['git', '--version']).strip().decode()
    except:
        return None


def make_extra_version(editable=False):
    extra = []
    if get_git_version() and os.path.isdir('.git'):
        rev_parse = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode()
        describe = subprocess.check_output(['git', 'describe', '--always', '--dirty']).strip().decode()
        extra.append(rev_parse)
        if describe.endswith('-dirty'):
            extra.append('dirty')
    if editable:
        extra.append('editable')
    with open('liquidctl/extraversion.py', 'w') as fv:
        fv.write('__extraversion__ = {!r}'.format(extra))


class custom_develop(develop):
    def run(self):
        make_extra_version(editable=True)
        super().run()


HOME = 'https://github.com/jonasmalacofilho/liquidctl'
VERSION = get_static_version()
SUPPORTED_URL = '{}/tree/v{}#supported-devices'.format(HOME, VERSION)
DOC_URL = '{}/tree/v{}#liquidctl--liquid-cooler-control'.format(HOME, VERSION)
CHANGES_URL = '{}/blob/v{}/CHANGELOG.md'.format(HOME, VERSION)

make_extra_version()

setuptools.setup(
    name='liquidctl',
    cmdclass={'develop': custom_develop},
    version=VERSION,
    author='Jonas Malaco',
    author_email='jonas@protocubo.io',
    description='Cross-platform tool and drivers for liquid coolers and other devices',
    long_description=make_pypi_long_description(DOC_URL),
    long_description_content_type='text/markdown',
    url=HOME,
    packages=setuptools.find_packages(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
    ],
    keywords='cross-platform driver nzxt kraken smart-device grid',
    project_urls={
        'Suported devices': SUPPORTED_URL,
        'Documentation': DOC_URL,
        'Changelog': CHANGES_URL,
    },
    install_requires=['docopt', 'pyusb', 'hidapi', 'appdirs'],
    python_requires='>=3',
    entry_points={
        'console_scripts': [
            'liquidctl=liquidctl.cli:main',
        ],
    },
)
