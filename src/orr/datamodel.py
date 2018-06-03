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


def load_attrs(cls, data, unprocessed_keys=None):
    """
    Set the attributes configured in the object's `auto_attrs` class
    attribute, from the given deserialized json data.

    Args:
      unprocessed_keys: keys that are allowed to exist in `data` after
        processing.
    """
    if unprocessed_keys is None:
        unprocessed_keys = []

    obj = cls()

    for info in cls.auto_attrs:
        name, load_value, *remaining = info

        if remaining:
            assert len(remaining) == 1
            attr_name = remaining[0]
        else:
            attr_name = name

        _log.debug(f'processing auto_attr: ({name}, {load_value}, {attr_name})')
        value = data.pop(name, None)
        if value is not None:
            value = load_value(obj, value)

        try:
            setattr(obj, attr_name, value)
        except Exception:
            raise RuntimeError(f"couldn't set {attr_name!r} on {obj!r}")

    for key in data.keys():
        if key in unprocessed_keys:
            continue

        raise RuntimeError(f'unrecognized key for obj {obj!r}: {key!r}')

    return obj


def load_object(cls, data):
    if hasattr(cls, 'from_data'):
        obj = cls.from_data(data)
    else:
        obj = load_attrs(cls, data)

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


def get_ballot_item_class(type_name):
    # Dict mapping ballot item type name to class.
    # TODO: make this module-level.
    BALLOT_ITEM_CLASSES = {
        'header': Header,
        'office': OfficeContest,
        'measure': MeasureContest,
        'ynoffice': YNOfficeContest,
    }

    try:
        cls = BALLOT_ITEM_CLASSES[type_name]
    except KeyError:
        raise RuntimeError(f'invalid ballot item type: {type_name!r}')

    return cls


# TODO: add validation.
def parse_id(obj, value):
    """
    Remove and parse an i18n string from the given data.
    """
    _log.debug(f'parsing id: {value}')
    return value


# TODO: add validation?
def parse_text(obj, value):
    """
    Remove and parse an i18n string from the given data.
    """
    _log.debug(f'parsing text: {value}')
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


class Choice:

    """
    Choice represents a selection on a ballot-- a candidate for an elected
    office, or Yes/No for a ballot measure, retention or recall office.
    Multiple choice for a measure is a selection other than yes/no for
    a pass/fail contest, e.g. preferred name of a proposed city incorporation.
    """

    auto_attrs = [
        ('_id', parse_id, 'id'),
        ('ballot_title', parse_i18n),
    ]

    def __init__(self, id_=None, type_name=None, ballot_title=None):
        self.id = id_
        self.ballot_title = ballot_title
        self.type_name = type_name

    def __repr__(self):
        title = i18n_repr(self.ballot_title)
        return f'<Choice {self.type_name!r} id={self.id!r} title={title[:70]!r}...>'


class Candidate(Choice):

    """
    A candidate can have additional attributes
    """

    auto_attrs = [
        ('_id', parse_id, 'id'),
        ('ballot_designation', parse_i18n),
        ('ballot_title', parse_i18n),
        ('candidate_party', parse_i18n),
    ]


def ballot_item_from_data(data, ballot_items_by_id):
    """
    Return a BallotItem object.
    """
    try:
        type_name = data['type']
    except KeyError:
        raise RuntimeError(f"key 'type' missing from data: {data}")

    cls = get_ballot_item_class(type_name)

    item = load_object(cls, data)

    if item.header_id:
        # Add this ballot item to the header's ballot item list.
        header = ballot_items_by_id.get(item.header_id, None)
        if not header:
            raise RuntimeError(f'Unknown header id {item.header_id!r}')
        header.add_child_item(item)

    return item


class Election:

    """
    The election is the root object for all content defined for an
    election operated by an Election Administration (EA), e.g. a
    county.

    An Election object without a date can be used to hold a definition
    of all current elected offices, represented as a contest and incumbents
    represented as candidate objects.
    """

    def process_ballot_items(self, value):
        """
        Scan the list of source data representing ballot items.

        Args:
          value: a list of dicts corresponding to the ballot items.
        """
        ballot_items_by_id = OrderedDict()
        for data in value:
            ballot_item = ballot_item_from_data(data, ballot_items_by_id)
            ballot_items_by_id[ballot_item.id] = ballot_item

        return ballot_items_by_id

    auto_attrs = [
        ('ballot_title', parse_i18n),
        ('election_area', parse_i18n),
        ('election_date', parse_date, 'date'),
        ('ballot_items', process_ballot_items, 'ballot_items_by_id'),
    ]

    def __init__(self):
        pass

    def __repr__(self):
        return f'<Election ballot_title={self.ballot_title!r} election_date={self.election_date!r}>'

    # Also expose the dict values as an ordered list, for convenience.
    @property
    def ballot_items(self):
        # Here we use that ballot_items_by_id is an OrderedDict.
        yield from self.ballot_items_by_id.values()

    @property
    def contests(self):
        for item in self.ballot_items:
            if isinstance(item, Contest):
                yield item


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


class BallotItem:

    """
    The BallotItem are items that appear on ballots-- either headers or
    contests. Each ballot item can be a subitem of a parent header.

    Attributes:
      id: must be unique across all contests or headers
      ballot_title: text appearing on ballots representing the header/contest
      ballot_subtitle: second level title for this item
      header_id: id of parent header object containing this item or 0 for root
      parent_header: the parent header of the item, as a Header object.
    """

    auto_attrs = [
        ('_id', parse_id, 'id'),
    ]

    def __init__(self, id_=None, ballot_title=None, ballot_subtitle=""):
        self.id = id_
        self.ballot_subtitle = ballot_subtitle
        self.ballot_title = ballot_title
        self.parent_header = None

    def __repr__(self):
        return f'<BallotItem id={self.id!r}>'

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


class Header(BallotItem):

    auto_attrs = [
        ('_id', parse_id, 'id'),
        ('ballot_title', parse_i18n),
        ('classification', parse_text),
        ('header_id', parse_text),
        ('type', parse_text),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ballot_items = []

    def __repr__(self):
        title = i18n_repr(self.ballot_title)
        return f'<Header id={self.id!r} title={title[:70]!r}...>'

    def add_child_item(self, item):
        """
        Link a child ballot item with its parent.

        Args:
          item: a BallotItem object.
        """
        self.ballot_items.append(item)
        item.parent_header = self  # back reference


class Contest(BallotItem):

    """
    The contest is a superclass of all contest types: offices, measures,
    and retention/recall. All contests have the following common attributes:
      id: must be unique across all contests or headers
      short_title: Short name for a contest usable in reports independent of
                   headers
      ballot_title: text appearing on ballots representing the contest
      choices: List of choices: candidates or Yes/No etc. on measures
               and recall/retention contests
    """

    def enter_choice(self, data, choice_cls, choices_by_id):
        """
        Common processing to enter a candidate or measure choice

        Args:
          choice_cls: the class to use to instantiate the choice.
        """
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
            c = self.enter_choice(data, choice_cls=self.choice_cls,
                            choices_by_id=choices_by_id)

        return choices_by_id

    auto_attrs = [
        ('_id', parse_id, 'id'),
        ('ballot_subtitle', parse_i18n),
        ('ballot_title', parse_i18n),
        # TODO: this should be parsed out.
        ('choice_names', parse_text),
        ('choices', enter_choices, 'choices_by_id'),
        ('header_id', parse_text),
        ('instructions_text', parse_text),
        ('is_partisan', parse_text),
        ('number_elected', parse_text),
        ('question_text', parse_text),
        ('type', parse_text),
        ('vote_for_msg', parse_text),
        ('vote_type_id', parse_text),
        ('writeins_allowed', parse_text),
    ]

    @classmethod
    def from_data(cls, data:dict):
        item = load_attrs(cls, data, unprocessed_keys=['choices', 'result_stats', 'subtotal_types'])

        # TODO: move the below into auto_attrs.
        result_stats = data.pop('result_stats')
        item.enter_result_stats(result_stats)

        subtotal_types = data.pop('subtotal_types')
        item.enter_subtotal_types(subtotal_types)

        return item

    def __init__(self, id_=None, ballot_title=None, ballot_subtitle=""):
        BallotItem.__init__(self, id_, ballot_title, ballot_subtitle)
        self.result_stats = []      # Pseudo choice for result summary attrs
        self.subtotal_types = []    # summary subtotals available
        self.result_details = []    # result detail definitions
        self.rcv_rounds = 0         # Number of RCV elimination rounds loaded

    # Also expose the dict values as an ordered list, for convenience.
    @property
    def choices(self):
        # Here we use that choices_by_id is an OrderedDict.
        yield from self.choices_by_id.values()

    def enter_result_stats(self, result_stats):
        """
        Scan summary result attributes for a contest
        """
        for data in result_stats:
            stat = load_object(ResultStat, data)
            index_object(self.choices_by_id, stat)
            self.result_stats.append(stat)

    def enter_subtotal_types(self, subtotal_types):
        """
        Scan summary subtotals available for this contest
        """
        for data in subtotal_types:
            append_result_subtotal(self, data, self.subtotal_types,
                subtotal_cls=SubtotalType)

    def enter_result_details(self, result_details):
        """
        Scan detail subtotals available for this contest
        """
        for data in result_details:
            append_result_subtotal(self, data, self.result_details,
                subtotal_cls=ResultDetail)


class OfficeContest(Contest):
    """
    The OfficeContest represents an elected office where choices are
    a set of candidates.
    """

    choice_cls = Candidate


class MeasureContest(Contest):
    """
    The MeasureContest represents a ballot measure question posed to voters.
    Most measures have a Yes/No question though the text that can appear on
    ballots for the response may be different, e.g. "Bonds Yes". For a
    yes/no question, the measure will pass or fail, depending on the approval
    required. Normally, the first choice is yes. Some measures might be
    multiple choice, e.g. preferred name of a proposed city, and might
    have more than 2 choices. Ranked Choice Voting could be used with a
    multiple choice measure.
    """

    choice_cls = Candidate


# In orr we don't need to distinguish from a measure.
class YNOfficeContest(MeasureContest):
    """
    A YNOfficeContest is a hybrid of MeasureContest and OfficeContest,
    used for approval voting (retention contest) or for a recall question.
    The attributes defining an elected office are included, and information
    on the incumbent/candidate can be defined.
    """
    pass


class ResultStat(Choice):

    """
    Besides votes for a candidate or measure choice, a set of vote/ballot
    totals are computed for a set of summary attributes that represent
    rejected votes and totals. The RESULT_STATS contain an id
    (that is distinct from a candidate/choice id) and "ballot_title"
    that can be used as a label in a report analogous to a candidate/choice name.
    """

    def __init__(self, id_=None, ballot_title=None):
        Choice.__init__(self, id_, ballot_title)


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
        ('_id', parse_id, 'id'),
        ('heading', parse_text),
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
        ('_id', parse_id, 'id'),
    ]

    def __init__(self, id_=None, area_heading=None, subtotal_heading=None,
                 is_vbm=False):
       self.id = id
       self.area_heading = area_heading
       self.subtotal_heading =subtotal_heading
       self.is_vbm = is_vbm
