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
from tempfile import TemporaryDirectory
from unittest import TestCase

import orr.xlsxwriting as xlsxwriting
import orr.testing.xlstesting as xlstesting


class ModuleTest(TestCase):

    """
    Test the functions in the xlsxwriting module.
    """

    def test_add_worksheet(self):
        rows1 = [
            ('id', 'name'),
            (2, 'Alice'),
            (3, 'Bob'),
        ]
        rows2 = [
            ('id', 'text'),
            (4, 'abc'),
            (5, 'xyz'),
        ]

        with TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            path = temp_dir / 'test.xlsx'

            with xlsxwriting.creating_workbook(path) as wb:
                xlsxwriting.add_worksheet(wb, rows=rows1)
                xlsxwriting.add_worksheet(wb, rows=rows2, name='MySheet')

            # TODO: also check the data in the sheets.
            wb = xlstesting.load(path)
            actual = xlstesting.get_sheet_names(wb)
            expected = ['Sheet1', 'MySheet']
            self.assertEqual(actual, expected)
