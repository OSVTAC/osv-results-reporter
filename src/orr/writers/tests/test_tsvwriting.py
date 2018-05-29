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
from unittest import TestCase

import orr.writers.tsvwriting as tsvwriting


class TsvWritingModuleTest(TestCase):

    """
    Test the functions in orr.writers.tsvwriting.
    """

    def test_make_tsv_file(self):
        dir_path = 'my/output'
        cases = [
            ('President', Path('my/output/President.tsv')),
            ('Vice President', Path('my/output/Vice President.tsv')),
        ]
        for name, expected in cases:
            with self.subTest(name=name):
                actual = tsvwriting.make_tsv_file(dir_path, name)
                self.assertEqual(actual, expected)
