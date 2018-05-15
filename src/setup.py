"""
This file lets the project be installed locally using `pip install`.

This setup.py is not meant to support publishing the project to PyPI!
"""

from pathlib import Path
import sys

from setuptools import setup, find_packages


def _log(msg):
    # Print to stderr instead of using the logging module because using
    # the logging module is probably overkill for this simple case.
    print(f'setup.py: {msg}', file=sys.stderr)


def parse_install_requires():
    """
    Parse requirements.in, and return the list to pass as the
    install_requires argument to setup().
    """
    path = Path(__file__).parent / 'requirements.in'
    text = path.read_text()
    reqs = [line.strip() for line in text.splitlines()
            if not line.startswith('#')]

    _log(f'parsed install_requires from requirements.in: {reqs}')

    return reqs


setup(
    name='osv-results-reporter',
    # TODO: DRY up with orr.main.VERSION.
    version='0.0.1',
    description='template-based election results report generator',
    url='https://github.com/carl3/open-results-reporter',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    packages=find_packages(),
    install_requires=parse_install_requires(),
    entry_points={
        'console_scripts': [
            'orr=orr.main:main',
        ],
    },
)
