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
Test the orr.utils module.
"""

from unittest import TestCase

import orr.utils as utils


class UtilsModuleTest(TestCase):

    """
    Test the functions in orr.utils.
    """

    def test_strip_trailing_whitespace(self):
        cases = [
            # Test the last line ending in a trailing newline.
            ('abc  \ndef\n', 'abc\ndef\n'),
            # Test the last line **not** ending in a trailing newline.
            ('abc  \ndef', 'abc\ndef\n'),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                actual = utils.strip_trailing_whitespace(text)
                self.assertEqual(actual, expected)
