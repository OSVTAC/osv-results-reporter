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
Contains end-to-end tests (e.g. of template rendering).
"""


from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import orr.main as main


def get_file_names(dir_path):
    """
    Return the names of the files in the given directory.
    """
    return sorted(path.name for path in dir_path.iterdir())


class EndToEndTest(TestCase):

    """
    Test end-to-end template rendering.
    """

    def render(self, input_dir, template_dir, extra_template_dirs, output_parent):
        input_paths = [input_dir]
        output_dir_name = 'actual'

        output_dir = main.run(input_paths=input_paths,
            template_dir=template_dir, extra_template_dirs=extra_template_dirs,
            output_parent=output_parent, output_dir_name=output_dir_name,
            use_data_model=True)

        return output_dir

    def test_minimal(self):
        input_dir = Path('sampledata') / 'test-minimal'
        template_dir = Path('templates') / 'test-minimal'
        extra_template_dirs = [template_dir / 'extra']
        expected_dir = Path(__file__).parent / 'expected_minimal'

        with TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            actual_dir = self.render(input_dir=input_dir,
                template_dir=template_dir, extra_template_dirs=extra_template_dirs,
                output_parent=temp_dir)

            # TODO: also check the file contents.

            # Check the file names.
            expected_names = get_file_names(expected_dir)
            actual_names = get_file_names(actual_dir)
            self.assertEqual(actual_names, expected_names)
