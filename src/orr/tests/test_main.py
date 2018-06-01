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
Test the orr.main module.
"""

from datetime import datetime
from unittest import TestCase

import orr.main as main


class MainModuleTest(TestCase):

    """
    Test the functions in orr.main.
    """

    def test_generate_output_name(self):
        dt = datetime(2018, 1, 2, 16, 30, 15)
        expected = 'build_20180102_163015'
        actual = main.generate_output_name(dt=dt)
        self.assertEqual(actual, expected)
