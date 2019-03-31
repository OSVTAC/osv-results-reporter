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
import sys
from tempfile import TemporaryDirectory
from textwrap import dedent
import unittest
from unittest import TestCase

import orr.tests.testhelpers as testhelpers
import orr.utils as utils
from orr.utils import IN_DOCKER, US_LOCALE


class UtilsModuleTest(TestCase):

    """
    Test the functions in orr.utils.
    """

    def test_get_output_path(self):
        output_dir = 'my/path'
        env = testhelpers.make_test_env(output_dir=output_dir)
        actual = utils.get_output_path(env, rel_path='html/index.html')
        self.assertEqual(actual, Path('my/path/html/index.html'))

    def test_truncate(self):
        # Create a string that exceeds the truncation length.
        long_string = 100 * 'a'

        cases = [
            ('abc', "'abc'"),
            # Test a string that exceeds the truncation length.
            (long_string, "'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'..."),
            # Test a non-string.
            ({'a': 1}, '"{\'a\': 1}"'),
            # Test a non-string that exceeds the truncation length.
            ({long_string: 1}, '"{\'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"...'),
        ]
        for obj, expected in cases:
            with self.subTest(obj=obj):
                actual = utils.truncate(obj)
                self.assertEqual(actual, expected)

    def test_format_number(self):
        cases = [
            ((1000, 'C'), '1000'),
            ((1000, US_LOCALE), '1,000'),
        ]
        for (num, loc), expected in cases:
            with self.subTest(num=num, loc=loc):
                with utils.changing_locale(loc):
                    actual = utils.format_number(num)

                self.assertEqual(actual, expected)

    @unittest.skipUnless(IN_DOCKER, 'not running inside our Docker container')
    def test_format_number__locale_de_DE(self):
        """
        Test a locale where the thousands separator is a period.

        This doesn't work on Mac OS X for some reason.  More generally,
        it's only guaranteed to work in our Docker container because we're
        able to configure that environment correctly by installing the
        needed locale.
        """
        num, loc, expected = 1000, 'de_DE.UTF-8', '1.000'

        with utils.changing_locale(loc):
            actual = utils.format_number(num)

        self.assertEqual(actual, expected)

    def test_compute_percent(self):
        cases = [
            ((1, 3), 33.3333333),
            # 0 is allowed for the denominator.
            ((1, 0), 0),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                num, denom = args
                actual = utils.compute_percent(num, denom)
                self.assertAlmostEqual(actual, expected)

    def test_format_percent(self):
        cases = [
            (0, '0.00%'),
            (10, '10.00%'),
            (5.7777, '5.78%'),
        ]
        for percent, expected in cases:
            with self.subTest(percent=percent):
                actual = utils.format_percent(percent)
                self.assertEqual(actual, expected)

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

    # TODO: also test files inside directories.
    def test_directory_sha256sum(self):
        file_infos = [
            ('a.txt', 'aaa'),
            ('b.txt', 'bbb'),
            ('c.txt', 'ccc'),
            ('SHA256SUMS', 'xxx'),
        ]
        exclude_paths = ['a.txt', 'c.txt']
        expected = dedent("""\
        cd2eb0837c9b4c962c22d2ff8b5441b7b45805887f051d39bf133b583baf6860 *SHA256SUMS
        3e744b9dc39389baf0c5a0660589b8402f3dbb49b89b3e75f2c9355852a3c677 *b.txt
        """)
        with TemporaryDirectory() as temp_dir:
            for rel_path, text in file_infos:
                path = Path(temp_dir) / rel_path
                path.write_text(text)

            actual = utils.directory_sha256sum(temp_dir, exclude_paths=exclude_paths)
            self.assertEqual(actual, expected)
