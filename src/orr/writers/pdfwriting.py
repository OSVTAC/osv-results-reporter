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

import os

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table


def make_table(row_count):
    """
    Args:
      rows: the number of data rows.
    """
    data = [20 * ('Alice', )]
    for i in range(row_count):
        value = (i + 1) * 1000
        row = 20 * (value, )
        data.append(row)

    table = Table(data)

    return table


# TODO: keep working on PDF generation.  This is a scratch function.
def make_pdf(path, text):
    """
    Args:
      path: a path-like object.
      text: the text to include, as a string.
    """
    # Convert the path to a string for reportlab.
    path = os.fspath(path)
    canvas = Canvas(path)

    table = make_table(row_count=60)

    # tables = table.split(40, 40)
    # tables = [table, table]

    tables = [table]

    # We need to call wrapOn() before calling drawOn().
    result = table.wrapOn(canvas, 300, 300)
    print(f'wrapOn: {result}')

    table.drawOn(canvas, 20, 20)

    canvas.showPage()
    canvas.save()
