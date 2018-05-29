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
import logging

import xlsxwriter


_log = logging.getLogger(__name__)


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
            self.worksheet.write(row_index, i, value)

        self.row_index += 1


class XLSXBook:

    """
    Encapsulates an XLSX file (aka workbook).
    """

    def __init__(self, path):
        """
        Args:
          path: a path-like object.
        """
        # TODO: open the file in a create method and not __init__().
        _log.info(f'opening Excel file for writing: {path}')
        self.workbook = xlsxwriter.Workbook(path)

        self.closed = False

    def close(self):
        _log.debug(f'closing: {self.workbook!r}')
        self.workbook.close()
        self.closed = True

    # We define a __del__() method to help us when it's not convenient
    # to call close() explicitly (e.g. from within a template).
    def __del__(self):
        if not self.closed:
            _log.debug(f'calling close from __del__: {self.workbook!r}')
            self.close()

    def add_sheet(self, name=None, rows=None):
        """
        Create, and return an XLSXSheet object.

        Args:
          name: an optional name for the worksheet. Defaults to e.g. "Sheet1".
        """
        if rows is None:
            rows = []

        worksheet = self.workbook.add_worksheet(name)
        sheet = XLSXSheet(worksheet)

        for row in rows:
            sheet.add_row(row)

        return sheet


@contextmanager
def creating_workbook(path):
    """
    Create and yield an XLSXBook object.

    Args:
      path: a path-like object.
    """
    book = XLSXBook(path)

    try:
        yield book
    finally:
        # Close the file handle
        book.close()


# TODO: remove this shortcut function?
def add_worksheet(book, rows=None, name=None):
    """
    Add a worksheet to a workbook.

    Args:
      book: an XLSXBook object.
      rows: the data to add to the sheet, as an iterable of iterables.
      name: an optional name for the worksheet.
    """
    if rows is None:
        rows = []

    sheet = book.add_sheet(name=name)
    for row in rows:
        sheet.add_row(row)
