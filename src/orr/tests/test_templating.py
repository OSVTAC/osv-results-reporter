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

from pathlib import Path
from unittest import TestCase

import orr.configlib as configlib
import orr.templating as templating


class TemplatingModuleTest(TestCase):

    """
    Test the functions in orr.templating.
    """

    def make_test_env(self, output_dir):
        """
        Return a Jinja2 Environment object for testing.
        """
        return configlib.create_jinja_env(output_dir)

    def test_get_output_path(self):
        output_dir = 'my/path'
        env = self.make_test_env(output_dir=output_dir)
        actual = templating.get_output_path(env, rel_path='html/index.html')
        self.assertEqual(actual, Path('my/path/html/index.html'))

    def test_output_file_uri(self):
        # Use an absolute path for this test so we can know the complete
        # return value.
        output_dir = '/my/path'
        env = self.make_test_env(output_dir=output_dir)
        actual = templating.output_file_uri(env, rel_path='html/index.html')
        self.assertEqual(actual, 'file:///my/path/html/index.html')
