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
Support for creating PDF files.
"""

import logging
import os

from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, SimpleDocTemplate, Table
from reportlab.rl_config import defaultPageSize


_log = logging.getLogger(__name__)


def get_available_size():
    """
    Return the available space on the page as (width, height).
    """
    page_width, page_height = defaultPageSize

    return (page_width - 2 * inch, page_height - 2 * inch)


def make_table_data(row_count):
    """
    Args:
      rows: the number of data rows.
    """
    column_count = 20
    first_row = [f'Column{i}' for i in range(column_count)]

    data = [first_row]
    for i in range(row_count):
        value = (i + 1) * 10000
        row = [value + j for j in range(20)]
        data.append(row)

    return data

def slice_data_vertically(data, start, stop):
    """
    Return a list of new row data, slicing each row.

    Args:
      data: a list of row data.
      start: the starting slice index.
      stop: the stopping slice index.
    """
    return [tuple(row[start:stop]) for row in data]


def compute_width(data, start_column, end_column):
    """
    Compute the width of a table constructed from the given columns of data.

    Args:
      start_column: the index of the first column.
      end_column: the index of the last column.
    """
    assert end_column > start_column

    # Grab the data that would be used from each row.
    new_data = slice_data_vertically(data, start=start_column, stop=(end_column + 1))
    table = Table(new_data)

    # We can pass 0 for the available width and height since it doesn't
    # affect the calculation.
    width, height = table.wrap(0, 0)

    return width


def split_data_vertically(data, start_column, width, column_count):
    """
    Return the number of columns that can fit in the available width.

    Args:
      width: the available width.
      column_count: the maximum number of columns.
    """
    end_column = start_column + 1
    while end_column < column_count:
        _log.debug(f'computing (start_column, end_column): ({start_column}, {end_column})')
        actual_width = compute_width(data, start_column, end_column=end_column)
        if actual_width > width:
            end_column -= 1
            break

        # Otherwise, continue.
        end_column += 1

    if end_column == start_column:
        _log.warn('split_data_vertically() computed zero columns')
        end_column += 1

    return end_column - start_column


def compute_column_counts(data, width):
    """
    Return an iterable of column counts representing how a table constructed
    from the given data should be split along columns.

    Args:
      width: the available width.
    """
    column_count = max(len(row) for row in data)

    counts = []
    start_column = 0
    while start_column < column_count:
        count = split_data_vertically(data, start_column, width=width, column_count=column_count)
        counts.append(count)
        start_column += count

    return counts


def split_table_vertically(table, column_counts):
    """
    Split a Table object along columns.

    Returns a list of new Table objects.

    Args:
      table: a reportlab Table object.
      column_counts: an iterable of the number of columns of data to use
        in each table split from the original.
    """
    # TODO: don't rely on an internal API.
    data = table._cellvalues

    tables = []
    start = 0
    for column_count in column_counts:
        stop = start + column_count
        new_data = slice_data_vertically(data, start=start, stop=stop)
        table = Table(new_data)
        tables.append(table)
        start = stop

    return tables


# TODO: keep working on PDF generation.  This is a scratch function.
def make_pdf(path, text):
    """
    Args:
      path: a path-like object.
      text: the text to include, as a string.
    """
    # Convert the path to a string for reportlab.
    path = os.fspath(path)
    document = SimpleDocTemplate(path)

    available = get_available_size()
    available_width, available_height = available

    data = make_table_data(row_count=60)

    column_counts = compute_column_counts(data, width=available_width)

    table = Table(data)

    # First split the table along rows.
    tables = table.split(*available)

    story = []
    for table in tables:
        # Then split each sub-table along columns, using the column
        # counts we already computed.
        new_tables = split_table_vertically(table, column_counts)
        _log.debug(f'split table into {len(new_tables)} tables')
        for new_table in new_tables:
            story.extend([new_table, PageBreak()])

    document.build(story)
