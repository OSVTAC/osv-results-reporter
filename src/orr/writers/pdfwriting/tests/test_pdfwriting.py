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
Test the orr.writers.pdfwriting.pdfwriter module.
"""

from pathlib import Path
from unittest import TestCase

from reportlab.pdfgen.canvas import Canvas

import orr.writers.pdfwriting.pdfwriter as pdfwriter


class PdfWritingModuleTest(TestCase):

    """
    Test the functions in orr.writers.pdfwriting.pdfwriter.
    """

    def test_wrap_text(self):
        cases = [
            ('Carl Hage', (54.012, 20)),
            ('Chris Jerdonek', (80.688, 20)),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                canvas = Canvas('sample.pdf')
                actual = pdfwriter.wrap_text(canvas, text)
                self.assertEqual(actual, expected)
