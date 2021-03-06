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

from collections import namedtuple, OrderedDict
from datetime import datetime
import itertools
import logging
import re

from orr.models.rcvresults import RCVResults
import orr.utils as utils
from orr.utils import truncate, ENGLISH_LANG

_log = logging.getLogger(__name__)


AREA_ID_ALL = 'ALL'
PARTY_ID_ALL = 'ALL'
VOTING_GROUP_ID_ALL = 'TO'

# The possible winning_status values.
WINNING_STATUSES = [
    'tied',
    'to_runoff',
    'winning',
]

# Besides the votes for candidates and measure choices counted, there
# are a set of summary results with ballots not counted by category,
# and a summary result for totals. These have a set of IDs and a generic title.
# For n of m voting (Vote for n), a voter can make n selections, so for
# "vote for 3", if only 1 choice was made, there would be 2 undervotes,
# and if 4 or more choices were made, there would be 3 overvotes
VOTING_STATS = OrderedDict([
    ('RSCst', 'Ballots Cast'),      # Ballot sheets submitted by voters
    ('RSExh', 'Exhausted Ballots'), # All RCV choices were eliminated (RCV only)
    ('RSOvr', 'Overvotes'),         # Possible votes rejected by overvoting
    ('RSReg', 'Registered Voters'), # Voters registered for computing turnout
    ('RSRej', 'Ballots Rejected'),  # Not countable
    ('RSTot', 'Total Votes'),       # Sum of valid votes reported
    ('RSTrn', 'Voter Turnout'),     # (SVCst/SVReg)*100
    ('RSUnc', 'Ballots Uncounted'), # Not yet counted or needing adjudication
    ('RSUnd', 'Undervotes'),        # Blank votes or additional votes not made
    ('RSWri', 'Write-in Votes'),    # Write-in candidates not explicitly listed
])

# Set defining the RESULT_STATS items that are percentages (decimal)
# that should be displayed with a % suffix.
RESULT_STAT_PERCENTAGE = { 'RSTrn' }

# Both detailed reports and contest summary reports might list a vote
# total as well as one or more subtotals. A set of ID/Suffix codes and
# a name/title is predefined. An RCV contest will also have RCV Round subtotals
VOTING_GROUPS = OrderedDict([
    (VOTING_GROUP_ID_ALL, 'Total'),  # Total of all subtotals
    ('ED','Election Day'),      # Election day precinct voting (in county)
    ('MV','Vote by Mail'),      # Vote by mail ballots (in county)
    ('EV','Early Voting'),      # Early voting/vote centers (in county)
    ('IA','In-County Total'),   # Subtotal this county only (multi-county contest)
    ('XA','Other Counties'),    # Votes from other counties (multi-county contest)
    ('PR','Provisional Voting') # Voting with provisional ballot envelopes
    ])


def ensure_int(value, arg_name):
    if type(value) != int:
        raise TypeError(f'argument {arg_name!r} not an int: {type(value)}')


def parse_text_ids(ids_text):
    """
    Args:
      ids_text: space-separated list of IDS, as a string.
    """
    return ids_text.split()


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


# Encapsulates the data needed to format a Python format string.
#
# This is useful for text that needs to be translated prior to being
# inserted into the format string.
SubstitutionString = namedtuple('SubstitutionString', 'format_string, data')


def get_i18n_value(obj):
    if not hasattr(obj, '__i18n_attr__'):
        raise RuntimeError(f'object does not have __i18n_attr__: {obj!r}')

    attr_name = obj.__i18n_attr__
    try:
        return getattr(obj, attr_name)
    except AttributeError:
        msg = f'i18n attribute {attr_name!r} missing from object: {obj}'
        # Use `from None` since the new exception provides strictly
        # more information than the previous.
        raise RuntimeError(msg) from None


def translate_object(obj, lang=None):
    """
    Args:
      value: the object to translate.  This can be either (1) a data
        model object with an `__i18n_attr__` attribute, (2) a
        `SubstitutionString` object, or (3) an i18n dict.
      lang: an optional 2-letter language code.  Defaults to English.
    """
    if lang is None:
        lang = ENGLISH_LANG

    if hasattr(obj, '__i18n_attr__'):
        obj = get_i18n_value(obj)

    if isinstance(obj, SubstitutionString):
        # TODO: make this a method of `SubstitutionString`?
        try:
            data = tuple(
                translate_object(part, lang=lang) for part in obj.data
            )
            return obj.format_string.format(*data)
        except Exception:
            raise RuntimeError(f'error translating SubstitutionString: {obj!r}')

    return utils.choose_translation(obj, lang=lang)


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

    # This attribute says which property contains the translations.
    __i18n_attr__ = 'text'

    def __init__(self, id_=None, text=None):
        """
        Args:
          text: an i18n dict.
        """
        self.id = id_
        self.text = text

    def __repr__(self):
        return f'<VotingGroup id={self.id!r}>'


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

    # This attribute says which property contains the translations.
    __i18n_attr__ = 'text'

    def __init__(self, _id=None, heading=None):
        self.id = _id
        # TODO: remove self.heading.
        self.heading = heading
        self._text = None

    def __repr__(self):
        return f'<ResultStatType id={self.id!r}>'

    @property
    def text(self):
        if self._text is None:
            # TODO: remove this fallback after heading is removed.
            return {ENGLISH_LANG: self.heading}

        return self._text


# TODO: store the voting_group_to_id on each object, in advance?
class ResultStyle:

    """
    Encapsulates what result totals and subtotals are available (e.g.
    for a contest).

    Specifically, it encapsulates:

    1) an ordered list of VotingGroup objects (e.g. TO, ED, MV, etc).
    2) an ordered list of ResultStatType objects (e.g. RSReg, RSCst,
       RSTot, etc).

    Instance attributes:

      id:
      description:
      is_rcv:
      result_stat_types:
    """

    def __init__(self):
        self.id = None
        self.description = None
        self.is_rcv = None

        # These two attributes are set by the loader at the same time.
        # This is a list of the ResultStatType objects, in the correct order.
        self.result_stat_types = None
        # This is a mapping from ResultStatType id to ResultStatType index.
        self.stat_id_to_index = None

        # These two attributes are set by the loader at the same time.
        # This is a list of the VotingGroup objects, in the correct order.
        self.voting_groups = None
        # This is a mapping from VotingGroup id to VotingGroup index.
        self.vg_id_to_index = None

    def __repr__(self):
        return f'<ResultStyle id={self.id!r}>'

    @property
    def result_stat_count(self):
        return len(self.result_stat_types)

    def get_stat_by_id(self, stat_id):
        index = self.stat_id_to_index[stat_id]

        return self.result_stat_types[index]

    def get_stat_index(self, stat_id):
        index = self.stat_id_to_index[stat_id]
        stat = self.result_stat_types[index]

        yield (stat, index)

    def get_vg_by_id(self, vg_id):
        """
        Args: a VotingGroup object or id.
        """
        index = self.vg_id_to_index[vg_id]
        vg = self.voting_groups[index]

        return vg

    def get_vg_index(self, vg_id=None):
        """
        Args: a VotingGroup object or id.
        """
        if vg_id is None:
            vg_id = VOTING_GROUP_ID_ALL  # "TO"
        elif type(vg_id) != str:
            # Then assume it is a VotingGroup object.
            vg_id = vg_id.id

        index = self.vg_id_to_index[vg_id]
        vg = self.voting_groups[index]

        yield (vg, index)

    def voting_groups_from_ids(self, ids):
        """
        Return the list of voting group objects corresponding to a
        list of voting group ids. Unmatched ids are omitted.
        """
        if ids == ['*']:
            # Then return all of the ids, in order.
            return self.voting_groups

        voting_groups = [
            self.get_vg_by_id(vg_id) for vg_id in ids
        ]

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
      reporting_areas:
      reporting_groups:
    """

    reporting_group_pattern = re.compile(r'(.*)~(.*)')

    def __init__(self, id_=None, short_name=None):
        self.id = id_
        self.short_name = short_name

        self.classification = None
        self.name = None
        self.is_vbm = False
        self.reporting_areas = None
        self.reporting_groups = None

        # This is a private attribute needed to set `self.reporting_groups`.
        self._reporting_area_ids = None

    def __repr__(self):
        return f'<Area {self.classification!r}: id={self.id!r}>'

    @property
    def is_all(self):
        return self.id == AREA_ID_ALL


class ReportingGroup:

    """
    The reporting group defines an (area, voting_group) tuple for
    results subtotals. The area with id "ALL" is a special placeholder
    area meaning all precincts (for that contest), and VotingGroup "TO"
    is used for all voters in those areas.
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

    def __repr__(self):
        return (
            f'<ReportingGroup|{self.index!r}: area={self.area!r} vg={self.voting_group!r}>'
        )

    def __str__(self):
        return f'{self.area.id}~{self.voting_group.id}'

    @property
    def group_id(self):
        return (self.area.id, self.voting_group.id)

    def display(self):
        """
        Return the display format for use in a template.

        An example return value is -- "Precinct 1141 - Early Voting".
        """
        text = self.area.short_name
        if self.area.id == AREA_ID_ALL or self.voting_group.id != VOTING_GROUP_ID_ALL:
            # This defaults to English.
            vg_name = translate_object(self.voting_group)
            text += f' - {vg_name}'

        return text


class Party:

    """
    Attributes:

      id:
      heading:
    """

    # This attribute says which property contains the translations.
    __i18n_attr__ = 'name'

    def __init__(self, _id=None):
        self.id = _id
        self._name = None

    def __repr__(self):
        return f'<Party {self.id!r}>'

    @property
    def name(self):
        return self._name


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

    # This attribute says which property contains the translations.
    __i18n_attr__ = 'ballot_title'

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
      is_successful: boolean indicating whether the choice was successful
        (e.g. elected, advanced to runoff, met the initiative threshold, etc).
    """

    # This attribute says which property contains the translations.
    __i18n_attr__ = 'ballot_title'

    def __init__(self, contest=None):
        self.id = None
        self.ballot_title = None
        self.winning_status = None

        # Back-reference.
        self.contest = contest

    def __repr__(self):
        return f'<Choice id={self.id!r} title={i18n_repr(self.ballot_title)}>'

    @property
    def is_successful(self):
        # For now, we consider any winning_status value to be "successful".
        return self.winning_status is not None


# TODO: make this not subclass Choice.
class Candidate(Choice):

    """
    Represents a candidate selection on a ballot-.

    Instance attributes:

      id:
      ballot_designation:
      ballot_party_label: an i18n dict (e.g. "Party Preference: Democratic"
        for the English).
      ballot_title:
      candidate_party: a Party object.
      contest: back-reference to a Contest object.
    """

    def __init__(self, contest=None):
        self.id = None
        self.ballot_title = None
        self.winning_status = None

        # Back-reference.
        self.contest = contest

        self.ballot_party_label = None
        self.candidate_party = None

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
    and (2) index in the results row.
    """

    def __init__(self, result_style=None, choices=None):
        """
        Args:
          result_stat_types: an iterable of ResultStatType objects.
          choices: the choices in the contest, as a list of Choice objects.
        """
        self.choices = choices
        self.result_style = result_style

        all_items = list(result_style.result_stat_types)
        if choices:
            all_items.extend(choices)
        self.all_items = all_items

    @property
    def choice_count(self):
        return len(self.choices)

    @property
    def result_stat_types(self):
        return self.result_style.result_stat_types

    @property
    def stat_id_to_index(self):
        return self.result_style.stat_id_to_index

    @property
    def result_stat_count(self):
        return len(self.result_stat_types)

    def has_stat(self, stat_id):
        """
        Return whether the given ResultStatType is present.

        This is useful e.g. for telling whether "RSWri" is applicable.
        """
        return stat_id in self.stat_id_to_index

    def get_choice_index(self, choice):
        """
        Return the index of a choice's results in each results row.
        """
        return self.result_stat_count + choice.index

    def get_stat_or_choice_index(self, stat_or_choice):
        """
        Args:
          stat_or_choice: a ResultStatType object or Choice object.
          stat_id: the id of a ResultStatType object.
        """
        if type(stat_or_choice) == ResultStatType:
            stat_id = stat_or_choice.id
        elif isinstance(stat_or_choice, str):
            return self.stat_id_to_index[stat_or_choice]

        if not isinstance(stat_or_choice, Choice):
            raise RuntimeError(f'stat_or_choice not Choice but: {stat_or_choice!r}')

        return self.get_choice_index(stat_or_choice)

    def iter_indices_by_id(self, label_or_id):
        """
        A generator yielding the indices corresponding to a single string id.

        Args:
          label_or_id: a ResultStatType id, or one of the special strings "*"
            or "CHOICES".
        """
        if label_or_id == '*':
            yield from range(self.result_stat_count)
        elif label_or_id == 'CHOICES':
            yield from range(self.result_stat_count,
                self.result_stat_count + len(self.choices))
        else:
            yield self.stat_id_to_index[label_or_id]

    def iter_indices_by_spaced_ids(self, spaced_ids=None):
        """
        A generator yielding indices after converting from a space-separated
        list of ids.

        Map a space-separated ID list into a set of result type index values.
        The index can be used to access the result_stat_types[].header or
        results[] value. If the id is not available, it will be skipped. The
        value '*' will return 0..result_stat_count-1. The value 'CHOICES'
        will insert the index values for all choices,
        result_stat_count..result_stat_count+choice_count-1

        This routine allows an API to access the heading and result value
        for a specific set of result stat types in set order. When the
        CHOICES id is included, the stat values can be reordered before and
        after choices.
        """
        if spaced_ids is None:
            spaced_ids = '*'

        for label_or_id in parse_text_ids(spaced_ids):
            yield from self.iter_indices_by_id(label_or_id)

    def iter_result_stats(self, spaced_ids=None):
        """
        A generator that yields ResultStatType objects.

        Args:
          spaced_ids: a list of ResultStatType ids, as a space-delimited
            string, or None to yield all of the ResultStatType objects,
            in order.
        """
        result_stat_types = self.result_stat_types

        if spaced_ids is None:
            # Then yield all of them.
            yield from result_stat_types
            return

        stat_indices = self.iter_indices_by_spaced_ids(spaced_ids)

        yield from (result_stat_types[i] for i in stat_indices)

    def get_summary_index(self, id_, stat_or_choice=None):
        """
        A generator that yields (obj, index) pairs.

        Args:
          stat_or_choice: a ResultStatType object or Choice object.
          stat_id: the id of a ResultStatType object.
          stat_ids: a string of space-delimited ids.
        """
        if stat_or_choice is not None:
            # TODO: check stat_or_choice_index
            index = self.get_stat_or_choice_index(stat_or_choice)

            yield (stat_or_choice, index)
        else:
            assert id_ is not None
            indices = self.iter_indices_by_id(id_)

            yield from ((self.all_items[i], i) for i in indices)


class ResultTotal:

    # This attribute says which property contains the translations.
    __i18n_attr__ = 'text'

    def __init__(self, obj, total):
        assert obj is not None
        assert not isinstance(obj, str)
        self.obj = obj
        self.total = total

    def __repr__(self):
        return f'<ResultTotal|{self.total!r}: {self.obj!r}>'

    @property
    def text(self):
        return get_i18n_value(self.obj)


class IndexedTotals:

    """
    Encapsulates a list of vote totals indexed by a mapping of some kind.
    """

    # TODO: remove the need for the can_vote_for_multiple argument.
    # TODO: should we keep headers, or get it by calling resolve()?
    def __init__(self, name, totals, resolve, headers, can_vote_for_multiple=None):
        """
        Args:
          name: a name, for debugging purposes.
          totals: the list of totals.
          resolve: a function with signature: `resolve(*args, **kwargs)`
            that yields one or more pairs: `(obj, index)`.
            For example: `resolve(stat_id=stat_id) -> [(result_stat, index)]`.
          headers: the headers, for debugging purposes.
          can_vote_for_multiple: None means unspecified.
        """
        self.can_vote_for_multiple = can_vote_for_multiple
        self.resolve = resolve
        self.headers = headers
        self.name = name
        self.totals = totals

    def __repr__(self):
        if self.headers is None:
            parts = [str(total) for total in self.totals]
        else:
            parts = []
            for header, total in zip(self.headers, self.totals):
                parts.append(f'{header.id}:{total}')

        details = ', '.join(parts)
        return f'<IndexedTotals {self.name!r}: {details} >'

    @property
    def total_votes(self):
        """
        Return the total vote for choices (i.e. "RSTot"), as a ResultTotal object.
        """
        try:
            return self.get_total('RSTot')
        except Exception:
            # Re-raise as something other than AttributeError for a less
            # confusing traceback.
            raise RuntimeError()

    def _iter_totals(self, *args, **kwargs):
        """
        Return the summary total for a ResultStatType or Choice object,
        as a ResultTotal object.

        Args:
          stat_or_choice: a ResultStatType object or Choice object.
          stat_id: the id of a ResultStatType object.
        """
        try:
            yield from (
                ResultTotal(o, total=self.totals[i]) for o, i in self.resolve(*args, **kwargs)
            )
        except Exception:
            raise RuntimeError(
                'failed for:\n'
                f' resolve function: {self.resolve!r}\n'
                f'   args: {args!r}\n'
                f' kwargs: {kwargs!r}'
            )

    # TODO: update this docstring.
    # TODO: document what arguments and keyword arguments are accepted.
    def get_total(self, *args, **kwargs):
        """
        Return the summary total for a ResultStatType or Choice object,
        as a ResultTotal object.

        Args:
          stat_or_choice: a ResultStatType object or Choice object.
          stat_id: the id of a ResultStatType object.
        """
        try:
            # The following line will error out if result_totals doesn't
            # contain just one pair.
            result_total, = self._iter_totals(*args, **kwargs)
        except ValueError:
            msg = (
                'failed for:\n'
                f' resolve function: {self.resolve!r}\n'
                f'   args: {args!r}\n'
                f' kwargs: {kwargs!r}'
            )
            raise RuntimeError(msg)

        return result_total

    def iter_totals(self, spaced_ids):
        """
        Yield ResultTotal objects.

        Args:
          stat_ids: a list of ResultStatType ids, as a space-delimited
            string, or None to yield all of the ResultStatType objects,
            in order.
        """
        # Convert the space-delimited string to a list.
        for id_ in parse_text_ids(spaced_ids):
            yield from self._iter_totals(id_)

    # TODO: add a reverse argument?
    def sorted_totals(self, spaced_ids):
        key = lambda r: r.total
        # Order by descending total.
        results = sorted(self.iter_totals(spaced_ids), key=key, reverse=True)

        return results

    # TODO: change this to return a ResultTotal object?
    def get_max_total(self, spaced_ids):
        results = self.iter_totals(spaced_ids)
        return max(result.total for result in results)

    # TODO: remove or update this?
    def get_voted_ballots(self):
        """
        Return a ResultTotal object.
        """
        if self.can_vote_for_multiple:
            # Then use "Ballots cast" as the denominator.
            return self.get_total('RSCst')

        return self.total_votes


class ReportableMixin:

    """
    Encapsulates objects with reportable totals, e.g. a contest, or turnout
    for the election as a whole.

    Attributes:
      id: must be unique across all contests or headers

      ballot_title: text appearing on the ballot representing the contest.
      ballot_subtitle: second level title for this item
      header_id: id of the parent header object containing this item
        (or a falsey value for root).
      parent_header: the parent header of the item, as a Header object.

      _results_details_loaded: bool indicating if detailed results are present
    """

    # TODO: don't pass election.
    def __init__(self, election=None, areas_by_id=None, voting_groups_by_id=None):
        """
        Args:
          areas_by_id:
        """
        assert election is not None

        # TODO: remove all_voting_groups_by_id?
        self.all_voting_groups_by_id = voting_groups_by_id
        self.areas_by_id = areas_by_id
        self.election = election

        self.ballot_title = None
        self.ballot_subtitle = None
        self.name = None
        self.parent_header = None
        self.result_style = None

        self.url_state_results = None

        # This is the matrix of summary results totals.  The "shape"
        # of the matrix (e.g. 2-D vs. 3-D) depends on whether the concrete
        # class is Contest or Turnout.
        self._results_summary = None

        self._results_details_loaded = False

    @property
    def all_area(self):
        """
        Return the ALL area, as an Area object.
        """
        return self.areas_by_id[AREA_ID_ALL]

    @property
    def result_stat_types(self):
        """
        Helper function to get the number of result stats
        """
        return self.result_style.result_stat_types

    @property
    def result_stat_count(self):
        """
        Helper function to get the number of result stats
        """
        return self.result_style.result_stat_count

    @property
    def voting_groups(self):
        return self.result_style.voting_groups

    def iter_reporting_groups(self, summary_only=False):
        """
        Return an iterator that creates and yields the reporting groups
        (as ReportingGroup objects).

        Args:
          summary_only: whether to yield the reporting groups only for
            the summary totals.
        """
        area = self.voting_district
        reporting_areas = iter(area.reporting_areas)

        # The ALL area needs to be special-cased.  Namely, to get the
        # voting groups for the ALL area (i.e. the contest as a whole),
        # we need to look to the contest's result style.
        area = next(reporting_areas)
        assert area.is_all

        for index, voting_group in enumerate(self.voting_groups):
            yield ReportingGroup(area, voting_group, index=index)

        if summary_only:
            return

        # For the remaining areas, we look at the area itself for its
        # voting groups.
        for area in reporting_areas:
            for voting_group in area.reporting_groups:
                index += 1
                yield ReportingGroup(area, voting_group, index=index)

    def has_stat(self, stat_id):
        """
        Return whether the given ResultStatType is present.

        This is useful e.g. for telling whether "RSWri" is applicable.
        """
        return self.results_mapping.has_stat(stat_id)

    def get_stat_by_id(self, stat_id):
        return self.result_style.get_stat_by_id(stat_id)

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

    def detail_headings(self, spaced_ids=None, translator=None):
        """
        Args:
          translator: a function that is a return value of `make_translator()`.
        """
        headings = ['Subtotal Area']

        for choice in self.iter_choices():
            heading = translator(choice)
            headings.append(heading)

        result_stats = self.results_mapping.iter_result_stats(spaced_ids)

        headings.extend(translator(stat) for stat in result_stats)

        return headings

    def load_results_details(self):
        """
        Loads the results details for the contest.

        Returns '' so this can be called from templates. No action is taken
        if the details have already been loaded.
        """
        # We use the results attribute as a marker to tell if the data
        # has already been loaded.  Skip if already loaded.
        if not self._results_details_loaded:
            self._load_contest_results_data(self)

        return ''

    # TODO: move this to the Contest object.
    def get_contest_totals_by_stat(self, voting_group=None):
        """
        Return the summary totals for a voting group, as an IndexedTotals
        object.

        Args:
          voting_group: a VotingGroup object, or None for the "all" voting
            group.
        """
        if type(self) == Turnout:
            can_vote_for_multiple = False
        else:
            can_vote_for_multiple = self.can_vote_for_multiple

        # Summary results should be loaded for the election if present
        assert self.election.summary_data_loaded

        # Here we make the assumption that the reporting group for the
        # "all" area for the voting group we're interested in has an
        # index that matches the index of the voting group.
        # TODO: remove this assumption.
        (vg, rg_index), = self.result_style.get_vg_index(voting_group)

        # This is the row of subtotals corresponding to the voting group.
        vg_totals = self._results_summary[rg_index]

        # TODO: include the contest repr in the name argument.
        # TODO: also pass headers?
        return IndexedTotals('contest totals', vg_totals, headers=None,
            resolve=self.results_mapping.get_summary_index,
            can_vote_for_multiple=can_vote_for_multiple)

    def make_rcv_results(self, continuing_stat_id):
        """
        Args:
          continuing_stat_id: the id of the ResultStatType object
            corresponding to continuing ballots.
        """
        if self.rcv_totals is None:
            raise RuntimeError(f'rcv_totals None for {self!r}: rcv_rounds={rcv_rounds!r}')

        if not self.rcv_totals:
            # Then make sure rcv_rounds is 0.
            assert not self.rcv_rounds
            return None

        # Convert the choices from a generator to a list before passing
        # to RCVResults.
        candidates = list(self.iter_choices())
        continuing_stat = self.get_stat_by_id(continuing_stat_id)
        return RCVResults(self.rcv_totals, results_mapping=self.results_mapping,
            candidates=candidates, continuing_stat=continuing_stat)

    def detail_rows(self, spaced_choice_ids, reporting_groups=None):
        """
        Yield rows of vote stat and choice values for the given reporting
        groups.

        Args:
          reporting_groups: an iterable of ReportingGroup objects.  Defaults
            to all of the contest's reporting groups.
        """
        if reporting_groups is None:
            reporting_groups = self.iter_reporting_groups()

        self.load_results_details()

        results_mapping = self.results_mapping
        indices = list(results_mapping.iter_indices_by_spaced_ids(spaced_choice_ids))

        results = self.results
        for rg in reporting_groups:
            results_row = results[rg.index]
            row = [rg.display()]
            row.extend(utils.format_number(results_row[i]) for i in indices)
            yield row


class Turnout(ReportableMixin):

    # TODO: don't pass election.
    def __init__(self, election=None, areas_by_id=None, voting_groups_by_id=None,
        eligible_voters_stat=None):
        """
        Args:
          eligible_voters_stat: the result stat for eligible voters ("RSEli"),
            as a ResultStatType object. This is turnout specific.
        """
        super().__init__(election=election, areas_by_id=areas_by_id,
            voting_groups_by_id=voting_groups_by_id)

        self.eligible_voters = None
        self.eligible_voters_stat = eligible_voters_stat

        # These two attributes are set by the loader at the same time.
        # This is a list of the Party objects, in the correct order.
        self.parties = None
        # This is a mapping from Party id to Party index.
        self._party_id_to_index = None

    def __repr__(self):
        return f'<Turnout: object>'

    @property
    def turnout_summary(self):
        """
        Return the summary turnout totals.

        This is a 3-D matrix (list of list of lists) indexed by:
        reporting group (area-voting_group pair) -> party -> result stat.
        """
        return self._results_summary

    def get_eligible_total(self):
        """
        Return the number of voters eligible to register (stat_id "RSEli"),
        as a ResultTotal object.
        """
        return ResultTotal(self.eligible_voters_stat, total=self.eligible_voters)

    def _get_party_index(self, id_=None):
        if id_ == 'PARTIES':
            # Skip the "all" party.
            indices = (
                index for (party_id, index) in self._party_id_to_index.items()
                    if party_id != PARTY_ID_ALL
            )
        else:
            if id_ is None:
                id_ = PARTY_ID_ALL
            indices = [self._party_id_to_index[id_]]

        yield from ((self.parties[i], i) for i in indices)

    # TODO: share code with get_contest_totals_by_stat()?
    def get_totals_by_stat(self, vg=None):
        """
        Return an IndexedTotals object for turnout by result stat.

        Args:
          vg: the voting group for which to get totals, as a voting group
            object or string id, or None for the "all" voting group ("TO").
            Defaults to None.
        """
        (vg, vg_index), = self.result_style.get_vg_index(vg)

        # Pass no party id for the "all" party.
        (all_party, all_party_index), = self._get_party_index()

        totals = self.turnout_summary[vg_index][all_party_index]

        return IndexedTotals('turnout by stat', totals, resolve=self.result_style.get_stat_index,
            headers=self.result_stat_types)

    def get_totals_by_vg(self, stat_id):
        """
        Return an IndexedTotals object for turnout by voting group.

        Args:
          stat_id: the result stat for which to get totals, as a ResultStatType id.
        """
        stat_index = self.result_style.stat_id_to_index[stat_id]

        all_party_index = self._party_id_to_index[PARTY_ID_ALL]

        totals = []
        for vg_totals in self.turnout_summary:
            total = vg_totals[all_party_index][stat_index]
            totals.append(total)

        return IndexedTotals('turnout by voting group', totals,
            resolve=self.result_style.get_vg_index,
            headers=self.result_style.voting_groups)

    def get_totals_by_party(self, stat_id):
        """
        Return an IndexedTotals object for turnout by party.

        Args:
          stat_id: the result stat for which to get totals, as a ResultStatType id.
        """
        stat_index = self.result_style.stat_id_to_index[stat_id]

        (vg, vg_index), = self.result_style.get_vg_index(VOTING_GROUP_ID_ALL)

        totals = self.turnout_summary[vg_index]

        totals = []
        for party_totals in self.turnout_summary[vg_index]:
            total = party_totals[stat_index]
            totals.append(total)

        return IndexedTotals('turnout by party', totals, resolve=self._get_party_index,
            headers=self.parties)

class Contest(ReportableMixin):

    """
    Contest is a class that encompasses all contest types: offices, measures,
    and retention/recall. All contests have the following common attributes:

    Attributes:
      type_name: a string indicating the Contest type (see below for
        descriptions).
      choices: List of choices: candidates or Yes/No etc. on measures
               and recall/retention contests
      results_mapping: a ResultsMapping object.
      results: the result subtotals as a matrix, where each row corresponds
        to a ReportingGroup object, and each column a ResultStatType object
        or Choice object.  This means a subtotal can be accessed e.g. as
        `results[rg_index][stat_choice_index]`.
      rcv_totals: a list of tuples, one for each round, starting with the
        first round.

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
        """
        Args:
          type_name:
        """
        assert type_name is not None
        super().__init__(election=election, areas_by_id=areas_by_id,
            voting_groups_by_id=voting_groups_by_id)

        self.id = id_
        self.type_name = type_name

        self.contest_party = None

        # This is a dict mapping Choice id to Choice object.
        self.choices_by_id = None

        self.results_mapping = None

        # Number of RCV elimination rounds loaded
        self.rcv_rounds = None
        # TODO: document the format of this value.
        self.rcv_totals = None

        self.votes_allowed = None

        # This is the Choice object used for determining whether the
        # approval threshold is met.
        self.approval_choice = None
        # This is True when there is an approval required and the threshold is met.
        self.approval_met = None
        # The "approval_threshold" value can be a string having one
        # of the following forms:
        #  * "Advisory"
        #  * "Majority" (translates to "more than 50%" aka 50% + 1)
        #  * "n%" for some integer n
        #  * "m/n" for some integers m and n (e.g. 55/100 or 2/3).
        #
        # For California elections, the possibilities are: "Advisory",
        # "Majority", "55%", and "2/3".
        self.approval_threshold = None

    def __repr__(self):
        name = translate_object(self.contest_name)
        return f'<Contest {self.type_name!r}: id={self.id!r} name={name!r}>'

    @property
    def contest_summary(self):
        """
        Return the contest's summary totals.

        The return value is a 2-D matrix (list of lists) indexed by:
        reporting group (area-voting_group pair) -> result stats and choices.
        In other words, the rows correspond to reporting groups, and
        the columns correspond to result stats and choices.
        """
        return self._results_summary

    @property
    def approval_passed(self):
        return self.approval_met

    @property
    def choice_count(self):
        if self.choices_by_id is None:
            return 0

        return len(self.choices_by_id)

    # This is named "contest_name" instead of "name" to make it easier to
    # search for occurrences in the code.
    @property
    def contest_name(self):
        """
        Return the contest name, as a SubstitutionString object.
        """
        format_str = '{}'
        if self.name:
            fields = [self.name]
        elif self.ballot_title:
            fields = [self.ballot_title]
            if self.ballot_subtitle:
                format_str += ' - {}'
                fields.append(self.ballot_subtitle)
        else:
            format_str = ''
            fields = []

        if self.contest_party:
            format_str += ' ({})'
            fields.append(self.contest_party.name)

        return SubstitutionString(format_str, fields)

    @property
    def is_rcv(self):
        """
        Return whether the contest is an RCV contest.
        """
        return self.result_style.is_rcv

    @property
    def can_vote_for_multiple(self):
        """
        Return True or False, or None for unspecified.

        None can happen e.g. for the turnout pseudo-contest, as votes
        don't make sense in that context.
        """
        if self.votes_allowed is None:
            return None

        try:
            return self.votes_allowed > 1 and not self.is_rcv
        except Exception:
            raise RuntimeError(f'error for contest: {self!r}')

    percent_pattern = re.compile(r'^(\d+)%$')
    fraction_pattern = re.compile(r'^(\d+)/(\d+)$')

    @property
    def approval_threshold_fraction(self):
        """
        Converts the approval_threshold string to a fractional number,
        0.0 if not applicable or .50, .55, .66667 etc for Majority, percent,
        or fractions.
        """
        approval_threshold = self.approval_threshold
        if not approval_threshold:
            return 0.0
        if approval_threshold == 'Majority':
            return 0.5

        m = self.percent_pattern.match(approval_threshold)
        if m:
            return(float(m.group(1))/100.0)

        m = self.fraction_pattern.match(approval_threshold)
        if m:
            return(float(m.group(1))/float(m.group(2)))

        return 0.0

    @property
    def approval_threshold_percentage(self):
      fraction = self.approval_threshold_fraction
      if fraction == 0.0:
        return ''
      if fraction == 0.5:
        return '50%+1'
      if fraction == 2/3:
        return '66⅔%'
      return '{:.2g}%'.format(fraction * 100.0)

    # Also expose the dict values as an ordered list, for convenience.
    # TODO: change this to a list?
    def iter_choices(self):
        """
        Return an iterator over the Choice objects, in their pre-election order.
        """
        # Here we use that choices_by_id is an OrderedDict.
        yield from self.choices_by_id.values()

    # TODO: move this to IndexedTotals.
    @property
    def choices_sorted(self):
        """
        Return the list of choices in descending order of total votes
        """
        rg_totals = self.get_contest_totals_by_stat()
        if self.approval_threshold:
            def sorter(choice):
                # Sort Yes above No. Return 1 for Yes and 0 for No to
                # accomplish this.
                return 1 if self.is_approval_choice(choice) else 0
        else:
            def sorter(choice):
                # For other contests, sort by vote total
                return rg_totals.get_total(stat_or_choice=choice).total

        yield from sorted(self.iter_choices(), reverse=True, key=sorter)

    def is_approval_choice(self, choice):
        if not self.approval_threshold:
            return False

        return choice is self.approval_choice


class Election:

    """
    The election is the root object for all content defined for an election
    operated by an Election Administration (EA), e.g. a county.

    An Election object without a date can be used to hold a definition
    of all current elected offices, represented as a contest and incumbents
    represented as candidate objects.

    Instance attributes:

      input_dir: the directory containing the election.json file, as a
        Path object.
      input_results_dir: the directory containing the detailed results
        data files, as a Path object.

      ballot_title:
      date:
      election_area:
      headers_by_id:
      contests_by_id:
    """

    def __init__(self, input_dir, input_results_dir):
        """
        Args:
          input_dir: the directory containing the election.json file, as a
            Path object.
          input_results_dir: the directory containing the detailed results
            data files, as a Path object.
        """
        assert input_dir is not None
        assert input_results_dir is not None

        self.input_dir = input_dir
        self.input_results_dir = input_results_dir

        self.ballot_title = None
        self.date = None

        self.results_title = None
        self.url_state_results = None

        # Whether results data is available, or None if the results haven't
        # been checked for and loaded.
        self._results_available = None

    def __repr__(self):
        return f'<Election ballot_title={i18n_repr(self.ballot_title)} election_date={self.date!r}>'

    @property
    def summary_data_loaded(self):
        return self._results_available is not None

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
        Yield all contests as pairs (headers, contests), where--
          headers: the new headers that need to be displayed, as a list
            of pairs (level, header) (or the empty list if there are no
            new headers):
              level: the "level" of the header, as an integer (1-based) index.
              header: a Header object.
          contests: a list of Contest objects to follow the headers.
        """
        key = lambda contest: contest.parent_header

        header_path = []
        # Group contests in order by parent_header (i.e. by "section").
        for parent_header, contests in itertools.groupby(self.contests, key=key):
            contests = list(contests)
            contest = contests[0]
            headers = contest.get_new_headers(header_path)
            header_path = contest.make_header_path()

            yield (headers, contests)

    def contests_structured(self):
        """
        Yield all headers as pairs (header, items), where--
          header: a Header object
          items: list of items under this header; each item is either a Contest
            or a (header, items) pair
        """
        header_stack = []
        for headers, contests in self.contests_with_headers():
            for level, header in headers:
                # Close out headers with an equal or higher level than level
                while len(header_stack) >= level:
                    closed_header_structure = header_stack.pop()
                    if len(header_stack) == 0:
                        yield closed_header_structure

                new_header_structure = (header, [])
                if len(header_stack) > 0:
                    header_stack[-1][1].append(new_header_structure)
                header_stack.append(new_header_structure)

            header_stack[-1][1].extend(contests)

        if len(header_stack) > 0:
            yield header_stack[0]
