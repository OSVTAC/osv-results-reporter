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
Helper script to normalize a json file.

Usage: python scripts/normalize-json.py JSON_PATH

Prints the normalized json to stdout.
"""

import json
import sys


def main():
    try:
        path = sys.argv[1]
    except IndexError:
        raise RuntimeError('path not provided')

    with open(path) as f:
        data = json.load(f)

    serialized = json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False)

    print(serialized)


if __name__ == '__main__':
    main()
