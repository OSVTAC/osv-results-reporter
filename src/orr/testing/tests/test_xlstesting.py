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

from pathlib import Path
from unittest import TestCase

import orr.testing.xlstesting as xlstesting
from orr.testing.xlstesting import SAMPLE_XLSX_PATH


class ModuleTest(TestCase):

    """
    Test the functions in orr.main.
    """

    def test_get_sheet_names(self):
        wb = xlstesting.load(SAMPLE_XLSX_PATH)
        actual = xlstesting.get_sheet_names(wb)
        expected = ['People', 'Animals']
        self.assertEqual(actual, expected)
