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
Test the orr.datamodel module.
"""

import datetime
from unittest import TestCase

import orr.datamodel as datamodel
from orr.datamodel import (Area, Choice, Contest, ReportingGroup, SubstitutionString,
    VotingGroup)


class DataModelModuleTest(TestCase):

    """
    Test the functions in orr.datamodel.
    """

    def test_get_path_difference(self):
        """
        Test the typical case.
        """
        obj1, obj2, obj3, obj4, obj5 = ([i] for i in range(5))
        old_seq = [obj1, obj2, obj3]
        new_seq = [obj1, obj2, obj4, obj5]

        expected = [
            (3, obj4),
            (4, obj5),
        ]
        actual = datamodel.get_path_difference(new_seq, old_seq)
        self.assertEqual(actual, expected)

    def test_get_path_difference__new_is_subset(self):
        """
        Test the new path being a proper subset.
        """
        objects = [[i] for i in range(4)]
        old_seq = objects
        new_seq = objects[:2]

        # Then no elements are new.
        expected = []
        actual = datamodel.get_path_difference(new_seq, old_seq)
        self.assertEqual(actual, expected)

    def test_get_path_difference__new_is_superset(self):
        """
        Test the new path being a proper superset.
        """
        objs = [[i] for i in range(4)]
        old_seq = objs[:2]
        new_seq = objs

        expected = [
            (3, objs[2]),
            (4, objs[3]),
        ]
        actual = datamodel.get_path_difference(new_seq, old_seq)
        self.assertEqual(actual, expected)


class ReportingGroupTest(TestCase):


    def test_display(self):
        cases = [
            # Test the common case.
            (('PCT1141', 'Precinct 1141', 'EV', 'Early Voting'),
             'Precinct 1141 - Early Voting'),
            # Test with Area id equal to "*".
            (('*', 'All Precincts', 'EV', 'Early Voting'),
             'All Precincts - Early Voting'),
            # Test with VotingGroup id equal to "TO".
            (('PCT1141', 'Precinct 1141', 'TO', 'Total'),
             'Precinct 1141'),
            # Test with Area id equal to "*" **and** VotingGroup id equal to "TO".
            (('*', 'All Precincts', 'TO', 'Total'),
             'All Precincts - Total'),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                area_id, area_short_name, voting_id, voting_heading = args
                area = Area(id_=area_id, short_name=area_short_name)
                voting_group = VotingGroup(id_=voting_id, heading=voting_heading)

                rg = ReportingGroup(area, voting_group)
                actual = rg.display()
                self.assertEqual(actual, expected)


class ChoiceTest(TestCase):

    def test_repr(self):
        title = {
            'en': 'English text ' + 100 * 'a',
            'es': 'Spanish',
        }
        contest = None  # The contest isn't important for this test.
        choice = Choice(contest=contest)
        choice.id = 100
        choice.ballot_title = title
        expected = "<Choice id=100 title=[en]'English text aaaaaaaaaaaaaaaaaaaaaaaaaaa'...>"
        actual = repr(choice)
        self.assertEqual(actual, expected)


class ContestTest(TestCase):

    def test_contest_name__with_subtitle(self):
        contest = Contest(id_=1, type_name='item', election=object())
        contest.ballot_title = 'Board Member'
        contest.ballot_subtitle = 'District 2'

        actual = contest.contest_name
        expected = SubstitutionString('{} - {}', data=('Board Member', 'District 2'))
        self.assertEqual(actual, expected)

    def test_contest_name__without_subtitle(self):
        contest = Contest(id_=1, type_name='item', election=object())
        contest.ballot_title = 'Board Member'

        actual = contest.contest_name
        expected = SubstitutionString('{}', data=('Board Member', ))
        self.assertEqual(actual, expected)

    def test_make_header_path(self):
        # A real Election object isn't needed, so pass any non-None value.
        item1, item2, item3 = (Contest(id_=i, type_name='item', election='xxx') for i in range(3))
        item2.parent_header = item1
        item3.parent_header = item2

        expected = [item1, item2]
        actual = item3.make_header_path()
        self.assertEqual(actual, expected)

    def test_get_new_headers(self):
        # A real Election object isn't needed, so pass any non-None value.
        item1, item2, item3, item4, item5 = (Contest(id_=i, type_name='item', election='xxx') for i in range(1, 6))
        item2.parent_header = item1
        item3.parent_header = item2

        item4.parent_header = item1
        item5.parent_header = item4

        header_path = item3.make_header_path()

        expected = [
            (2, item4),
        ]
        actual = item5.get_new_headers(header_path)
        self.assertEqual(actual, expected)
