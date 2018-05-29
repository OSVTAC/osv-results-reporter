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
import random
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


def split_table_along_rows(table, available):
    """
    Split a table along rows, iteratively.

    Returns a list of new Table objects.

    Args:
      table: a Table object.
      available: the space available for each table as a pair (width, height).
    """
    tables = []

    while True:
        new_tables = table.split(*available)
        assert 1 <= len(new_tables) <= 2

        tables.append(new_tables[0])
        if len(new_tables) <= 1:
            break

        table = new_tables[1]

    return tables


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


def split_table_along_columns(make_table, table, column_counts, table_name=None):
    """
    Split a table along columns, iteratively.

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
        table = make_table(new_data, table_name=table_name)
        tables.append(table)
        start = stop

    table.last_in_row = True

    return tables


class CanvasState:

    def __init__(self):
        self._page_row = 1
        self._page_column = 1

        self.table_name = None

    def get_page_size(self, canvas):
        # TODO: is it okay to depend on this internal API?
        return canvas._pagesize

    def start_new_page_row(self):
        self._page_row += 1
        self._page_column = 1

    def write_centered_text(self, canvas, text, height):
        page_width = self.get_page_size(canvas)[0]
        width = canvas.stringWidth(text)
        x = (page_width - width) / 2
        canvas.drawString(x=x, y=height, text=text)

    def write_page_number(self, canvas):
        page_number = canvas.getPageNumber()

        text = f'Page {page_number} [{self._page_row} : {self._page_column}]'
        _log.debug(f'writing page number: {text!r}')

        # Center the page number near the very bottom.
        self.write_centered_text(canvas, text=text, height=(0.5 * inch))

        self._page_column += 1

    def write_page_header(self, canvas):
        page_number = canvas.getPageNumber()
        text = self.table_name
        _log.debug(f'writing page {page_number} header: {text}')

        page_height = self.get_page_size(canvas)[1]
        height = page_height - 0.5 * inch

        self.write_centered_text(canvas, text=text, height=height)

    def onFirstPage(self, canvas, document):
        # TODO: instead do this inside DocumentTemplate.afterPage().
        self.write_page_number(canvas)

    def onLaterPages(self, canvas, document):
        # TODO: instead do this inside DocumentTemplate.afterPage().
        self.write_page_number(canvas)


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


class VerticalText(Flowable):

    """
    Represents a single vertical line of unwrapped text.
    """

    # Require a fixed width and height at the outset so the flowable
    # can be used as the value of a Table cell (so that the Table will
    # be able to wrap correctly, etc).
    def __init__(self, text, width, height):
        """
        Args:
          text: a string.
          width: the width of the text (after being rotated).
          height: the height of the text (after being rotated).
        """
        super().__init__()

        self.width = width
        self.height = height
        self.text = text

    def wrap(self, available_width, available_height):
        # Store the available width and height for the draw() stage.
        self.aw = available_width
        self.ah = available_height

        return (self.width, self.height)

    def draw(self):
        canvas = self.canv
        # Center the text horizontally in the middle of the cell.
        # TODO: also account for the line width.
        x = self.aw / 2
        draw_vertical_text(canvas, self.text, x=x)


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

    def compute_vertical_text_dimensions(self, text):
        """
        Compute and return (width, height).
        """
        # TODO: incorporate the style into the computation.
        width, height = wrap_text(self.canvas, text)

        # Swap the dimensions since the text will be rotated 90-degrees.
        return (height, width)

    def make_vertical_text(self, text, dimensions=None):
        """
        Create and return a VerticalText flowable.
        """
        if dimensions is None:
            dimensions = wrap_text(self.canvas, text)

        width, height = dimensions

        # Swap the dimensions since the text will be rotated 90-degrees.
        vertical_text = VerticalText(text, width=width, height=height)

        return vertical_text


def make_header_row(texts, text_wrapper):
    """
    Return a list of VerticalText objects for use as the header row of
    a Table object.
    """
    # A list of ordered pairs (width, height).
    dimensions = [text_wrapper.compute_vertical_text_dimensions(text) for text in texts]
    max_height = max(dimension[1] for dimension in dimensions)

    vertical_texts = [text_wrapper.make_vertical_text(text, dimensions=(dim[0], max_height))
                      for text, dim in zip(texts, dimensions)]

    return vertical_texts


def prepare_table_data(rows, text_wrapper):
    """
    Args:
      rows: the number of data rows.
      text_wrapper: a TextWrapper object.
    """
    headers = rows[0]
    header_row = make_header_row(headers, text_wrapper=text_wrapper)

    data = [header_row]
    data.extend(rows[1:])

    return data


class DocumentTemplate(SimpleDocTemplate):

    """
    Our customized DocTemplate.
    """

    def afterPage(self):
        # Write the name of the current table at the top of each page.
        self.canvas_state.write_page_header(self.canv)


def make_doc_template_factory(path, page_size, title=None):
    """
    Return a concrete BaseDocTemplate object.
    """
    # Add a little margin cushion to prevent overflow.
    margin = 0.9 * inch
    margins = {key: margin for key in MARGIN_NAMES}

    def make_doc_template(canvas_state=None):
        """
        Args:
          canvas_state: a CanvasState object.
        """
        doc_template = DocumentTemplate(path, pagesize=page_size, title=title, **margins)
        doc_template.canvas_state = canvas_state

        return doc_template

    return make_doc_template


def iter_table_story(data, available, make_table, table_name=None):
    """
    Create and yield "story" elements for a new table.

    Args:
      available: the space available for the table as a pair (width, height).
    """
    assert table_name is not None
    available_width = available[0]

    column_counts = compute_column_counts(make_table, data=data, width=available_width)
    _log.debug(f'will split table along columns into {len(column_counts)}: {column_counts}')

    # Display the header on each page.
    table = make_table(data, table_name=table_name, repeatRows=1)

    # First split the table along rows.
    tables = split_table_along_rows(table, available)
    _log.debug(f'split table along rows into {len(tables)}')

    for table in tables:
        # Then split each sub-table along columns, using the column
        # counts we already computed.
        new_tables = split_table_along_columns(make_table, table=table,
                            column_counts=column_counts, table_name=table_name)

        for new_table in new_tables:
            yield new_table
            # Force a page break after each part of the table.
            yield PageBreak()


def make_pdf(path, contests, title=None):
    """
    Args:
      path: a path-like object.
      contests: an iterable of pairs (contest_name, rows).
      title: an optional title to set on the PDF's properties.
    """
    # Convert the path to a string for reportlab.
    path = os.fspath(path)
    page_size = DEFAULT_PAGE_SIZE

    make_doc_template = make_doc_template_factory(path, page_size=page_size, title=title)

    document = make_doc_template()

    # Do a fake build to set document.canv.
    # TODO: eliminate needing to do the fake build.
    document.build([])
    text_wrapper = TextWrapper(document=document)

    available = get_available_size(page_size=page_size)
    available_width, available_height = available
    _log.debug(f'computed available width: {available_width} ({available_width / inch} inches)')

    # Create a CanvasState for the real build() stage.
    canvas_state = CanvasState()

    class TrackingTable(Table):

        """
        A table that tells CanvasState which table has been drawn.
        """

        def __init__(self, *args, table_name=None, **kwargs):
            super().__init__(*args, **kwargs)

            self.last_in_row = False
            self.table_name = table_name

        def drawOn(self, *args, **kwargs):
            super().drawOn(*args, **kwargs)

            # Set the name of the current table so it's available inside
            # BaseDocTemplate.afterPage() when we write the page header.
            canvas_state.table_name = self.table_name

            if self.last_in_row:
                # The document's onFirstPage() and onLaterPages() functions
                # fire **before** any flowables are drawn (and in particular
                # before start_new_page_row() is called below), so
                # start_new_page_row() below takes effect for the next
                # page and table.
                canvas_state.start_new_page_row()

        # Override Table._calcPreliminaryWidths() to prevent ReportLab
        # from expanding the table columns to fill the entire width of
        # the page.  There doesn't seem to be a nicer way to do this.
        # TODO: find a way to avoid having to use this hack.
        def _calcPreliminaryWidths(self, available_width):
            return super()._calcPreliminaryWidths(availWidth=0)

    def make_table(data, table_name=None, **kwargs):
        """
        Args:
          **kwargs: additional keyword arguments to pass to the Table
            constructor.
        """
        table = TrackingTable(data, table_name=table_name, **kwargs)

        table.setStyle(TableStyle([
            # Add grid lines to the table.
            # The third element is the width of the grid lines.
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            # Shade the first (header) row.
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgoldenrodyellow),
        ]))

        return table

    story = []
    for contest_name, rows in contests:
        assert contest_name is not None
        data = prepare_table_data(rows, text_wrapper=text_wrapper)
        for flowable in iter_table_story(data, available, make_table=make_table, table_name=contest_name):
            story.append(flowable)

    # Create a new document since we called build() on the first one.
    document = make_doc_template(canvas_state=canvas_state)

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
