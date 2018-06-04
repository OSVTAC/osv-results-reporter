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

from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys

import babel.dates


_log = logging.getLogger(__name__)


UTF8_ENCODING = 'utf-8'

# The buffer size to use when hashing files.
HASH_BYTES = 2 ** 12  # 4K

# Our options for pretty-printing JSON for increased human readability.
DEFAULT_JSON_DUMPS_ARGS = dict(sort_keys=True, indent=4, ensure_ascii=False)

SHA256SUMS_FILENAME = 'SHA256SUMS'


@contextmanager
def changing_cwd(dir_path):
    initial_cwd = os.getcwd()
    new_cwd = Path(dir_path)
    try:
        os.chdir(new_cwd)
        yield
    finally:
        # Change back.
        os.chdir(initial_cwd)


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


def get_sha256sum_args():
    """
    Return the initial platform-specific arguments to generate SHA256SUMS.
    """
    platform = sys.platform

    if platform == 'darwin':
        # On Mac OS X, sha256sum isn't available.
        # Also, we need to specify 256 manually here because `shasum`
        # defaults to SHA-1.
        args = ['shasum', '--algorithm', '256', '-b']
    else:
        args = ['sha256sum', '-b']

    return args


# TODO: test this.
def get_files_recursive(dir_path):
    """
    Return all the files (but not directories) recursively in a directory,
    and return them as **paths relative to the directory being recursed
    over**.
    """
    # Change the current working directory to the directory we are recursing
    # over so the resulting paths will be relative to that.
    with changing_cwd(dir_path):
        cwd = Path('.')
        paths = sorted(path for path in cwd.glob('**/*') if not path.is_dir())

    return paths


# TODO: test this.
# TODO: also expose a function to check a SHA256SUMS file.
def directory_sha256sum(dir_path):
    dir_path = Path(dir_path)

    # Get the paths relative to the directory we are recursing over.
    # Also, `sha256sum` breaks if passed a directory path, so we need to
    # be filtering those out, which get_files_recursive() does do.
    rel_paths = get_files_recursive(dir_path)

    initial_args = get_sha256sum_args()
    args = initial_args.copy()
    args.extend(str(p) for p in rel_paths)

    _log.info(f"computing SHA256SUMS using: {' '.join(initial_args)} ...")
    proc = subprocess.run(args, stdout=subprocess.PIPE, encoding=UTF8_ENCODING,
                          check=True, cwd=dir_path)
    text = proc.stdout

    return text
