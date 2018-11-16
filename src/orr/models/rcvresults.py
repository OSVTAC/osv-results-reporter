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
    def __init__(self, votes, transfer, continuing, after_eliminated=False):
        """
        Args:
          after_eliminated: whether this is a placeholder round for a
            candidate after they have been eliminated.  This is useful
            for showing the negative transfer when a candidate has been
            eliminated.
        """
        self.continuing = continuing
        self.after_eliminated = after_eliminated
        self.transfer = transfer
        self.votes = votes

    @property
    def percent(self):
        return 100 * (self.votes / self.continuing)


class RCVResults:

    def __init__(self, rcv_totals, results_mapping, candidates, continuing_stat):
        """
        Args:
          rcv_totals: the raw RCV round totals, as a list of tuples, one for
            each round, starting with the first round.
          results_mapping: a ResultsMapping object, which encodes the
            positions of candidates and stats within the rcv_totals
            data structure.
          candidates: a list of Candidate objects.
          continuing_stat: the ResultStatType object corresponding to
            continuing ballots in each round.
        """
        self.candidates = candidates
        self.continuing_stat = continuing_stat
        self.results_mapping = results_mapping
        self.rcv_totals = rcv_totals

    def get_continuing_index(self):
        return self.results_mapping.get_stat_index(self.continuing_stat)

    def get_round_totals(self, round_num):
        return self.rcv_totals[round_num - 1]

    def get_continuing_total(self, round_num):
        """
        Return the continuing total for a round.
        """
        round_totals = self.get_round_totals(round_num)
        index = self.get_continuing_index()

        return round_totals[index]

    def get_candidate_total(self, candidate, round_num):
        """
        Return a candidate's vote total in a round.
        """
        round_totals = self.get_round_totals(round_num)
        index = self.results_mapping.get_candidate_index(candidate)

        return round_totals[index]

    # TODO: remove this.
    def get_candidate_round(self, candidate, round_num):
        """
        Return a RoundTotal object.
        """
        total = self.get_candidate_total(candidate, round_num=round_num)
        continuing = self.get_continuing_total(round_num)
        if round_num == 1:
            prev_total = 0
        else:
            prev_total = self.get_candidate_total(candidate, round_num=(round_num - 1))

        transfer = total - prev_total
        round_total = RoundTotal(total, transfer=transfer, continuing=continuing)

        return round_total

    def get_candidate_rounds(self, candidate):
        """
        Return a list of RoundTotal objects.
        """
        index = self.results_mapping.get_candidate_index(candidate)
        continuing_index = self.get_continuing_index()

        rounds = []
        after_eliminated = False
        prev_total = 0
        for round_totals in self.rcv_totals:
            total = round_totals[index]
            if total is None:
                total = 0
                after_eliminated = True

            transfer = total - prev_total
            continuing = round_totals[continuing_index]
            round_total = RoundTotal(total, transfer=transfer, continuing=continuing,
                                     after_eliminated=after_eliminated)
            rounds.append(round_total)
            if after_eliminated:
                break

            prev_total = total

        return rounds

    def find_max_round(self, candidate):
        """
        Return the max round for a choice, as a (1-based) integer round number.

        Args:
          candidate: a Candidate object.
        """
        rounds = self.get_candidate_rounds(candidate)
        round_num = len(rounds)
        if rounds[-1].after_eliminated:
            # Then don't count the last round.
            round_num -= 1

        return round_num

    def compute_max_rounds(self):
        """
        Return a dict mapping choice_id to max round.

        Args:
          rcv_results: an RCVResults object.
        """
        max_rounds = {}
        for candidate in self.candidates:
            max_round = self.find_max_round(candidate)
            max_rounds[candidate.id] = max_round

        return max_rounds

    def compute_order_info(self):
        """
        Return (candidates, max_rounds), where candidates is the list
        of candidates in sorted order (starting with the winner), and
        max_rounds is a dict mapping candidate id to the number of the
        highest round the candidate reached.
        """
        max_rounds = self.compute_max_rounds()

        def key(candidate):
            """
            A comparison key function to sort choices first by round
            (starting with the highest), followed by vote total (starting
            with the highest), followed by id (starting with the lowest).
            """
            max_round = max_rounds[candidate.id]
            return (-1 * max_round, -1 * self.get_candidate_total(candidate, max_round), candidate.id)

        candidates = sorted(self.candidates, key=key)

        return (candidates, max_rounds)

    def compute_candidate_order(self):
        candidates, max_rounds = self.compute_order_info()

        return candidates
