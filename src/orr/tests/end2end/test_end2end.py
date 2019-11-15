#
# Open Source Voting Results Reporter (ORR) - election results report generator
# Copyright (C) 2018, 2019  Chris Jerdonek
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

import orr.scripts.orr_main as main
from orr.utils import SHASUMS_PATH


def get_paths_inside(dir_path, exclude_exts=None):
    """
    Return the paths to all files in the given directory, including
    subdirectories.

    The paths are returned as a sorted list of strings, with the paths
    relative to the given directory.

    Args:
      exclude_exts: an iterable of extensions to exclude (where the leading
        dot **is** included).
    """
    if exclude_exts is None:
        exclude_exts = []

    return sorted(str(path.relative_to(dir_path)) for path in dir_path.glob('**/*')
                  if not path.is_dir() and path.suffix not in exclude_exts)


# TODO: also do an end-to-end test through the CLI and using subprocess?
class EndToEndTest(TestCase):

    """
    Test end-to-end template rendering.
    """

    maxDiff = None

    def assert_files_equal(self, actual_path, expected_path):
        """
        Check that two files have matching content.
        """
        try:
            actual_text, expected_text = (path.read_text() for path in (actual_path, expected_path))
            self.assertEqual(actual_text, expected_text)
        except Exception:
            raise RuntimeError(f'expected path at: {expected_path}')

    def check_directories(self, actual_dir, expected_dir, zip_file_path):
        dirs = (actual_dir, expected_dir)

        # First check the file names.
        # Exclude generated PDF files so we don't have to store binary
        # files in source control.  The file's contents are already being
        # checked by virtue of the path being listed in the SHA256SUMS file.)
        # Each iterable is a list of strings (not Path objects).
        actual_rel_paths, expected_rel_paths = (
            get_paths_inside(dir_path) for dir_path in dirs
        )

        # We don't store the binary files in source control, so we need to
        # (1) add them to the expected list manually, and (2) skip them
        # when checking contents.
        files_not_to_check = [zip_file_path, 'sov.pdf']
        expected_rel_paths = sorted(expected_rel_paths + files_not_to_check)

        self.assertEqual(actual_rel_paths, expected_rel_paths)

        for name in files_not_to_check:
            actual_rel_paths.remove(name)

        # Move the files that contain secure file hashes to the end of the
        # list so that the file diff we see is more informative (i.e.
        # not just a difference in hash values).
        # In particular, make SHASUMS_PATH the very last file checked.
        for name in ('index.html', str(SHASUMS_PATH)):
            if name in actual_rel_paths:
                actual_rel_paths.remove(name)
                actual_rel_paths.append(name)

        for rel_path in actual_rel_paths:
            actual_path, expected_path = (dir_path / rel_path for dir_path in dirs)
            self.assert_files_equal(actual_path, expected_path)

    def render(self, input_dir, template_dir, extra_template_dirs, output_dir,
        build_time):

        output_data, output = main.run(input_dir=input_dir,
            template_dir=template_dir, extra_template_dirs=extra_template_dirs,
            output_dir=output_dir, build_time=build_time, deterministic=True)

        return output_data

    def test_minimal(self):
        input_dir = Path('sampledata') / 'test-minimal'
        template_dir = Path('templates') / 'test-minimal'
        extra_template_dirs = [template_dir / 'extra']
        expected_dir = Path(__file__).parent / 'expected_minimal'
        # Pass a fixed datetime for build reproducibility.
        build_time = datetime(2018, 6, 1, 20, 48, 12)
        expected_zip_path = 'full-results.tar.gz'

        with TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            output_dir = temp_dir / 'actual'
            output_data = self.render(input_dir=input_dir,
                template_dir=template_dir, extra_template_dirs=extra_template_dirs,
                output_dir=output_dir, build_time=build_time)

            self.assertEqual(expected_zip_path, output_data['zip_file'])
            actual_dir = Path(output_data['output_dir'])

            self.check_directories(actual_dir, expected_dir, zip_file_path=expected_zip_path)
