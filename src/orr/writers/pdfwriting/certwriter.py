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
Support for creating the charts needed for the PDF certification letter.
"""

import logging
import sys

import reportlab.lib.colors as colors
from reportlab.platypus import (Flowable, PageBreak, Paragraph, SimpleDocTemplate,
    Table, TableStyle)

import orr.utils as utils


_log = logging.getLogger(__name__)

THICKNESS_0 = 0.5
THICKNESS_1 = 1.5
THICKNESS_2 = 2
DEFAULT_COLOR = colors.black


def make_horizontal_line(coord, thickness, count=None, top=False):
    if count is None:
        count = 1

    command = 'LINEABOVE' if top else 'LINEBELOW'

    if count < 0:
        x_coord = count
    else:
        x_coord = coord[0] - 1 + count

    end_coord = (x_coord, coord[1])

    return (command, coord, end_coord, thickness, DEFAULT_COLOR)


def make_vertical_line(coord, thickness, count=None, left=False):
    if count is None:
        count = 1

    command = 'LINEBEFORE' if left else 'LINEAFTER'

    if count < 0:
        y_coord = -1
    else:
        y_coord = coord[1] - 1 + count

    end_coord = (coord[0], y_coord)

    return (command, coord, end_coord, thickness, DEFAULT_COLOR)


def make_line_below_style(coord, thickness, count=None):
    if count is None:
        count = 1

    end_coord = (coord[0] - 1 + count, coord[1])

    return ('LINEBELOW', coord, coord, thickness, DEFAULT_COLOR)


def make_line_after_style(coord, thickness, count=None):
    if count is None:
        count = 1

    end_coord = (coord[0], coord[1] - 1 + count)

    return ('LINEAFTER', coord, end_coord, thickness, DEFAULT_COLOR)


def make_box_style(coord, thickness, columns=None):
    if columns is None:
        columns = 1

    end_coord = (coord[0] - 1 + columns, -1)

    return ('BOX', coord, end_coord, thickness, DEFAULT_COLOR)


def get_number_rounds(summary_totals):
    """
    Compute and return the number of rounds.
    """
    return len(summary_totals[0]) - 2


# TODO: test this.
def make_table_data(choice_totals, summary_totals, last_round):
    rounds = get_number_rounds(summary_totals)

    data = [
        ('', 'Round 0', '', 'Round 1', '', f'Final Round ({last_round})', ''),
        ('Candidates',) + 3 * ('Votes', '%'),
    ]
    data.extend(choice_totals)

    for totals in summary_totals:
        header = totals[0]
        row = [header]
        for value in totals[1:]:
            row.extend((value, ''))
        data.append(row)
        data.append(len(row) * ('', ))

    if totals:
        data.pop()

    return data


def make_vertical_line_styles(rounds, last_choice_row):
    """
    Args:
      rounds: the number of rounds.
    """
    # The info for these vertical lines is ordered from left to right.
    infos = [
        ((0, 1), dict(count=-1, left=True)),
        ((1, 0), dict(count=-1, left=True)),
    ]
    for i in range(1, rounds + 1):
        row = ((2 * i, 0), dict(count=-1))
        infos.append(row)

    i = 2 * i + 1
    infos.extend([
        ((i, last_choice_row + 1), dict(count=-1)),
        ((i + 1, 0), dict(count=(last_choice_row + 1))),
    ])

    styles = []
    for *args, kwargs in infos:
        kwargs.update(thickness=THICKNESS_1)
        row = make_vertical_line(*args, **kwargs)
        styles.append(row)

    return styles


# TODO: simplify this implementation using generators.
def make_table_styles(choice_totals, summary_totals):
    rounds = get_number_rounds(summary_totals)
    last_choice_row = len(choice_totals) + 2 - 1

    styles = []

    infos = [
        # The grid for the first row.
        ((1, 0), (-1, 1)),
        ((0, 1), (-2, -1)),
        # The grid for the last column.
        ((-1, 1), (-1, last_choice_row)),
    ]
    for coords in infos:
        row = ('GRID',) + coords + (THICKNESS_0, DEFAULT_COLOR)
        styles.append(row)

    # The info for these horizontal lines is ordered from top to bottom.
    infos = [
        ((1, 0), THICKNESS_1, dict(count=-1, top=True)),
        ((0, 1), THICKNESS_1, dict(top=True)),
        ((0, 1), THICKNESS_2, dict(count=-1)),
        ((-1, last_choice_row), THICKNESS_1, dict()),
        ((0, -1), THICKNESS_1, dict(count=-2)),
    ]
    for *args, kwargs in infos:
        row = make_horizontal_line(*args, **kwargs)
        styles.append(row)

    new_styles = make_vertical_line_styles(rounds, last_choice_row=last_choice_row)
    styles.extend(new_styles)

    for i in range(0, rounds):
        i = 2 * i + 1
        row = ('SPAN', (i, 0), (i + 1, 0))
        styles.append(row)

    # ('ALIGN', (0, 0), (-1, 1), 'CENTER'),

    return styles


def format_choice_totals(choice_totals):
    new_rows = []
    for row in choice_totals:
        iterator = iter(row)
        new_row = [next(iterator)]
        while True:
            try:
                total = next(iterator)
            except StopIteration:
                break

            total = utils.format_number(total)
            new_row.append(total)

            percent = next(iterator)
            percent = utils.format_percent(percent)
            new_row.append(percent)

        new_rows.append(new_row)

    return new_rows


# TODO: finish implementing this.
def make_table(choice_totals, summary_totals, last_round):
    choice_totals = format_choice_totals(choice_totals)

    data = make_table_data(choice_totals, summary_totals, last_round=last_round)

    table = Table(data)
    styles = make_table_styles(choice_totals, summary_totals)

    table.setStyle(TableStyle(styles))

    return table


# TODO: remove this when no longer needed.
if __name__ == '__main__':
    import locale

    from orr.utils import US_LOCALE

    locale.setlocale(locale.LC_ALL, US_LOCALE)
    logging.basicConfig(level=logging.INFO)

    try:
        path = sys.argv[1]
    except IndexError:
        path = 'sample.pdf'

    # Create some sample data for testing.
    choice_totals = [
        ('AAA', 10000, 30.01, 12000, 31.2, 11000, 35),
        ('BBB', 7000, 25, 8000, 21, 9000, 25.66),
    ]

    summary_totals = [
        ('Total Votes', 35001, 35100, 35700),
        ('Total Ballots Cast', 40000, 40000, 40000),
    ]

    table = make_table(choice_totals, summary_totals, last_round=4)
    story = [table]
    document = SimpleDocTemplate(path)
    _log.info(f'writing PDF to: {path}')
    document.build(story)
