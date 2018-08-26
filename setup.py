import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read().split('<!-- stop here for PyPI -->', 1)[0]

setuptools.setup(
    name='liquidctl',
    version='1.0.0rc1',
    author='Jonas Malaco',
    author_email='jonas@protocubo.io',
    description='Liquid cooler control',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jonasmalacofilho/liquidctl',
    packages=setuptools.find_packages(),
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
    ),
    keywords='liquid cooler driver kraken',
    project_urls={
        'Documentation': 'https://github.com/jonasmalacofilho/liquidctl/blob/master/README.md',
    },
    install_requires=['docopt', 'pyusb'],
    python_requires='>=3',
    entry_points={
        'console_scripts': [
            'liquidctl=liquidctl.cli:main',
        ],
    },
)
