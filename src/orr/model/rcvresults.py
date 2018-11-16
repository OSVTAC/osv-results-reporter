# -*- coding: utf-8 -*-
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
Model classes to support RCV contest results.
"""

class RoundTotal:

    # TODO: also include status like: elected, eliminated, etc.
    def __init__(self, votes, transfer):
        self.transfer = transfer
        self.votes = votes

    def percent_continuing(self, continuing):
        # TODO
        pass


class RCVResults:

    def __init__(self, rcv_totals, results_mapping, candidates):
        """
        Args:
          rcv_totals: the raw RCV round totals, as a list of tuples, one for
            each round, starting with the first round.
          results_mapping: a ResultsMapping object, which encodes the
            positions of candidates and stats within the rcv_totals
            data structure.
          candidates: a list of Candidate objects.
        """
        self.rcv_totals = rcv_totals
        self.results_mapping = results_mapping
        self.candidates = candidates

    def get_candidate_total(self, candidate, round_num):
        """
        Return a candidate's vote total in a round.
        """
        round_totals = self.rcv_totals[round_num - 1]
        index = self.results_mapping.get_candidate_index(candidate)

        return round_totals[index]

    def get_candidate_round(self, candidate, round_num):
        """
        Return a RoundTotal object.
        """
        total = self.get_candidate_total(candidate, round_num=round_num)
        if round_num == 1:
            prev_total = 0
        else:
            prev_total = self.get_candidate_total(candidate, round_num=(round_num - 1))

        transfer = total - prev_total
        round_total = RoundTotal(total, transfer=transfer)

        return round_total

