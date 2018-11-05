# -*- coding: utf-8 -*-
#
# Open Source Voting Results Reporter (ORR) - election results report generator
# Copyright (C) 2018  Carl Hage
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
Class definitions to represent an election definition, with
contests containing a list of choices, either an OfficeContest with list
of candidates or MeasureContest with list of named choices, usually
yes/no.
"""

from collections import OrderedDict
from datetime import datetime
import logging
import re

import orr.utils as utils
from orr.utils import truncate

_log = logging.getLogger(__name__)


AREA_ID_ALL = '*'
VOTING_GROUP_ID_ALL = 'TO'

# Besides the votes for candidates and measure choices counted, there
# are a set of summary results with ballots not counted by category,
# and a summary result for totals. These have a set of IDs and a generic title.
# For n of m voting (Vote for n), a voter can make n selections, so for
# "vote for 3", if only 1 choice was made, there would be 2 undervotes,
# and if 4 or more choices were made, there would be 3 overvotes
VOTING_STATS = OrderedDict([
    ('RSTot', 'Ballots Counted'),   # Sum of valid votes reported
    ('RSCst', 'Ballots Cast'),      # Ballot sheets submitted by voters
    ('RSReg', 'Registered Voters'), # Voters registered for computing turnout
    ('RSTrn', 'Voter Turnout'),     # (SVCst/SVReg)*100
    ('RSRej', 'Ballots Rejected'),  # Not countable
    ('RSUnc', 'Ballots Uncounted'), # Not yet counted or needing adjudication
    ('RSWri', 'Writein Votes'),     # Write-in candidates not explicitly listed
    ('RSUnd', 'Undervotes'),        # Blank votes or additional votes not made
    ('RSOvr', 'Overvotes'),         # Possible votes rejected by overvoting
    ('RSExh', 'Exhausted Ballots')  # All RCV choices were eliminated (RCV only)
    ])

# Set defining the RESULT_STATS items that are percentages (decimal)
# that should be displayed with a % suffix.
RESULT_STAT_PERCENTAGE = { 'RSTrn' }

# Both detailed reports and contest summary reports might list a vote
# total as well as one or more subtotals. A set of ID/Suffix codes and
# a name/title is predefined. An RCV contest will also have RCV Round subtotals
VOTING_GROUPS = OrderedDict([
    ('TO','Total'),             # Total of all subtotals
    ('ED','Election Day'),      # Election day precinct voting (in county)
    ('MV','Vote by Mail'),      # Vote by mail ballots (in county)
    ('EV','Early Voting'),      # Early voting/vote centers (in county)
    ('IA','In-County Total'),   # Subtotal this county only (multi-county contest)
    ('XA','Other Counties'),    # Votes from other counties (multi-county contest)
    ('PR','Provisional Voting') # Voting with provisional ballot envelopes
    ])


def parse_idlist(idlist):
    """
    Args:
      idlist: space-separated list of IDS, as a string.
    """
    return idlist.split()


# TODO: test this.
def i18n_repr(i18n_text):
    """
    Return a representation suitable for direct inclusion in a __repr__
    value, for example f'<Item title={i18n_repr(self.title)}>'.
    """
    if type(i18n_text) == dict and 'en' in i18n_text:
        # Add a prefix to indicate the English was picked out.
        return '[en]{}'.format(truncate(i18n_text['en']))

    return truncate(i18n_text)


# --- Results reporting group/type definitions ---

class VotingGroup:

    """
    When reporting summary data, the votes reported may include a total
    as well as a set of contest or election configurable subtotals. For
    detailed data with precinct and district breakdowns, each area subtotal
    may have separated subtotal types, e.g. election day precinct voting,
    and vote-by-mail. An object is defined to hold a reference id as well
    as a label.

    Standard IDs are listed with the constant VOTING_GROUPS. The set
    of voting groups subtotaled can be configured per election, and
    might vary by election district (in case of cross-county reporting).

    Instance attributes:

      id:
      heading:
    """

    def __init__(self, id_=None, heading=None):
        self.id = id_
        self.heading = heading


class ResultStatType:

    """
    The ResultStatType represents a type of results statistics value
    computed for a contest, in addition to the vote values totaled
    for each choice. This is an enumerated type with a an i18n
    printable heading.

    Instance attributes:

      id:
      heading:
      is_percent:
    """

    def __init__(self):
        self.id = None
        self.heading = None


class ResultStyle:

    """
    Each contest references the id of a ResultStyle that defines a
    set of attributes for the type of voting including what result stats
    will be available.

    Instance attributes:

      id:
      description:
      is_rcv:
      result_stat_types:
      voting_group_indexes_by_id:
      voting_groups:
    """

    def __init__(self):
        self.id = None
        self.voting_group_indexes_by_id = None

    def __repr__(self):
        return f'<ResultStyle id={self.id!r}>'

    def get_voting_group_by_id(self, id_):
        index = self.voting_group_indexes_by_id[id_]
        voting_group = self.voting_groups[index]

        return voting_group

    def voting_group_ids_from_idlist(self, idlist):
        """
        Return the matching voting group ids, as a list.

        Args:
          idlist: a space-separated list of ids, as a string.
        """
        if (not idlist) or (idlist == "*"):
            # Then return all of the ids, in order.
            return [voting_group.id for voting_group in self.voting_groups]

        # Otherwise, return only the matching ones.
        ids = parse_idlist(idlist)
        ids = [id_ for id_ in ids if id_ in self.voting_group_indexes_by_id]

        return ids

    def voting_group_indexes_from_idlist(self, idlist):
        """
        Returns the list of voting group index values by the
        space-separated list of ids. Unmatched ids are omitted.
        """
        ids = self.voting_group_ids_from_idlist(idlist)
        indexes = [self.voting_group_indexes_by_id[id_] for id_ in ids]

        return indexes

    def voting_groups_from_idlist(self, idlist):
        """
        Returns the list of voting group objects by the
        space-separated list of ids. Unmatched ids are omitted.
        """
        ids = self.voting_group_ids_from_idlist(idlist)
        voting_groups = [self.get_voting_group_by_id(id_) for id_ in ids]

        return voting_groups


class Area:

    """
    The Area object represents any kind of precinct or district
    that corresponds to a geographic area. ID codes for precincts
    and districts must be unique across all types.

    Sometimes we want to access IDs that may be either a precinct
    or district (i.e. a Precinct acts as a district for voting),
    but usually precints and districts are distinct.

    An Area object of classification "Precinct" can represent a base
    precinct, a precinct split (precinct divided into unique combinations of
    intersecting districts), or consolidated precinct -- a group of precincts
    combined for voting and reporting. A consolidated precinct may be the
    same as a base precinct, i.e. have only one precinct.

    A consolidated precinct ID might be shared with a base precinct,
    but when loading data, the precinct list should be either
    consolidated precincts or base precincts. Precinct splits have
    an ID composed of the base preinct and a suffix (either a letter A-Z
    or number, e.g. '03' or with a separator '.03'.

    A precinct might be all "Vote-By-Mail", meaning all voters in that
    precinct use only mail ballots. [In that case there would be
    no election-day precinct voting.] Within a base precinct, it is
    possible that only some precinct splits would be VBM. In that case,
    there might be election day voting for some contests but VBM-only
    for others in that precinct.

    The special ID "*" is used as a placeholder for "All Precincts",
    meaning all precincts associated with a contest, or all precincts
    within an Election Administration (e.g. county).

    Districts:

    An area can also represent a geographic area representing an organization
    (jurisdiction/public agency) as a whole, or a portion of the
    organization representing a seat on a board (e.g. Council District),
    a proposed transfer area (e.g. change of school district), or
    tax assessment area (e.g. for road improvements, School Facilities
    Improvement District). [An SFID is a portion of a school district
    with tax assessment or bond funding certain schools.]

    A district may have is_vbm if all precincts in that district
    are marked as VBM only.

    An area can also represent the geographic area
    for a zip code, or Census Block/Block-Group. Normally data,
    representing zip code associations and/or Census Blocks are
    maintained in separate data lists, but should have IDs within
    the shared Area namespace.

    The voting district for a contest may be associated with a list
    of "reporting groups"

    Attributes:
      id:
      classification:
      name:
      short_name:
      is_vbm:
      consolidated_ids:
      reporting_group_ids:
    """

    reporting_group_pattern = re.compile(r'(.*)~(.*)')

    def __init__(self, id_=None, short_name=None):
        self.id = id_
        self.short_name = short_name

        self.classification = None
        self.name = None
        self.is_vbm = False

    def __repr__(self):
        return f'<Area {self.classification!r}: id={self.id!r}>'

    def iter_reporting_groups(self, areas_by_id, voting_groups_by_id):
        """
        An iterator that creates and yields the reporting groups.
        """
        reporting_group_ids = parse_idlist(self.reporting_group_ids)

        for index, s in enumerate(reporting_group_ids):
            m = self.reporting_group_pattern.match(s)
            try:
                if not m:
                    raise ValueError(f'ReportingGroup id does not match pattern')
                area_id, group_id = m.groups()
                area = areas_by_id[area_id]
                voting_group = voting_groups_by_id[group_id]
                group = ReportingGroup(area, voting_group, index=index)
            except Exception:
                raise RuntimeError(f"error handling ReportingGroup id {s!r} for area {self.id!r}")

            yield group


class ReportingGroup:

    """
    The reporting group defines an (Area, VotingGroup) tuple for
    results subtotals. The Area ID '*' is a special placeholder meaning
    all precincts (in a contest), and VotingGroup 'TO' is used for
    all voters. Each voting district active in an election should have
    a reporting_group_ids string that is a space-separated list of
    area_id~voting_group_id ID pairs that reference a list of (area,group)
    tuples.
    """

    def __init__(self, area, voting_group, index=None):
        """
        Args:
          area: an Area object.
          voting_group: a VotingGroup object.
        """
        self.area = area
        self.voting_group = voting_group
        self.index = index

    def display(self):
        """
        Return the display format for use in a template.

        An example return value is -- "Precinct 1141 - Early Voting".
        """
        text = self.area.short_name
        if self.area.id == AREA_ID_ALL or self.voting_group.id != VOTING_GROUP_ID_ALL:
            text += f' - {self.voting_group.heading}'

        return text


# --- Ballot Item definitions

class Header:

    """
    Attributes:
      id:
      ballot_title:
      classification:

      ballot_items: the child items, which are either Contest objects,
        or other Header objects.
      parent_header: the parent header of the item, as a Header object.
    """

    def __init__(self):
        self.ballot_title = None
        self.ballot_items = []
        self.id = None
        self.parent_header = None

    def __repr__(self):
        return f'<Header id={self.id!r} title={i18n_repr(self.ballot_title)}>'


class Choice:

    """
    Represents a non-candidate selection on a ballot, e.g. Yes/No for
    a ballot measure, retention or recall office.
    Multiple choice for a measure is a selection other than yes/no for
    a pass/fail contest, e.g. preferred name of a proposed city incorporation.

    Besides votes for a candidate or measure choice, a set of vote/ballot
    totals are computed for a set of summary attributes that represent
    rejected votes and totals. The RESULT_STATS contain an id
    (that is distinct from a candidate/choice id) and "ballot_title"
    that can be used as a label in a report analogous to a candidate/choice name.

    Instance attributes:

      id:
      ballot_title:
      contest: back-reference to a Contest object.
    """

    def __init__(self, contest):
        self.contest = contest

        self.ballot_title = None
        self.id = None

    def __repr__(self):
        return f'<Choice id={self.id!r} title={i18n_repr(self.ballot_title)}>'


class Candidate(Choice):

    """
    Represents a candidate selection on a ballot-.

    Instance attributes:

      id:
      ballot_title:
      ballot_designation:
      candidate_party:
      contest: back-reference to a Contest object.
    """

    def __init__(self, contest):
        self.contest = contest

        self.ballot_title = None
        self.id = None

    def __repr__(self):
        return f'<Candidate id={self.id!r} title={i18n_repr(self.ballot_title)}>'


def get_path_difference(new_seq, old_seq):
    """
    Return the sequence items that are **new** compared with the old.
    """
    # Work backwards starting from the end, finding the point at which
    # the two paths first diverge.
    index = min(len(new_seq), len(old_seq)) - 1
    while index >= 0:
        new_item, old_item = (path[index] for path in (new_seq, old_seq))
        if new_item is old_item:
            index += 1
            break
        index -= 1
    else:
        index = 0

    # Return all the items in the new path, starting from where the
    # path first diverged.
    return list(pair for pair in enumerate(new_seq[index:], start=index+1))


class ResultsMapping:

    """
    Encapsulates the association between (1) result stat types and choices,
    and (2) numeric stats / totals.
    """

    def __init__(self, result_stat_type_index_by_id, choice_count):
        """
        Args:
          candidate_index: the first candidate index for the rows in the table.
        """
        self.choice_count = choice_count
        self.result_stat_count = len(result_stat_type_index_by_id)
        self.result_stat_type_index_by_id = result_stat_type_index_by_id

    def get_candidate_index(self, candidate):
        return self.result_stat_count + candidate.index

    def get_indices_by_id(self, label_or_id):
        if label_or_id == '*':
            return list(range(self.result_stat_count))

        if label_or_id == 'CHOICES':
            return list(range(self.result_stat_count,
                              self.result_stat_count + self.choice_count))

        return [self.result_stat_type_index_by_id[label_or_id]]


class Contest:

    """
    Contest is a class that encompasses all contest types: offices, measures,
    and retention/recall. All contests have the following common attributes:

    Attributes:
      id: must be unique across all contests or headers
      type_name: a string indicating the Contest type (see below for
        descriptions).

      ballot_title: text appearing on the ballot representing the contest.
      ballot_subtitle: second level title for this item
      choices: List of choices: candidates or Yes/No etc. on measures
               and recall/retention contests
      header_id: id of the parent header object containing this item
        (or a falsey value for root).
      parent_header: the parent header of the item, as a Header object.
      rcv_results: a list of tuples, one for each round, starting with the
        last round.

    Private attributes:
      _load_contest_results_data: a function that loads the results details
        for the contest.  The function should have signature: load(contest).

    A Contest with type_name "office" represents an elected office where
    choices are a set of candidates.

    A Contest with type_name "measure" represents a ballot measure question posed to voters.
    Most measures have a Yes/No question though the text that can appear on
    ballots for the response may be different, e.g. "Bonds Yes". For a
    yes/no question, the measure will pass or fail, depending on the approval
    required. Normally, the first choice is yes. Some measures might be
    multiple choice, e.g. preferred name of a proposed city, and might
    have more than 2 choices. Ranked Choice Voting could be used with a
    multiple choice measure.

    (In orr we don't need to distinguish from a measure:)

    A Contest with type_name "ynoffice" is a hybrid of MeasureContest and OfficeContest,
    used for approval voting (retention contest) or for a recall question.
    The attributes defining an elected office are included, and information
    on the incumbent/candidate can be defined.
    """

    # TODO: don't pass election.
    def __init__(self, type_name, id_=None, election=None, areas_by_id=None,
        voting_groups_by_id=None):
        assert type_name is not None
        assert election is not None

        self.id = id_
        self.type_name = type_name
        self.election = election
        self.areas_by_id = areas_by_id
        self.all_voting_groups_by_id = voting_groups_by_id

        self.parent_header = None

        self.results_mapping = None   # a ResultsMapping object
        self.rcv_rounds = 0         # Number of RCV elimination rounds loaded

    def __repr__(self):
        return f'<Contest {self.type_name!r}: id={self.id!r}>'

    @property
    def is_rcv(self):
        """
        Return whether the contest is an RCV contest.
        """
        return bool(self.rcv_rounds)

    # Also expose the dict values as an ordered list, for convenience.
    @property
    def choices(self):
        # Here we use that choices_by_id is an OrderedDict.
        yield from self.choices_by_id.values()

    @property
    def reporting_groups(self):
        """
        Create and return a list of ReportingGroup objects.
        """
        area = self.voting_district
        voting_groups_by_id = self.all_voting_groups_by_id
        iterator = area.iter_reporting_groups(self.areas_by_id, voting_groups_by_id=voting_groups_by_id)
        return list(iterator)

    @property
    def reporting_group_count(self):
        return len(self.reporting_groups)

    @property
    def result_stat_count(self):
        """
        Helper function to get the number of result stats
        """
        return len(self.result_style.result_stat_types)

    @property
    def result_stats(self):
        """
        Helper function to get the result stat object list
        """
        return self.result_style.result_stat_types

    def _iter_headers(self):
        item = self
        while item.parent_header:
            yield item.parent_header

            item = item.parent_header

    def make_header_path(self):
        """
        Return the list of successive parent headers, starting from the root.
        """
        return list(reversed(list(self._iter_headers())))

    def get_new_headers(self, header_path):
        """
        Return the headers that are **new** compared with header_path.

        Returns: a list of pairs (i, header), where i is the (1-based)
          integer level of the header.
        """
        my_header_path = self.make_header_path()
        return get_path_difference(my_header_path, header_path)

    # TODO: move this method to ResultsMapping?
    def result_stat_indexes_by_id(self, stat_idlist=None):
        """
        Maps a space separated ID list into a set of result type
        index values. The index can be used to access the
        result_stat_types[].header or results[] value.
        If the id is not available, then it will be skipped.
        The special id value '*' will return 0..result_stat_count-1.
        The id value 'CHOICES' will insert the index values
        for all choices, result_stat_count..result_stat_count+choice_count-1

        This routine allows an API to access the heading and result
        value for a specific set of result stat types in set order.
        When the CHOICES id is included, the stat values can be
        reordered before and after choices.
        """
        if stat_idlist is None:
            stat_idlist = '*'

        stat_ids = parse_idlist(stat_idlist)

        indices = []
        table = self.results_mapping
        for label_or_id in stat_ids:
            new_indices = table.get_indices_by_id(label_or_id)
            indices.extend(new_indices)

        return indices

    def _result_stats_by_id(self, stat_idlist=None):
        """
        Returns a list of ResultStatType, either all or the list
        matching the space separated IDs.
        """
        indices = self.result_stat_indexes_by_id(stat_idlist)
        stat_types = self.result_style.result_stat_types
        return [stat_types[i] for i in indices]

    def detail_headings(self, stat_idlist=None, translate=None):
        """
        Args:
          translate: a function that has the same signature as our
            translate() contextfilter.
        """
        headings = ['Subtotal Area']

        for choice in self.choices:
            heading = translate(choice.ballot_title)
            headings.append(heading)

        stats = self._result_stats_by_id(stat_idlist)
        headings.extend(stat.heading for stat in stats)

        return headings

    def voting_groups_from_idlist(self, group_idlist=None):
        """
        Helper function to reference the voting groups.
        """
        return self.result_style.voting_groups_from_idlist(group_idlist)

    def load_results_details(self):
        """
        Loads the results details for the contest.

        Returns '' so this can be called from templates. No action is taken
        if the details have already been loaded.
        """
        # We use the results attribute as a marker to tell if the data
        # has already been loaded.  Skip if already loaded.
        if not hasattr(self, 'results'):
            self._load_contest_results_data(self)
            result_stat_type_index_by_id = self.result_style.result_stat_type_index_by_id
            self.results_mapping = ResultsMapping(result_stat_type_index_by_id,
                                                  choice_count=self.choice_count)

        return ''

    def summary_results(self, stat_index, group_idlist=None):
        """
        Returns a list of vote summary values (total votes for each
        VotingGroup defined. If group_idlist is defined it will be
        interpreted as a space separated list of VotingGroup IDs.

        The stat_index may be an integer, 0..result_stat_count
        for stats, or ..result_stat_count+choice_count for an index
        representing a choice, or alternatively can be a choice object,
        where the index is computed from the choice.
        """
        # Load the results if not already loaded
        self.load_results_details()
        table = self.results_mapping

        if isinstance(stat_index, Choice):
            stat_index = table.get_candidate_index(stat_index)
        else:
            if (not type(stat_index) is int) or stat_index<0 or stat_index >= self.result_stat_count + self.choice_count:
                raise RuntimeError(f'Invalid stat_index {stat_index} in contest {self.id}')

        # TODO: check stat_index
        return [self.results[i][stat_index] for i in
                self.result_style.voting_group_indexes_from_idlist(group_idlist)]

    def detail_rows(self, choice_stat_idlist, reporting_groups=None):
        """
        Yield rows of vote stat and choice values for the given reporting
        groups.

        Args:
          reporting_groups: an iterable of ReportingGroup objects.  Defaults
            to all of the contest's reporting groups.
        """
        if reporting_groups is None:
            reporting_groups = self.reporting_groups

        self.load_results_details()

        results = self.results
        indices = self.result_stat_indexes_by_id(choice_stat_idlist)

        for rg in reporting_groups:
            results_row = results[rg.index]
            row = [rg.display()]
            row.extend(utils.format_number(results_row[i]) for i in indices)

            yield row


class Election:

    """
    The election is the root object for all content defined for an election
    operated by an Election Administration (EA), e.g. a county.

    An Election object without a date can be used to hold a definition
    of all current elected offices, represented as a contest and incumbents
    represented as candidate objects.

    Instance attributes:

      input_dir: the directory containing the input data, as a Path object.

      ballot_title:
      date:
      election_area:
      headers_by_id:
      contests_by_id:

    Private attributes:
      _load_contest_status_data: a function that loads the contest results
        status data into each contest.  The function should have signature:
          load(election).
    """

    def __init__(self, input_dir):
        """
        Args:
          input_dir: the directory containing the input data, as a Path object.
        """
        assert input_dir is not None
        self.input_dir = input_dir

        self.ballot_title = None
        self.date = None

    def __repr__(self):
        return f'<Election ballot_title={i18n_repr(self.ballot_title)} election_date={self.date!r}>'

    # Also expose the dict values as an (ordered) list, for convenience.
    @property
    def headers(self):
        # Here we use that headers_by_id is an OrderedDict.
        yield from self.headers_by_id.values()

    # Also expose the dict values as an (ordered) list, for convenience.
    @property
    def contests(self):
        # Here we use that contests_by_id is an OrderedDict.
        yield from self.contests_by_id.values()

    def contests_with_headers(self):
        """
        Yield all contests as pairs (headers, contest), where--
          headers: the new headers that need to be displayed, as a list
            of pairs (level, header) (or the empty list if there are no
            new headers):
              level: the "level" of the header, as an integer (1-based) index.
              header: a Header object.
          contest: a Contest object.
        """
        parent_header = None
        header_path = []
        for contest in self.contests:
            headers = []
            if contest.parent_header != parent_header:
                # Then there are new headers to display.
                headers.extend(contest.get_new_headers(header_path))
                header_path = contest.make_header_path()

            yield headers, contest

    def load_contest_statuses(self):
        """
        Loads the contest results status data into each contest.

        Returns '' so this can be called from templates. No action is taken
        if the contest status has been loaded.
        """
        # We use _contest_status_loaded as a marker to indicate that the
        # data has already been loaded.  Skip if already loaded.
        if hasattr(self, '_contest_status_loaded'):
            return ''

        self._load_contest_status_data(self)

        self._contest_status_loaded = True

        return ''
