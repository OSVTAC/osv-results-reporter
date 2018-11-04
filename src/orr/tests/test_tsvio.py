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
Test the orr.tsvio module.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from orr.tsvio import TSVReader


class TSVReaderTest(TestCase):

    """
    Test the TSVReader class.
    """

    def test(self):
        text = dedent("""\
        header1\theader2\theader3
        row1\t100\t101\t102
        row2\t200\t201\t202
        """)
        expected = [
            ['row1', '100', '101', '102'],
            ['row2', '200', '201', '202'],
        ]
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'temp.tsv'
            path.write_text(text)
            with TSVReader(path) as reader:
                iterator = reader.readlines()
                actual = list(iterator)

        self.assertEqual(actual, expected)
