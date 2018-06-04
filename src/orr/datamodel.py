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
import functools
import logging


_log = logging.getLogger(__name__)


# Besides the votes for candidates and measure choices counted, there
# are a set of summary results with ballots not counted by category,
# and a summary result for totals. These have a set of IDs and a generic title.
# For n of m voting (Vote for n), a voter can make n selections, so for
# "vote for 3", if only 1 choice was made, there would be 2 undervotes,
# and if 4 or more choices were made, there would be 3 overvotes
RESULT_STATS = OrderedDict([
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

# Both detailed reports and contest summary reports might list a vote
# total as well as one or more subtotals. A set of ID/Suffix codes and
# a name/title is predefined. An RCV contest will also have RCV Round subtotals
SUBTOTAL_TYPES = OrderedDict([
    ('TO','Total'),             # Total of all subtotals
    ('ED','Election Day'),      # Election day precinct voting (in county)
    ('MV','Vote by Mail'),      # Vote by mail ballots (in county)
    ('EV','Early Voting'),      # Early voting/vote centers (in county)
    ('IA','In-County Total'),   # Subtotal this county only (multi-county contest)
    ('XA','Other Counties')     # Votes from other counties (multi-county contest)
    ])


def parse_as_is(obj, value):
    """
    Return the given value as is, without any validation, etc.
    """
    _log.debug(f'parsing as is: {value}')
    return value


# TODO: add validation.
def parse_id(obj, value):
    """
    Remove and parse an i18n string from the given data.
    """
    _log.debug(f'parsing id: {value}')
    return value


def parse_date(obj, value):
    """
    Remove and parse a date from the given data.

    Args:
      value: a date string, e.g. of the form "2016-11-08".
    """
    _log.debug(f'processing parse_date: {value}')

    date = datetime.strptime(value, '%Y-%m-%d').date()

    return date


# TODO: add validation.
def parse_i18n(obj, value):
    """
    Remove and parse an i18n string from the given data.
    """
    _log.debug(f'processing parse_i18n: {value}')
    return value


def i18n_repr(i18n_text):
    if 'en' in i18n_text:
        title = i18n_text['en']
    else:
        title = str(i18n_text)

    return title[:40]


def load_object(cls, data, cls_info=None):
    """
    Set the attributes configured in the object's `auto_attrs` class
    attribute, from the given deserialized json data.
    """
    if cls_info is None:
        cls_info = {}

    try:
        # This is where we use composition over inheritance.
        # We inject additional attributes and behavior into the class
        # constructor.
        obj = cls(**cls_info)
    except Exception:
        raise RuntimeError(f'error with cls {cls!r}: {cls_info!r}')

    for info in obj.auto_attrs:
        attr_name, load_value, *remaining = info

        if remaining:
            assert len(remaining) == 1
            data_key = remaining[0]
        else:
            data_key = attr_name

        _log.debug(f'processing auto_attr: ({attr_name}, {data_key}, {load_value})')
        value = data.pop(data_key, None)
        if value is not None:
            value = load_value(obj, value)

        try:
            setattr(obj, attr_name, value)
        except Exception:
            raise RuntimeError(f"couldn't set {attr_name!r} on {obj!r}")

    if data:
        raise RuntimeError(f'unrecognized keys for obj {obj!r}: {sorted(data.keys())}')

    return obj


def index_object(mapping, obj):
    """
    Add an object in our data model to a lookup dict that references
    objects by id, and also add an index / sequence number.

    Args:
      mapping: a dict to lookup by obj.id
      obj: object to be added
    """
    if not obj.id:
        raise RuntimeError(f'object does not have an id: {obj!r}')
    if obj.id in mapping:
        raise RuntimeError(f'duplicate object id: {obj!r}')

    # TODO: don't set obj.index here e.g. since choices and results are combined?
    # TODO: assign index numbers at the end, when creating the convenience
    #  list for an object type?
    obj.index = len(mapping)  # Assign a sequence number (0-based).
    mapping[obj.id] = obj


def append_result_subtotal(contest, data:dict, listattr:list, subtotal_cls):
    """
    This routine contains common processing to append a
    SubtotalType or ResultDetail to a list within the contest.

    Args:
        contest:    contest containing the listattr
        obj:        object to be appended
        data:       source data to copy
        listattr:   list attribute or contest to append
    """
    obj = load_object(subtotal_cls, data)  # Copy data
    obj.index = len(listattr)   # Assign a sequence
    obj.contest = contest       # Back reference
    listattr.append(obj)


class Header:

    """
    Attributes:
      ballot_items: the child items, which are either Contest objects,
        or other Header objects.
      header_id: id of the parent header object containing this item
        (or a falsey value for root).
      parent_header: the parent header of the item, as a Header object.
    """
    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_title', parse_i18n),
        ('classification', parse_as_is),
        ('header_id', parse_as_is),
    ]

    def __init__(self):
        self.ballot_title = None
        self.ballot_items = []
        self.header_id = None
        self.id = None
        self.parent_header = None

    def __repr__(self):
        title = i18n_repr(self.ballot_title)
        return f'<Header id={self.id!r} title={title[:70]!r}...>'

    def add_child_item(self, item):
        """
        Link a child ballot item with its parent.

        Args:
          item: a Contest or Header object.
        """
        assert type(item) in (Contest, Header)

        self.ballot_items.append(item)
        item.parent_header = self  # back reference


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
    """

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_title', parse_i18n),
    ]

    def __repr__(self):
        title = i18n_repr(self.ballot_title)
        return f'<Choice id={self.id!r} title={title[:70]!r}...>'


class Candidate:

    """
    Represents a candidate selection on a ballot-.
    """

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_title', parse_i18n),
        ('ballot_designation', parse_i18n),
        ('candidate_party', parse_i18n),
    ]

    def __repr__(self):
        title = i18n_repr(self.ballot_title)
        return f'<Candidate id={self.id!r} title={title[:70]!r}...>'


class SubtotalType:

    """
    When reporting summary data, the votes reported may include a total
    as well as a set of contest or election configurable subtotals. For
    detailed data with precinct and district breakdowns, each area subtotal
    may have separated subtotal types, e.g. election day precinct voting,
    and vote-by-mail. An object is defined to hold a reference id as well
    as a label.
    """

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('heading', parse_as_is),
    ]

    def __init__(self, id_=None, heading=None):
       self.id = id
       self.heading = heading


class ResultDetail:

    """
    When reporting detailed results data, a set of separate total/subtotal
    exists for a set of ResultDetail
    """

    auto_attrs = [
        ('id', parse_id, '_id'),
    ]

    def __init__(self, id_=None, area_heading=None, subtotal_heading=None,
                 is_vbm=False):
       self.id = id
       self.area_heading = area_heading
       self.subtotal_heading =subtotal_heading
       self.is_vbm = is_vbm


def get_path_difference(new_seq, old_seq):
    """
    Return the sequence items that are **new** compared with the old.
    """
    index = min(len(new_seq), len(old_seq)) - 1
    while index >= 0:
        new_item, old_item = (path[index] for path in (new_seq, old_seq))
        if new_item is old_item:
            index += 1
            break
        index -= 1
    else:
        index = 0

    return list(pair for pair in enumerate(new_seq[index:], start=index+1))


# Dict mapping contest data "_type" name to choice class.
BALLOT_ITEM_CLASSES = {
    'office': Candidate,
    'measure': Choice,
    'ynoffice': Choice,
}


class Contest:

    """
    Contest is a class that encompasses all contest types: offices, measures,
    and retention/recall. All contests have the following common attributes:

    Attributes:
      id: must be unique across all contests or headers
      type_name: a string indicating the Contest type (see below for
        descriptions).
      choice_cls: the class to use for the contest's choices (can be
        Choice or Candidate).

      ballot_title: text appearing on the ballot representing the contest.
      ballot_subtitle: second level title for this item
      choices: List of choices: candidates or Yes/No etc. on measures
               and recall/retention contests
      header_id: id of the parent header object containing this item
        (or a falsey value for root).
      parent_header: the parent header of the item, as a Header object.

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

    @classmethod
    def from_data(cls, data):
        """
        Create and return a Header object from data.
        """
        try:
            type_name = data.pop('_type')
        except KeyError:
            raise RuntimeError(f"key '_type' missing from data: {data}")

        try:
            choice_cls = BALLOT_ITEM_CLASSES[type_name]
        except KeyError:
            raise RuntimeError(f'invalid ballot item type: {type_name!r}')

        cls_info = dict(type_name=type_name, choice_cls=choice_cls)

        contest = load_object(Contest, data, cls_info=cls_info)

        return contest

    def enter_choice(self, data, choices_by_id):
        """
        Common processing to enter a candidate or measure choice

        Args:
          choice_cls: the class to use to instantiate the choice.
        """
        choice_cls = self.choice_cls
        choice = load_object(choice_cls, data)
        choice.contest = self     # Add back reference

        index_object(choices_by_id, choice)

    def enter_choices(self, choices):
        """
        Scan an input data list of contest choice entries to create.

        Args:
          choice_cls: the class to use to instantiate the choice (e.g.
            Candidate or Choice).
        """
        choices_by_id = OrderedDict()

        for data in choices:
            self.enter_choice(data, choices_by_id=choices_by_id)

        return choices_by_id

    def enter_result_stats(self, result_stats):
        """
        Scan summary result attributes for a contest
        """
        for data in result_stats:
            stat = load_object(Choice, data)
            index_object(self.choices_by_id, stat)
            self.result_stats.append(stat)

    def enter_subtotal_types(self, subtotal_types):
        """
        Scan summary subtotals available for this contest
        """
        for data in subtotal_types:
            append_result_subtotal(self, data, self.subtotal_types,
                subtotal_cls=SubtotalType)

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_subtitle', parse_i18n),
        ('ballot_title', parse_i18n),
        # TODO: this should be parsed out.
        ('choice_names', parse_as_is),
        ('choices_by_id', enter_choices, 'choices'),
        ('header_id', parse_as_is),
        ('instructions_text', parse_as_is),
        ('is_partisan', parse_as_is),
        ('number_elected', parse_as_is),
        ('question_text', parse_as_is),
        ('result_stats', enter_result_stats),
        ('subtotal_types', enter_subtotal_types),
        ('type', parse_as_is),
        ('vote_for_msg', parse_as_is),
        ('vote_type_id', parse_as_is),
        ('writeins_allowed', parse_as_is),
    ]

    def __init__(self, type_name, choice_cls=None, id_=None):
        assert type_name is not None

        self.id = id_
        self.type_name = type_name
        self.choice_cls = choice_cls

        self.header_id = None
        self.parent_header = None
        self.result_details = []    # result detail definitions
        self.result_stats = []      # Pseudo choice for result summary attrs
        self.subtotal_types = []    # summary subtotals available
        self.rcv_rounds = 0         # Number of RCV elimination rounds loaded

    def __repr__(self):
        return f'<Contest {self.type_name!r}: id={self.id!r}>'

    # Also expose the dict values as an ordered list, for convenience.
    @property
    def choices(self):
        # Here we use that choices_by_id is an OrderedDict.
        yield from self.choices_by_id.values()

    def enter_result_details(self, result_details):
        """
        Scan detail subtotals available for this contest
        """
        for data in result_details:
            append_result_subtotal(self, data, self.result_details,
                subtotal_cls=ResultDetail)

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


def process_header_id(item, headers_by_id):
    """
    Add the two-way association between a ballot item (header or contest)
    and its header, if it has a header.

    Args:
      item: a Header or Contest object.
    """
    if not item.header_id:
        # Then there is nothing to do.
        return

    # Add this ballot item to the header's ballot item list.
    try:
        header = headers_by_id[item.header_id]
    except KeyError:
        msg = f'Header id {item.header_id!r} not found for item: {item!r}'
        raise RuntimeError(msg)

    header.add_child_item(item)


class Election:

    """
    The election is the root object for all content defined for an
    election operated by an Election Administration (EA), e.g. a
    county.

    An Election object without a date can be used to hold a definition
    of all current elected offices, represented as a contest and incumbents
    represented as candidate objects.
    """

    def process_headers(self, value):
        """
        Process the source data representing the header items.

        Returns an OrderedDict mapping header id to Header object.

        Args:
          value: a list of dicts corresponding to the Header objects.
        """
        headers_by_id = OrderedDict()
        for data in value:
            header = load_object(Header, data)
            process_header_id(header, headers_by_id)
            index_object(headers_by_id, header)

        return headers_by_id

    def process_contests(self, value):
        """
        Process the source data representing the contest items.

        Returns an OrderedDict mapping contest id to Contest object.

        Args:
          value: a list of dicts corresponding to the Contest objects.
        """
        headers_by_id = self.headers_by_id
        contests_by_id = OrderedDict()

        for data in value:
            contest = Contest.from_data(data)
            process_header_id(contest, headers_by_id)
            index_object(contests_by_id, contest)

        return contests_by_id

    auto_attrs = [
        ('ballot_title', parse_i18n),
        ('date', parse_date, 'election_date'),
        ('election_area', parse_i18n),
        ('languages', parse_as_is),
        ('translations', parse_as_is),
        # Process headers before contests since the contest data references
        # the headers but not vice versa.
        ('headers_by_id', process_headers, 'headers'),
        ('contests_by_id', process_contests, 'contests'),
    ]

    def __init__(self):
        pass

    def __repr__(self):
        return f'<Election ballot_title={self.ballot_title!r} election_date={self.date!r}>'

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
