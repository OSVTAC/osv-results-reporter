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

from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
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

    def test_parse_datetime(self):
        cases = [
            ('2018-06-01 20:48:12', datetime(2018, 6, 1, 20, 48, 12)),
        ]
        for dt_string, expected in cases:
            with self.subTest(dt_string=dt_string):
                actual = utils.parse_datetime(dt_string)
                self.assertEqual(actual, expected)

    def test_format_date__default(self):
        day = date(2018, 6, 5)
        cases = [
            ('en', 'June 5, 2018'),
            ('es', '5 de junio de 2018'),
            ('tl', 'Hunyo 5, 2018'),
            ('zh', '2018年6月5日'),
        ]
        for lang, expected in cases:
            with self.subTest(lang=lang):
                actual = utils.format_date(day, lang=lang)
                self.assertEqual(actual, expected)

    def test_format_date__medium(self):
        """
        Test passing format_='medium'.
        """
        day = date(2018, 6, 5)
        cases = [
            ('en', 'Jun 5, 2018'),
            ('es', '5 jun. 2018'),
            ('tl', 'Hun 5, 2018'),
            ('zh', '2018年6月5日'),
        ]
        for lang, expected in cases:
            with self.subTest(lang=lang):
                actual = utils.format_date(day, lang=lang, format_='medium')
                self.assertEqual(actual, expected)

    def test_hash_file(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'temp.txt'
            path.write_text('abcdef')
            expected = 'bef57ec7f53a6d40beb640a780a639c83bc29ac8a9816f1fc6c5c6dcd93c4721'

            actual = utils.hash_file(path)
            self.assertEqual(actual, expected)
