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
        data = {}
        actual = datamodel.parse_date(data, 'date', '2016-11-08')
        self.assertEqual(type(actual), datetime.date)
        self.assertEqual(actual, datetime.date(2016, 11, 8))

    def test_parse_i18n(self):
        data = {
            'title': 'The Art of Programming',
            'greeting_es': 'Hola',
            'greeting_fr': 'Bonjour',
        }
        expected = {
            'en': 'Hello',
            'es': 'Hola',
            'fr': 'Bonjour'
        }
        actual = datamodel.parse_i18n(data, 'greeting', 'Hello')
        self.assertEqual(actual, expected)
        # Check that the translations were removed.
        self.assertEqual(data, {'title': 'The Art of Programming'})
