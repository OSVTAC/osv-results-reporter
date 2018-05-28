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
import sys

import reportlab.lib.colors as colors
# The "inch" value equals 72.0.
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (Flowable, PageBreak, Paragraph, SimpleDocTemplate,
    Table, TableStyle)


_log = logging.getLogger(__name__)

# ReportLab defaults to A4, so make the American standard more available.
DEFAULT_PAGE_SIZE = letter

# The names of ReportLab's BaseDocTemplate margin attributes.
MARGIN_NAMES = [
    'bottomMargin',
    'leftMargin',
    'rightMargin',
    'topMargin'
]

STYLES = getSampleStyleSheet()
NORMAL_STYLE = STYLES['Normal']


def get_available_size(page_size):
    """
    Return the available space on the page as (width, height).
    """
    page_width, page_height = page_size

    return (page_width - 2 * inch, page_height - 2 * inch)


def slice_data_vertically(data, start, stop):
    """
    Return a list of new row data, slicing each row.

    Args:
      data: a list of row data.
      start: the starting slice index.
      stop: the stopping slice index.
    """
    return [tuple(row[start:stop]) for row in data]


def compute_width(make_table, data, start_column, end_column):
    """
    Compute the width of a table constructed from the given columns of data.

    Args:
      make_table: a function that accepts a data argument and returns a
        ReportLab Table object.
      start_column: the index of the first column.
      end_column: the index of the last column.
    """
    assert end_column >= start_column

    # Grab the data that would be used from each row.
    new_data = slice_data_vertically(data, start=start_column, stop=(end_column + 1))
    table = make_table(new_data)

    # We can pass 0 for the available width and height since it doesn't
    # affect the calculation.
    width, height = table.wrap(0, 0)

    return width


def split_data_vertically(make_table, data, start_column, width, column_count):
    """
    Return the number of columns that can fit in the available width.

    Args:
      make_table: a function that accepts a data argument and returns a
        ReportLab Table object.
      width: the available width.
      column_count: the maximum number of columns.
    """
    end_column = start_column
    while end_column < column_count:
        actual_width = compute_width(make_table, data, start_column, end_column=end_column)
        _log.debug(f'width for columns ({start_column}, {end_column}): {actual_width}')
        if actual_width > width:
            end_column -= 1
            break

        # Otherwise, continue.
        end_column += 1

    if end_column == start_column:
        _log.warn('split_data_vertically() computed zero columns')
        end_column += 1

    return end_column - start_column


def compute_column_counts(make_table, data, width):
    """
    Return an iterable of column counts representing how a table constructed
    from the given data should be split along columns.

    Args:
      make_table: a function that accepts a data argument and returns a
        ReportLab Table object.
      width: the available width.
    """
    column_count = max(len(row) for row in data)

    counts = []
    start_column = 0
    while start_column < column_count:
        count = split_data_vertically(make_table, data, start_column, width=width, column_count=column_count)
        counts.append(count)
        start_column += count

    return counts


def split_table_vertically(make_table, table, column_counts):
    """
    Split a Table object along columns.

    Returns a list of new Table objects.

    Args:
      make_table: a function that accepts a data argument and returns a
        ReportLab Table object.
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
        table = make_table(new_data)
        tables.append(table)
        start = stop

    table.last_in_row = True

    return tables


class CanvasState:

    def __init__(self):
        self.page_column = 1
        self.page_row = 1

    def get_page_size(self, canvas):
        # TODO: is it okay to depend on this internal API?
        return canvas._pagesize

    def _write_page_number(self, canvas):
        page_number = canvas.getPageNumber()

        text = f'Page {page_number} [row {self.page_row}: col {self.page_column}]'
        _log.debug(f'writing page number: {text})')

        # Center the page number near the very bottom.
        page_width = self.get_page_size(canvas)[0]
        width = canvas.stringWidth(text)
        x = (page_width - width) / 2
        canvas.drawString(x, 0.5 * inch, text)

    def onFirstPage(self, canvas, document):
        self._write_page_number(canvas)

    def onLaterPages(self, canvas, document):
        self._write_page_number(canvas)


def draw_vertical_text(canvas, text, x=0, y=0):
    """
    Draw text on the canvas vertically.

    Args:
      x: the x coordinates at which to draw.
      y: the y coordinates at which to draw.
    """
    canvas.saveState()
    # Rotate 90 degrees counter-clockwise.
    canvas.rotate(90)
    # Adjust the coordinates after rotating.
    canvas.drawString(y, -1 * x, text)
    canvas.restoreState()


# TODO: incorporate the style.
def wrap_text(canvas, text):
    """
    Return the space taken up by horizontal text.

    Returns: (width, height)
    """
    assert canvas is not None
    width = canvas.stringWidth(text)
    # TODO: compute height.
    height = 20

    return width, height


class TextWrapper:

    """
    An object to help measure the dimensions of text.
    """

    def __init__(self, document):
        """
        Args:
          document: a ReportLab BaseDocTemplate object.
        """
        self.document = document

    @property
    def canvas(self):
        return self.document.canv


class VerticalText(Flowable):

    """
    Represents a single line of unwrapped text.
    """

    def __init__(self, text, text_wrapper=None):
        """
        Args:
          text: a string.
        """
        self.text = text
        self.text_wrapper = text_wrapper

    def wrap(self, available_width, available_height):
        canvas = self.text_wrapper.canvas
        width, height = wrap_text(canvas, self.text)

        # Swap the dimensions to reflect 90-degree rotation.
        return height, width

    def draw(self):
        canvas = self.canv
        draw_vertical_text(canvas, self.text)


# TODO: remove this (it's only for testing).
def make_sample_table_data(row_count, text_wrapper):
    """
    Args:
      rows: the number of data rows.
      text_wrapper: a TextWrapper object.
    """
    column_count = 20
    first_row = [f'Column{i}' for i in range(column_count)]
    # Try some vertical text.
    first_row[0] = VerticalText('Vertical text test...', text_wrapper=text_wrapper)

    data = [first_row]
    for i in range(row_count):
        value = (i + 1) * 10000
        row = [value + j for j in range(20)]
        data.append(row)

    return data


def make_doc_template_factory(path, page_size):
    """
    Return a concrete BaseDocTemplate object.
    """
    # Add a little margin cushion to prevent overflow.
    margin = 0.9 * inch
    margins = {key: margin for key in MARGIN_NAMES}

    def make_doc_template():
        return SimpleDocTemplate(path, pagesize=page_size, **margins)

    return make_doc_template


# TODO: keep working on PDF generation.  This is a scratch function.
def make_pdf(path):
    """
    Args:
      path: a path-like object.
      text: the text to include, as a string.
    """
    # Convert the path to a string for reportlab.
    path = os.fspath(path)

    # canvas = Canvas(path)
    # text = 'Hello, world'
    # draw_vertical_text(canvas, text, x=200, y=200)
    # canvas.save()
    # return

    page_size = DEFAULT_PAGE_SIZE
    make_doc_template = make_doc_template_factory(path, page_size=page_size)

    document = make_doc_template()
    # Do a fake build to set document.canv.
    document.build([])
    text_wrapper = TextWrapper(document=document)
    data = make_sample_table_data(row_count=60, text_wrapper=text_wrapper)

    available = get_available_size(page_size=page_size)
    available_width, available_height = available
    _log.debug(f'computed available width: {available_width} ({available_width / inch} inches)')


    canvas_state = CanvasState()

    class TrackingTable(Table):

        """
        A table that tells CanvasState which table has been drawn.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.last_in_row = False

        def drawOn(self, *args, **kwargs):
            _log.debug('calling: TrackingTable.drawOn()')
            super().drawOn(*args, **kwargs)

            if self.last_in_row:
                canvas_state.page_row += 1
                canvas_state.page_column = 1
            else:
                canvas_state.page_column += 1

    def make_table(data, **kwargs):
        """
        Args:
          **kwargs: additional keyword arguments to pass to the Table
            constructor.
        """
        table = TrackingTable(data, **kwargs)

        table.setStyle(TableStyle([
            # Add grid lines to the table.
            # The third element is the width of the grid lines.
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            # Shade the first (header) row.
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgoldenrodyellow),
        ]))

        return table

    column_counts = compute_column_counts(make_table, data=data, width=available_width)

    table = make_table(data, repeatRows=1)

    # First split the table along rows.
    tables = table.split(*available)

    story = []
    for table in tables:
        # Then split each sub-table along columns, using the column
        # counts we already computed.
        new_tables = split_table_vertically(make_table, table=table, column_counts=column_counts)
        _log.debug(f'split table into {len(new_tables)} tables')

        for new_table in new_tables:
            # Force a page break after each part of the table.
            story.extend([new_table, PageBreak()])

    # Create a new document since we called build() on the first one.
    document = make_doc_template()

    _log.info(f'writing PDF to: {path}')
    document.build(story, onFirstPage=canvas_state.onFirstPage, onLaterPages=canvas_state.onLaterPages)


if __name__ == '__main__':
    # The code below is for testing purposes.
    #
    # To run:
    #
    #     $ python src/orr/writers/pdfwriting.py
    #
    logging.basicConfig(level=logging.DEBUG)
    try:
        path = sys.argv[1]
    except IndexError:
        path = 'sample.pdf'

    make_pdf(path)
