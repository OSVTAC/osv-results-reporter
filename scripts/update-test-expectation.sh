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
    orr-docker --input-dir sampledata/test-minimal \
        --template-dir templates/test-minimal \
        --extra-template templates/test-minimal/extra \
        --output-parent src/orr/tests/end2end --output-subdir expected_minimal \
        --orr --debug --deterministic --build-time "2018-06-01 20:48:12" \
        || { echo 'running orr failed' ; exit 1; }
else
    orr --input-dir sampledata/test-minimal \
        --template-dir templates/test-minimal \
        --extra-template templates/test-minimal/extra \
        --output-parent src/orr/tests/end2end --output-subdir expected_minimal \
        --debug --deterministic --build-time "2018-06-01 20:48:12"  \
        || { echo 'running orr failed' ; exit 1; }
fi

# Remove the binary files so they're not accidentally stored in source control.
rm src/orr/tests/end2end/expected_minimal/sov.pdf \
    || { echo 'removing sov.pdf file failed' ; exit 1; }

rm src/orr/tests/end2end/expected_minimal/full-results.tar.gz \
    || { echo 'removing tar.gz file failed' ; exit 1; }

git add src/orr/tests/end2end/expected_minimal/ \
    || { echo 'git-add failed' ; exit 1; }

# Show the diff with the test expectation directory.
git diff --cached src/orr/tests/end2end/expected_minimal \
    || { echo 'git-diff failed' ; exit 1; }
