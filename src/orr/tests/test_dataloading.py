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
Test the orr.datamodel module.
"""

import datetime
import io
from textwrap import dedent
from unittest import TestCase

import orr.dataloading as dataloading
from orr.tsvio import TSVStream


class DataModelModuleTest(TestCase):

    """
    Test the functions in orr.datamodel.
    """

    def test_parse_date(self):
        data = {}
        actual = dataloading.parse_date(None, '2016-11-08')
        self.assertEqual(type(actual), datetime.date)
        self.assertEqual(actual, datetime.date(2016, 11, 8))

    def test_load_rcv_results(self):
        text = dedent("""\
        area_id\tsubtotal_type\tRSReg\tRSCst\t1000:ALICE GOMEZ\t1001:BOB CHIN\t1002:CATHY SMITH\t1003:DAVID WEST
        RCV3\tTO\t10000\t6000\t\t800\t300
        RCV2\tTO\t10000\t6000\t500\t800\t300
        RCV1\tTO\t10000\t6000\t500\t800\t300\t200
        """)
        expected = [
            (10000, 6000, None, 800, 300, None),
            (10000, 6000, 500, 800, 300, None),
            (10000, 6000, 500, 800, 300, 200),
        ]
        stream = io.StringIO(text)
        tsv_stream = TSVStream(stream)
        iter_rows = iter(tsv_stream)

        # Advance past the header line.
        next(iter_rows)

        actual = list(dataloading.read_rcv_results(tsv_stream, iter_rows, rounds=3))
        self.assertEqual(actual, expected)
