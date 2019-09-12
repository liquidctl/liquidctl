import setuptools

HOME = 'https://github.com/jonasmalacofilho/liquidctl'

with open('liquidctl/version.py', 'r') as fv:
    vals = {}
    exec(fv.read(), vals)
    version = vals['__version__']

supported_url = '{}/tree/v{}#supported-devices'.format(HOME, version)
doc_url = '{}/tree/v{}#liquidctl--liquid-cooler-control'.format(HOME, version)
changes_url = '{}/blob/v{}/CHANGELOG.md'.format(HOME, version)

with open('README.md', 'r', encoding='utf-8') as fh:
    continuation = ('For which devices are supported, installation instructions, '
                    'a guide to the CLI and device specific details, check the '
                    'complete [Documentation]({}).').format(doc_url)
    long_description = (fh.read().split('<!-- stop here for PyPI -->', 1)[0]
                        + continuation)

setuptools.setup(
    name='liquidctl',
    version=version,
    author='Jonas Malaco',
    author_email='jonas@protocubo.io',
    description='Cross-platform tool and drivers for liquid coolers and other devices',
    long_description=long_description,
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
        'Suported devices': supported_url,
        'Documentation': doc_url,
        'Changelog': changes_url,
    },
    install_requires=['docopt', 'pyusb', 'hidapi', 'appdirs'],
    python_requires='>=3',
    entry_points={
        'console_scripts': [
            'liquidctl=liquidctl.cli:main',
        ],
    },
)
