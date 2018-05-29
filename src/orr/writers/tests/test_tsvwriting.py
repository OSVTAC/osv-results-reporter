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
Test the orr.writers.tsvwriting module.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

import orr.writers.tsvwriting as tsvwriting


class TsvWritingModuleTest(TestCase):

    """
    Test the functions in orr.writers.tsvwriting.
    """

    def test_make_tsv_path(self):
        dir_path = 'my/output'
        cases = [
            ('President', Path('my/output/President.tsv')),
            ('Vice President', Path('my/output/Vice President.tsv')),
        ]
        for name, expected in cases:
            with self.subTest(name=name):
                actual = tsvwriting.make_tsv_path(dir_path, name)
                self.assertEqual(actual, expected)

    def test_make_tsv_file(self):
        rows = [
            ('Alice', 'Bill'),
            (100, 200),
        ]
        expected = dedent("""\
        Alice\tBill
        100\t200
        """)
        with TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            path = temp_dir / 'test.tsv'

            tsvwriting.make_tsv_file(path, rows=rows)
            actual = path.read_text()
            self.assertEqual(actual, expected)

    def test_make_tsv_directory(self):
        rel_dir = 'my/path'
        contests = [
            ('President', [('A', 'B'), (1, 2)]),
            ('Vice President', [('C', 'D'), (3, 4)]),
        ]
        expected = [
            Path('my/path/President.tsv'),
            Path('my/path/Vice President.tsv'),
        ]
        with TemporaryDirectory() as temp_dir:
            paths = list(tsvwriting.make_tsv_directory(temp_dir, rel_dir=rel_dir,
                                                    contests=contests))

            # TODO: also check the content of the files.
            self.assertEqual(paths, expected)
