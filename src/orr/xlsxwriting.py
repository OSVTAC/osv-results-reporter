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
Support for creating Excel XLSX files.
"""

from contextlib import contextmanager

import xlsxwriter


class XLSXSheet:

    """
    Encapsulates an XLSX worksheet.
    """

    def __init__(self, worksheet):
        """
        Args:
          worksheet: an xlsxwriter.worksheet.Worksheet object.
        """
        self.row_index = 0

        self.worksheet = worksheet

    def add_row(self, row):
        row_index = self.row_index
        for i, value in enumerate(row):
            self.worksheet.write(i, row_index, value)

        self.row_index += 1


@contextmanager
def creating_workbook(path):
    """
    Args:
      path: a path-like object.
    """
    workbook = xlsxwriter.Workbook(path)
    try:
        yield workbook
    finally:
        workbook.close()


def _add_sheet(wb, name=None):
    """
    Create, and return an XLSXSheet object.

    Args:
      wb: an xlsxwriter.Workbook object.
      name: an optional name for the worksheet.  Defaults to e.g. "Sheet1".
    """
    worksheet = wb.add_worksheet(name)
    sheet = XLSXSheet(worksheet)

    return sheet


# TODO: remove this shortcut function?
def add_worksheet(wb, rows=None, name=None):
    """
    Add a worksheet to a workbook.

    Args:
      wb: an xlsxwriter.Workbook object.
      rows: the data to add to the sheet, as an iterable of iterables.
      name: an optional name for the worksheet.
    """
    if rows is None:
        rows = []

    sheet = _add_sheet(wb, name=name)
    for row in rows:
        sheet.add_row(row)
