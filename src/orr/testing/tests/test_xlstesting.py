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


SAMPLE_DIR = Path(__file__).parent / 'data'
# The path to our sample xlsx file.
SAMPLE_XLSX_PATH = SAMPLE_DIR / 'sample.xlsx'


class ModuleTest(TestCase):

    """
    Test the functions in the xlstesting module.
    """

    def test_get_sheet_names(self):
        # The data in the second sheet.
        expected_data = [
            ('Id', 'Name', 'Color'),
            (4, 'Bear', 'Brown'),
            (5, 'Squirrel', 'Gray')
        ]

        with open(SAMPLE_XLSX_PATH, mode='rb') as f:
            wb = xlstesting.load(f)

            # Check the worksheet names.
            actual = xlstesting.get_sheet_names(wb)
            expected = ['People', 'Animals']
            self.assertEqual(actual, expected)

            # Check the data in the second sheet.
            sheet2 = wb.worksheets[1]
            data = xlstesting.get_sheet_rows(sheet2)
            self.assertEqual(data, expected_data)
