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
Helper script to generate a SHA256SUMS file of all the files inside a
directory (and its subdirectories, etc).

Usage: python scripts/sha256sum-directory.py DIR

Prints the result to stdout.

To run in the Docker container:

    $ docker run --entrypoint python orr scripts/sha256sum-directory.py DIR

"""

import logging
from pathlib import Path
import shlex
import subprocess
import sys


_log = logging.getLogger(__name__)


def get_command_args():
    platform = sys.platform

    if platform == 'darwin':
        # On Mac OS X, sha256sum isn't available.
        # Also, we need to specify 256 manually here because `shasum`
        # defaults to SHA-1.
        args = ['shasum', '--algorithm', '256', '-b']
    else:
        args = ['sha256sum', '-b']

    return args


def main():
    logging.basicConfig(level=logging.INFO)

    try:
        dir_path = sys.argv[1]
    except IndexError:
        raise RuntimeError('path not provided')

    dir_path = Path(dir_path)
    paths = sorted(path for path in dir_path.glob('**/*') if not path.is_dir())

    initial_args = get_command_args()
    args = initial_args.copy()
    args.extend(str(p) for p in paths)

    _log.info(f"writing SHA256SUMS to stdout using: {' '.join(initial_args)} ...")
    subprocess.run(args, encoding='utf-8', check=True)


if __name__ == '__main__':
    main()
