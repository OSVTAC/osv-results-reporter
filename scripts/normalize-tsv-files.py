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
Normalize TSV files in a directory.

The main thing this script does is ensure that every row has the same
number of tabs, which lets GitHub render it nicely online.

Usage: python scripts/normalize-tsv-files.py DIR_PATH
"""

from pathlib import Path
import sys

import orr.utils as utils


TAB = '\t'


def log(text):
    print(text, file=sys.stderr)


def normalize_tsv(path):
    new_lines = []
    with open(path) as f:
        line = next(f).rstrip()
        new_lines.append(line)
        count = line.count(TAB)

        for line in f:
            line = line.rstrip()
            line_count = line.count(TAB)
            if line_count < count:
                line += (count - line_count) * TAB

            new_lines.append(line)

    new_text = '\n'.join(new_lines) + '\n'
    path.write_text(new_text)


def main():
    try:
        path = sys.argv[1]
    except IndexError:
        raise RuntimeError('path not provided')

    dir_path = Path(path)

    for path in dir_path.glob('**/*.tsv'):
        log(f'normalizing: {path}')
        normalize_tsv(path)


if __name__ == '__main__':
    main()
