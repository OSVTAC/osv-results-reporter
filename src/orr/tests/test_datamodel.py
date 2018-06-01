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
from unittest import TestCase

import orr.datamodel as datamodel


class DataModelModuleTest(TestCase):

    """
    Test the functions in orr.datamodel.
    """

    def test_parse_date(self):
        data = {'date-xxx': '2016-11-08'}
        actual = datamodel.parse_date(data, 'date-xxx')
        self.assertEqual(type(actual), datetime.date)
        self.assertEqual(actual, datetime.date(2016, 11, 8))
        # Check that the date was removed from the dict.
        self.assertEqual(data, {})

    def test_parse_date__missing(self):
        """
        Check the date being missing from the dict.
        """
        data = {}
        actual = datamodel.parse_date(data, 'date-xxx')
        self.assertIsNone(actual)
