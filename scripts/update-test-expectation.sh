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

# This script is to regenerate the test expectation for the end-to-end
# test in ORR's unit test suite.
#
# See the repository's README for details.

set -x

# Allow the script to continue if git-rm fails in case the directory
# is already empty.
git rm --force --ignore-unmatch -r src/orr/tests/end2end/expected_minimal \
    || { echo 'git-rm failed' ; exit 1; }

if [ "$1" == "docker" ];
then
    docker build -t orr .
    docker rm orr_test_builder
    docker run --name orr_test_builder orr --debug --input sampledata/test-minimal \
        --build-time "2018-06-01 20:48:12" --deterministic \
        --template templates/test-minimal \
        --extra templates/test-minimal/extra \
        --output-dir expected_minimal \
        || { echo 'running orr failed' ; exit 1; }
    docker cp orr_test_builder:/app/_build/expected_minimal/. src/orr/tests/end2end/expected_minimal
else
    orr --debug --input sampledata/test-minimal \
        --build-time "2018-06-01 20:48:12" --deterministic \
        --template templates/test-minimal \
        --extra templates/test-minimal/extra \
        --output-parent src/orr/tests/end2end --output-dir expected_minimal \
        || { echo 'running orr failed' ; exit 1; }
fi

git add src/orr/tests/end2end/expected_minimal/ \
    || { echo 'git-add failed' ; exit 1; }

# Show the diff with the test expectation directory.
git diff --cached src/orr/tests/end2end/expected_minimal \
    || { echo 'git-diff failed' ; exit 1; }
