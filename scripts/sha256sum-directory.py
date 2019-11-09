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
Helper script to compute SHA256SUMS for all files inside a directory,
recursively.

Usage: python scripts/sha256sum-directory.py DIR

Prints the result to stdout.

To run in the Docker container:

    $ docker run --entrypoint python orr scripts/sha256sum-directory.py DIR

"""

import logging
import sys

import orr.utils as utils


def main():
    logging.basicConfig(level=logging.INFO)

    try:
        dir_path = sys.argv[1]
    except IndexError:
        raise RuntimeError('path not provided')

    text = utils.compute_sha256sum(dir_path)

    print(text)


if __name__ == '__main__':
    main()
