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


def get_paths_inside(dir_path, exclude_exts=None):
    """
    Return the paths to all files in the given directory, recursively.

    The paths returned are relative to the given directory, and sorted.

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

    def check_directories(self, actual_dir, expected_dir):
        dirs = (actual_dir, expected_dir)

        # First check the file names.
        # Exclude generated PDF files so we don't have to store binary
        # files in source control.  The file's contents are already being
        # checked by virtue of the path being listed in the SHA256SUMS file.)
        actual_rel_paths, expected_rel_paths = (
            get_paths_inside(dir_path, exclude_exts=['.pdf']) for dir_path in dirs
        )

        self.assertEqual(actual_rel_paths, expected_rel_paths)

        # Move the files that contain secure file hashes to the end of the
        # list so that the file diff we see is more informative (i.e.
        # not just a difference in hash values).
        # In particular, make SHA256SUMS_FILENAME the very last file checked.
        for name in ('index.html', SHA256SUMS_FILENAME):
            if name in actual_rel_paths:
                actual_rel_paths.remove(name)
                actual_rel_paths.append(name)

        for rel_path in actual_rel_paths:
            actual_path, expected_path = (dir_path / rel_path for dir_path in dirs)
            self.assert_files_equal(actual_path, expected_path)

    def render(self, input_dir, template_dir, extra_template_dirs, output_parent,
        build_time):
        input_paths = [input_dir]
        output_dir_name = 'actual'

        output_data = main.run(input_paths=input_paths,
            template_dir=template_dir, extra_template_dirs=extra_template_dirs,
            output_parent=output_parent, output_dir_name=output_dir_name,
            build_time=build_time, deterministic=True)

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
