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
Test the orr.models.rcvresults module.
"""

from unittest import TestCase

from orr.datamodel import Candidate, ResultStatType, ResultsMapping
import orr.models.rcvresults as rcvresults
from orr.models.rcvresults import RCVResults


# This is meant for four candidates.
SAMPLE_RCV_TOTALS = [
    (10000, 2000, 600, 800, 400, 200),
    (10000, 1900, 650, 820, 430, None),
    (10000, 1850, None, 1120, 730, None),
]


class RCVResultsTest(TestCase):

    """
    Test the RCVResults class.
    """

    def make_test_candidates(self):
        candidates = []
        names = [
            'ALICE GOMEZ',
            'BOB CHIN',
            'CATHY SMITH',
            'DAVID WEST',
        ]
        for index, name in enumerate(names):
            _id = 100 + index
            candidate = Candidate()
            candidate.id = _id
            candidate.index = index
            candidate.ballot_title = name
            candidates.append(candidate)

        return candidates

    def make_test_result_stat_types(self):
        """
        Return an iterable of ResultStatType objects for testing.
        """
        return [
            ResultStatType(20, heading='Registered'),
            ResultStatType(21, heading='Continuing'),
        ]

    def make_test_results(self):
        """
        Return an RCVResults object for testing.
        """
        candidates = self.make_test_candidates()
        choice_count = len(candidates)
        result_stat_types = self.make_test_result_stat_types()
        results_mapping = ResultsMapping(result_stat_types, choice_count=choice_count)
        rcv_results = RCVResults(SAMPLE_RCV_TOTALS, results_mapping, candidates=candidates)

        return rcv_results

    def test_find_max_round(self):
        rcv_results = self.make_test_results()
        candidates = rcv_results.candidates

        cases = [
            (0, 2),
            (1, 3),
            (2, 3),
            (3, 1),
        ]
        for index, expected in cases:
            with self.subTest(index=index):
                candidate = candidates[index]
                actual = rcv_results.find_max_round(candidate)
                self.assertEqual(actual, expected)

    def test_get_candidate_total(self):
        rcv_results = self.make_test_results()
        candidates = rcv_results.candidates
        candidate = candidates[1]
        actual = rcv_results.get_candidate_total(candidate, round_num=2)
        self.assertEqual(actual, 820)

    def test_get_candidate_round(self):
        rcv_results = self.make_test_results()
        candidates = rcv_results.candidates
        candidate = candidates[1]
        round_total = rcv_results.get_candidate_round(candidate, round_num=2)
        self.assertEqual(round_total.votes, 820)
        self.assertEqual(round_total.transfer, 20)

    def test_get_candidate_round(self):
        """
        Test the first round.
        """
        rcv_results = self.make_test_results()
        candidates = rcv_results.candidates
        candidate = candidates[1]
        round_total = rcv_results.get_candidate_round(candidate, round_num=1)
        self.assertEqual(round_total.votes, 800)
        self.assertEqual(round_total.transfer, 800)
