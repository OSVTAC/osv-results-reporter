#
# Open Source Voting Results Reporter (ORR) - election results report generator
# Copyright (C) 2018  Chris Jerdonek
#
# This file is part of Open Source Voting Results Reporter (ORR).
#
# ORR is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

"""
This file lets the project be installed locally using `pip install`.

This setup.py is not meant to support publishing the project to PyPI!
"""

from pathlib import Path
import sys

from setuptools import setup, find_packages


PACKAGE_DATA_EXTS = [
    # Include the empty extension for the file "SHA256SUMS".
    '',
    '.html',
    '.xlsx',
]


def _log(msg):
    # Print to stderr instead of using the logging module because using
    # the logging module is probably overkill for this simple case.
    print(f'setup.py: {msg}', file=sys.stderr)


def compute_package_data(name):
    """
    Return glob patterns of the data files needed for testing.

    At one point, this returned--

    [
        'testing/tests/data/*',
        'tests/end2end/expected_minimal/*',
        'tests/end2end/expected_minimal/results-detail/*',
        'tests/end2end/expected_minimal/results-rcv/*',
    ]
    """
    # Instead of listing individual files, we replace individual files
    # with the directory containing the file, concatenated with "*".
    # Then we use the set() operation to remove duplicates.
    # We use relative_to() to return "testing/..." instead of
    # "orr/testing/...", for example.
    patterns = set(
        str((p.parent / '*').relative_to(name))
        for p in Path(name).glob('**/*')
        if (p.is_file() and not p.name.startswith('.') and
            p.suffix in PACKAGE_DATA_EXTS)
    )
    patterns = sorted(patterns)

    return patterns


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
    url='https://github.com/OSVTAC/osv-results-reporter',
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
    package_data={
        'orr': compute_package_data('orr'),
    },
)
