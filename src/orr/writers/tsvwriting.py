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
Support for creating TSV (and CSV) files.
"""

from pathlib import Path


TSV_SUFFIX = '.tsv'


def make_tsv_path(dir_path, name):
    """
    Return the path to the file, as a Path object.

    Args:
      path: the directory in which to write the TSV file, as a path-like
        object.
      name: the base name, without the file suffix.
    """
    base_path = Path(dir_path) / name
    path = base_path.with_suffix(TSV_SUFFIX)

    return path


def make_tsv_file(path, rows):
    with path.open('w') as f:
        for row in rows:
            line = '\t'.join(str(value) for value in row) + '\n'
            f.write(line)


def make_tsv_directory(root_dir, rel_dir, contests):
    """
    Create TSV files (one for each contest), and yield the path to each
    file as it is created, as a Path object.

    Args:
      rel_dir: the directory in which to write the TSV files, as a
        path-like object relative to the given root directory.  The
        directory will be created if it doesn't already exist.
      contests: an iterable of pairs (contest_name, rows).
    """
    root_dir = Path(root_dir)
    rel_dir = Path(rel_dir)
    # It's okay if the directory already exists.
    (root_dir / rel_dir).mkdir(parents=True, exist_ok=True)

    for contest_name, rows in contests:
        rel_path = make_tsv_path(rel_dir, contest_name)
        path = root_dir / rel_path
        make_tsv_file(path, rows)

        yield rel_path
