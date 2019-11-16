# -*- coding: utf-8 -*-
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
Test the orr.templating module.
"""

from datetime import date
from pathlib import Path, PosixPath
from unittest import TestCase

from jinja2.utils import Namespace

import orr.templating as templating
import orr.tests.testhelpers as testhelpers


class TemplatingModuleTest(TestCase):

    """
    Test the functions in orr.templating.
    """

    def test_output_file_uri(self):
        # Use an absolute path for this test so we can know the complete
        # return value.
        output_dir = '/my/path'

        cases = [
            # Test a path with more than one path part.
            ('html/index.html', 'file:///my/path/html/index.html'),
            # Test a path whose file name contains a space.
            ('Vice President.tsv', 'file:///my/path/Vice%20President.tsv'),
        ]

        env = testhelpers.make_test_env(output_dir=output_dir)
        for rel_path, expected in cases:
            with self.subTest(rel_path=rel_path):
                actual = templating.output_file_uri(env, rel_path=rel_path)
                self.assertEqual(actual, expected)

    def test_format_date(self):
        day = date(2018, 2, 5)
        cases = [
            ('en', 'February 5, 2018'),
            ('es', '5 de febrero de 2018'),
            ('tl', 'Pebrero 5, 2018'),
            ('zh', '2018年2月5日'),
        ]
        for lang, expected in cases:
            with self.subTest(lang=lang):
                context = {'options': Namespace(lang=lang)}

                actual = templating.format_date(context, day)
                self.assertEqual(actual, expected)

    def test_format_date_medium(self):
        day = date(2018, 2, 5)
        cases = [
            ('en', 'Feb 5, 2018'),
            ('es', '5 feb. 2018'),
            ('tl', 'Peb 5, 2018'),
            ('zh', '2018年2月5日'),
        ]
        for lang, expected in cases:
            with self.subTest(lang=lang):
                context = {'options': Namespace(lang=lang)}

                actual = templating.format_date_medium(context, day)
                self.assertEqual(actual, expected)

    def test_get_relative_href(self):
        cases = [
            (('summary.html', 'new.html', 'en'), 'new.html'),
            # Test a rel_path "above" the top level.
            (('summary.html', '../new.html', 'en'), '../new.html'),
            # Test a current page down one level.
            (('details/contest.html', 'new.html', 'en'), '../new.html'),
            # Test a rel_path "above" the top level.
            (('details/contest.html', '../new.html', 'en'), '../../new.html'),
        ]
        for (current_path, rel_path, lang), expected in cases:
            with self.subTest(rel_path=rel_path, lang=lang):
                context = {
                    'default_rel_path': Path(current_path),
                    'options': Namespace(lang=lang),
                }

                actual = templating.get_relative_href(context, rel_path, lang=lang)
                self.assertEqual(type(actual), PosixPath)
                self.assertEqual(str(actual), expected)

    def test_get_home_href(self):
        cases = [
            (('summary.html', 'en'), 'index.html'),
            (('details/contest.html', 'en'), '../index.html'),
            (('details/contest.html', 'es'), '../index-es.html'),
        ]
        for (rel_path, lang), expected in cases:
            with self.subTest(rel_path=rel_path, lang=lang):
                context = {
                    'default_rel_path': Path(rel_path),
                    'options': Namespace(lang=lang),
                }

                actual = templating.get_home_href(context)
                self.assertEqual(type(actual), PosixPath)
                self.assertEqual(str(actual), expected)

    def test_default_contest_path(self):
        class Contest:
            def __init__(self, id):
                self.id = id

        contest = Contest(id=42)

        cases = [
            (None, 'contest-42.html'),
            ('results', 'results/contest-42.html'),
        ]
        for dir_path, expected in cases:
            with self.subTest(dir_path=dir_path):
                actual = templating.default_contest_path(contest, dir_path=dir_path)
                self.assertEqual(actual, expected)
