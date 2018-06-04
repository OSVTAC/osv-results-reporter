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


from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import orr.main as main
from orr.utils import SHA256SUMS_FILENAME


# TODO: check recursively.
def get_file_names(dir_path):
    """
    Return the names of the files in the given directory.
    """
    return sorted(path.name for path in dir_path.iterdir())


class EndToEndTest(TestCase):

    """
    Test end-to-end template rendering.
    """

    maxDiff = None

    def assert_files_equal(self, actual_path, expected_path):
        """
        Check that two files have matching content.
        """
        actual_text, expected_text = (path.read_text() for path in (actual_path, expected_path))
        try:
            self.assertEqual(actual_text, expected_text)
        except Exception:
            raise RuntimeError(f'expected path at: {expected_path}')

    def check_directories(self, actual_dir, expected_dir):
        dirs = (actual_dir, expected_dir)
        # First check the file names.
        actual_names, expected_names = (get_file_names(dir_path) for dir_path in dirs)
        self.assertEqual(actual_names, expected_names)

        if SHA256SUMS_FILENAME in actual_names:
            # Then check it last so we can see better diffs.
            actual_names.remove(SHA256SUMS_FILENAME)
            actual_names.append(SHA256SUMS_FILENAME)

        for file_name in actual_names:
            actual_path, expected_path = (dir_path / file_name for dir_path in dirs)
            self.assert_files_equal(actual_path, expected_path)

    def render(self, input_dir, template_dir, extra_template_dirs, output_parent,
        build_time):
        input_paths = [input_dir]
        output_dir_name = 'actual'

        output_data = main.run(input_paths=input_paths,
            template_dir=template_dir, extra_template_dirs=extra_template_dirs,
            output_parent=output_parent, output_dir_name=output_dir_name,
            use_data_model=True, build_time=build_time)

        output_dir = Path(output_data['output_dir'])

        return output_dir

    def test_minimal(self):
        input_dir = Path('sampledata') / 'test-minimal'
        template_dir = Path('templates') / 'test-minimal'
        extra_template_dirs = [template_dir / 'extra']
        expected_dir = Path(__file__).parent / 'expected_minimal'
        # Pass a fixed datetime for build reproducibility.
        build_time = datetime(2018, 6, 1, 20, 48, 12)

        with TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            actual_dir = self.render(input_dir=input_dir,
                template_dir=template_dir, extra_template_dirs=extra_template_dirs,
                output_parent=temp_dir, build_time=build_time)

            self.check_directories(actual_dir, expected_dir)
