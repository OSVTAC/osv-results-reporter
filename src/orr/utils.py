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
Simple helper functions.
"""

from datetime import datetime
import hashlib
import json

import babel.dates


# The buffer size to use when hashing files.
HASH_BYTES = 2 ** 12  # 4K

# Our options for pretty-printing JSON for increased human readability.
DEFAULT_JSON_DUMPS_ARGS = dict(sort_keys=True, indent=4, ensure_ascii=False)


def read_json(path):
    with open(path) as f:
        data = json.load(f)

    return data


def strip_trailing_whitespace(text):
    """
    Strip trailing whitespace from the end of each line.
    """
    lines = text.splitlines()
    text = ''.join(line.rstrip() + '\n' for line in lines)

    return text


def parse_datetime(dt_string):
    """
    Parse a string in a standard format representing a datetime, and
    return a datetime.datetime object.

    Args:
      dt_string: a datetime string in the format, "2018-06-01 20:48:12".
    """
    return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')


def format_date(date, lang, format_=None):
    """
    Args:
      date: a datetime.date object.
      lang: a 2-letter language code.
    """
    if format_ is None:
        format_ = 'long'
    return babel.dates.format_date(date, format=format_, locale=lang)


# TODO: support other hash algorithms.
def hash_file(path):
    """
    Hash the contents of a file, using SHA-256.

    Returns the result as a hexadecimal string.
    """
    hasher = hashlib.sha256()
    with open(path, mode='rb') as f:
        while True:
            data = f.read(HASH_BYTES)
            if not data:
                break
            hasher.update(data)

    sha = hasher.hexdigest()

    return sha
