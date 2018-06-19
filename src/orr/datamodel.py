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


def parse_as_is(obj, value):
    """
    Return the given value as is, without any validation, etc.
    """
    _log.debug(f'parsing as is: {value}')
    return value


# TODO: add validation.
def parse_id(obj, value):
    """
    Remove and parse an id string from the given data.
    """
    _log.debug(f'parsing id: {value}')
    return value


def parse_int(obj, value):
    """
    Remove and parse an int string from the given data.
    """
    _log.debug(f'parsing int: {value}')
    # TODO str conversion
    return value


def parse_bool(obj, value):
    """
    Remove and convert a bool value as True, False, or None.
    A string value of Y or N becomes True or False, and a null
    string maps to None. [The distinction facilitates import from
    untyped input, e.g. TSV.]
    """
    _log.debug(f'parsing bool: {value}')
    if type(value) is str:
        if value == '':
            value = None
        elif value[0] in "YyTt1":
            value = True
        elif value[0] in "NnFf0":
            value = False
        else:
            raise RuntimeError(
                f'invalid boolean value for obj {obj!r}: {value}')
    elif type(value) is int:
        value = value != 0
    elif type(value) is not bool and value != None:
        raise RuntimeError(
                f'invalid boolean value for obj {obj!r}: {value}')

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

def parse_date_time(obj, value):
    """
    Remove and parse a date time from the given data.

    Args:
      value: a date string, e.g. of the form "2016-11-08 hh:mm:ss".
    """
    _log.debug(f'processing parse_date: {value}')

    date = datetime.strptime(value, '%Y-%m-%d %H:%M:%S').date()

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


class AutoAttr:

    """
    Defines an attribute to set when loading JSON data, and how to load it.
    """

    def __init__(self, attr_name, load_value, data_key=None, context_keys=None,
        unpack_context=False):
        """
        Args:
          attr_name: the name of the attribute.
          load_value: the function to call when loading.  The function
            should have the signature load_value(obj, value, ...).
          data_key: the name of the key to access from the JSON to obtain
            the data value to pass to load_value().  Defaults to attr_name.
          context_keys: the name of the context keys that processing this
            attribute depends on.  Defaults to not depending on the context.
          unpack_context: whether to unpack the context argument into
            kwargs when calling the load_value() function.
        """
        if data_key is None:
            data_key = attr_name
        if context_keys is None:
            context_keys = []

        self.attr_name = attr_name
        self.context_keys = set(context_keys)
        self.data_key = data_key
        self.load_value = load_value
        self.unpack_context = unpack_context


# TODO: make context required?
def load_object(cls, data, cls_info=None, context=None):
    """
    Set the attributes configured in the object's `auto_attrs` class
    attribute, from the given deserialized json data.
    """
    if cls_info is None:
        cls_info = {}
    if context is None:
        context = {}

    try:
        # This is where we use composition over inheritance.
        # We inject additional attributes and behavior into the class
        # constructor.
        obj = cls(**cls_info)
    except Exception:
        raise RuntimeError(f'error with cls {cls!r}: {cls_info!r}')

    for info in obj.auto_attrs:
        # TODO: simplify this logic.
        if type(info) == AutoAttr:
            attr_name = info.attr_name
            context_keys = info.context_keys
            data_key = info.data_key
            load_value = info.load_value
            remaining = []

            # Check that the context has the needed specified keys
            if context_keys and not context_keys <= set(context):
                msg = (f'context does not have keys {sorted(context_keys)} '
                       f'while calling {load_value}: {sorted(context)}')
                raise RuntimeError(msg)

            if info.unpack_context:
                # Only unpack the context keys that are needed / recognized.
                kwargs = {key: context[key] for key in context_keys}
            else:
                kwargs = dict(context=context)

        else:
            attr_name, load_value, *remaining = info
            kwargs = {}

            if remaining:
                data_key = remaining.pop(0)
            else:
                data_key = attr_name

        _log.debug(f'processing auto_attr: ({attr_name}, {data_key}, {load_value})')
        value = data.pop(data_key, None)
        if value is not None:
            try:
                value = load_value(obj, value, *remaining, **kwargs)
            except Exception:
                raise RuntimeError(f'while processing attr_name {attr_name!r} for: {obj!r}')

        try:
            setattr(obj, attr_name, value)
        except Exception:
            raise RuntimeError(f"couldn't set {attr_name!r} on {obj!r}")

    if data:
        raise RuntimeError(
            f'unrecognized keys for obj {obj!r}: {sorted(data.keys())}')

    if hasattr(cls, 'finalize'):
        # Perform class-specific init after data is loaded
        obj.finalize()
    return obj

def process_id(obj, idstr, mapname):
    """
    Convert a string ID into a reference to the object
    """

    return mapping[idstr]

def process_id_in_election(obj, idstr, mapname):
    """
    Convert a string ID into a reference to the object from a dict
    within the obj.election dict
    """

    return getattr(obj.election,mapname)[idstr]


def process_index_idlist(data, objects_by_id):
    """
    Parse a space-separated list of object IDS into objects.

    Args:
      data: a space-separated list of IDS, as a string.
      objects_by_id: the dict of all objects of a single type, mapping
        object id to object.

    Returns: (objects, indexes_by_id)
      objects: the objects as a list.
      indexes_by_id: a dict mapping (0-based) index to object.

    """
    ids = data.split()
    indexes_by_id = {object_id: index for index, object_id in enumerate(ids)}
    objects = [objects_by_id[object_id] for object_id in ids]

    return objects, indexes_by_id


def process_idlist(obj, liststr, mapname):
    """
    For a list represented as a space separated list of IDs, split
    the string and return the values from the mapping dict.
    """
    mapping = getattr(obj,mapname)
    return [mapping[i] for i in liststr.split()]


# TODO: choose a better name.
def mapped_object(mapping, obj):
    """
    Enter the object in the "mapping" dict.

    Args:
      mapping: a dict to lookup by obj.id
      obj: object to be added
    """
    if not obj.id:
        raise RuntimeError(f'object does not have an id: {obj!r}')
    if obj.id in mapping:
        raise RuntimeError(f'duplicate object id: {obj!r}')

    mapping[obj.id] = obj


def index_object(mapping, obj):
    """
    Add an object in our data model to a lookup dict that references
    objects by id, and also add an index / sequence number.

    Args:
      mapping: a dict to lookup by obj.id
      obj: object to be added
    """
    # TODO: don't set obj.index here e.g. since choices and results are combined?
    # TODO: assign index numbers at the end, when creating the convenience
    #  list for an object type?
    obj.index = len(mapping)  # Assign a sequence number (0-based)
    mapped_object(mapping,obj)


def read_objects_to_dict(cls, seq, context=None):
    """
    Read from JSON data a list of objects that don't require an "index"
    attribute.

    Returns a dict mapping id to object.

    Args:
      context: optional context dictionary that load_object() for the
        class depends on.
    """
    obj_by_id = OrderedDict()
    for data in seq:
        item = load_object(cls, data, context=context)
        mapped_object(obj_by_id, item)

    return obj_by_id


def form_index_dict(objlist):
    """
    A dict mapping an object id to list index is created for
    a list of objects. The index converts the id to the index
    in the list 0..len(objlist)-1
    """
    mapping = {}
    i = 0
    for obj in objlist:
        mapping[obj.id] = i
        i += 1

    return mapping

def map_idlist(mapping, idlist):
    """
    Splits a space separated list of ids and returns the non-null
    values as a result.
    """
    return [mapping[k] for k in idlist.split() if k in mapping]

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
    """

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('heading', parse_i18n)
    ]

    def __init__(self):
        self.id = None
        self.heading = None

class ResultStatType:
    """
    The ResultStatType represents a type of results statistics value
    computed for a contest, in addition to the vote values totaled
    for each choice. This is an enumerated type with a an i18n
    printable heading.
    """
    auto_attrs = [
        ('id', parse_id, '_id'),
        ('heading', parse_i18n),
        ('is_percent', parse_bool)
    ]

    def __init__(self):
        self.id = None
        self.heading = None

class ResultStyle:

    """
    Each contest references the id of a ResultStyle that defines a
    set of attributes for the type of voting including what result stats
    will be available.
    """

    def process_result_stat_types(self, value, result_stat_types_by_id):
        result_stat_types, indexes_by_id = process_index_idlist(value, result_stat_types_by_id)
        self.result_stat_type_index_by_id = indexes_by_id

        return result_stat_types

    def process_voting_groups(self, value, voting_groups_by_id):
        voting_groups, indexes_by_id = process_index_idlist(value, voting_groups_by_id)
        self.voting_group_index_by_id = indexes_by_id

        return voting_groups

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('description', parse_i18n),
        ('is_rcv', parse_bool),
        AutoAttr('voting_groups', process_voting_groups,
            data_key='voting_group_ids', context_keys=('voting_groups_by_id',),
            unpack_context=True),
        AutoAttr('result_stat_types', process_result_stat_types,
            data_key='result_stat_type_ids', context_keys=('result_stat_types_by_id',),
            unpack_context=True),
    ]

    def __init__(self):
        self.id = None

    def voting_group_indexes_by_id(self, idlist):
        """
        Returns the list of voting group index values by the
        space separated list of ids. Unmatched ids are omitted.
        """
        if not idlist or idlist == "*":
            return range(len(self.voting_groups))

        return map_idlist(self.result_stat_type_index_by_id, idlist)



class ReportingGroup:
    """
    The reporting group defines an (Area, VotingGroup) tuple for
    results subtotals. The Area ID '*' is a special placeholder meaning
    all precincts (in a contest), and VotingGroup 'TO' is used for
    all voters. Each voting district active in an election should have
    a reporting_group_ids string that is a space-separated list of
    area_id~voting_group_id ID pairs that reference a list of (area,group)
    tuples.

    When creating a ReportingGroup, it is appended to the district.
    """
    def __init__(self, area, voting_group):
        self.area = area
        self.voting_group = voting_group
        self.index = len(district.reporting_groups)
        district.reporting_groups.append(self)

# --- Precinct/District definitions ---

class Area:
    """
    The Area object represents any kind of precinct or district
    that corresponds to a geographic area. ID codes for precincts
    and districts must be unique across all types.

    Sometimes we want to access IDs that may be either a precinct
    or district (i.e. a Precinct acts as a district for voting),
    but usually precints and districts are distinct.
    """
    def __init__(self):
        self.id = None
        self.name = None
        self.short_name = None
        self.is_vbm = False

class Precinct(Area):
    """
    The Precinct object can represent a base precinct, a precinct
    split (precinct divided into unique combinations of intersecting
    districts), or consolidated precinct-- a group of precincts
    combined for voting and reporting. A consolidated precinct may
    be the same as a base precinct, i.e. have only one precinct.

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
    """
    auto_attrs = [
        ('id', parse_id, '_id'),
        ('name', parse_i18n),
        ('short_name', parse_i18n),
        ('is_vbm', parse_bool),
        ('consolidated_ids',parse_as_is)
    ]

    def __init__(self):
        Area.__init__(self)

class District:
    """
    The District represents a geographic area representing an organization
    (jurisdiction/public agency) as a whole, or a portion of the
    organization representing a seat on a board (e.g. Council District),
    a proposed transfer area (e.g. change of school district), or
    tax assessment area (e.g. for road improvements, School Facilities
    Improvement District). [An SFID is a portion of a school district
    with tax assessment or bond funding certain schools.]

    A district may have is_vbm if all precincts in that district
    are marked as VBM only.

    A subclass of District can also represent the geographic area
    for a zip code, or Census Block/Block-Group. Normally data,
    representing zip code associations and/or Census Blocks are
    maintained in separate data lists, but should have IDs within
    the shared Area namespace.

    The voting district for a contest may be associated with a list
    of "reporting groups"

    The special ID * is used as a placeholder for "All Precincts",
    meaning all precincts associated with a contest, or all precincts
    within an Election Administration (e.g. county).
    """

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('name', parse_i18n),
        ('short_name', parse_i18n),
        ('is_vbm', parse_bool),
        ('classification', parse_as_is),
        ('reporting_group_ids', parse_as_is)
    ]

    def __init__(self):
        Area.__init__(self)
        self._reporting_groups = None;

    @property
    def reporting_groups(self):
        if self._reporting_groups == None:
            # Create the reporting_groups list from IDs on first access
            self._reporting_groups = []
            for s in self.reporting_group_ids.split():
                m = re.match(r'(.*)~(.*)',s)
                if not m:
                    raise RuntimeError(
                        f"invalid reporting_group_ids '{s}' for district {self.id}")
                area_id, group_id = m.groups()
                rg = ReportingGroup(
                    self.election.areas_by_id[area_id],
                    self.election.voting_groups_by_id[group_id])
                setattr(rg, 'index', len(self._reporting_groups))
                self._reporting_groups.append(rg)
        return self._reporting_groups



# --- Ballot Item definitions

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
        self.areas_by_id = OrderedDict()

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

    def result_index(self):
        """
        Returns the column index into result values corresponding
        to this choice.
        """
        return self.index + contest.result_stat_count

    def summary_results(self, group_idlist=None):
        """
        Returns the contest.summary_results with the choice_stat_index
        computed for this choice.
        """

        return self.contest.summary_results(self.result_index,idlist)

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
    def from_data(cls, data, election):
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

        cls_info = dict(type_name=type_name, choice_cls=choice_cls,
                        election=election)

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


    # List of results detail headers to copy to the contest
    results_details_headers = dict(
        reporting_time=parse_date_time,
        total_precincts=parse_int,
        precincts_reporting=parse_int,
        rcv_rounds=parse_int)

    def load_results_details(self, filename=None):
        """
        Load the detailed results for this contest with reporting groups with
        a breakdown by precinct/district.

        Args:
            filename: name of a specific result file to load. If not
                      specified, the name will be composed with the
                      election.get_result_detail_filename.
        """
        if self.getattr('results',None):
            return

        if not filename:
            filename = self.election.get_result_detail_filename(self.id)

        _log.debug(f'load_results_details({filename})')

        with open(filename, encoding='utf-8') as f:
            for line in f:
                # Read keyword header lines
                if line == "---\n":
                    break
                m = re.match(r'^(\w+):\s*(.*)',line)
                if not m:
                    raise RuntimeError(
                        f'invalid results line {line} in {filename}')
                k, v = m.groups()
                if k in results_details_headers:
                    setattr(self, k, results_details_headers[k](self, v))

            # TODO: validate the format with contests hash
            # Copy the number of result stat types in this contest

            # Init column counts and 2D array of values
            self.result_stat_count = len(self.result_style.result_stat_types)
            self.choice_count = len(self.choices_by_id)
            self.reporting_group_count = len(self.reporting_groups)
            self.results = []
            self.rcv_results = [ None * self.rcv_rounds ]

            # Read the column heading definition
            line = f.readline()
            ncols = len(line.split(sep='|'))
            if ncols != 2 + self.result_stat_count + self.choice_count:
                raise RuntimeError(
                    f'Mismatched column heading in {filename}: {line}')
            # We could verify column headings, but instead validate based
            # on a hash checksum of contest definitions, so the heading
            # line becomes a comment for unvalidated input

            # Read the results, RCV first
            next_rcv_round = self.rcv_rounds
            for line in f:
                cols = line.split(sep='|')
                if len(cols) != ncols:
                    raise RuntimeError(
                        f'Mismatched columns in {filename}: {line}')
                if next_rcv_round:
                    # Separate the RCV results array
                    if cols[0] != f'RCV{next_rcv_round}':
                        raise RuntimeError(
                            f'Mismatched RCV line {next_rcv_round} in {filename}: {line}')
                    self.rcv_results[next_rcv_round] = cols[2:]
                    next_rcv_round -= 1
                else:
                    # We could verify the reporting group but will skip
                    self.results.append(cols[2:])
            if len(self.results) != self.reporting_group_count:
                raise RuntimeError(
                    f'Mismatched reporting groups in {filename}')

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
        # An empty
        if not stat_idlist:
            return range(self.result_stat_count)

        # A list comprehension is not easy due to python limitations
        l = []
        mapping = self.result_style.result_stat_type_index_by_id
        for k in stat_idlist.split():
            if k == '*':
                l.extend(range(self.result_stat_count))
            elif k == 'CHOICES':
                l.extend(range(self.result_stat_count,
                               self.result_stat_count+self.choice_count))
            elif k in mapping:
                l.append(mapping[k])

        return l


    def result_stats_by_id(self, group_idlist=None):
        """
        Returns a list of ResultStatType, either all or the list
        matching the space separated IDs.
        """
        return [ self.result_style.result_stat_types[i]
                for i in self.result_stat_indexes_by_id(group_idlist) ]


    def summary_results(self, choice_stat_index, group_idlist=None):
        """
        Returns a list of vote summary values (total votes for each
        VotingGroup defined. If group_idlist is defined it will be
        interpreted as a space separated list of VotingGroup IDs.
        """
        # Load the results if not already loaded
        self.load_results_details()

        # TODO: check choice_stat_index
        return [ self.results[i][choice_stat_index]
                 for i in
                 self.result_style.voting_group_indexes_by_id(idlist) ]

    def detail_results(self, reporting_index, choice_stat_idlist=None):
        """
        Returns a list of vote stat and choice values for the reporting
        group correspinding to the reporting_index value. Reporting
        """

        # TODO: check

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
        ('result_style', process_id_in_election, 'result_style', 'result_style_by_id'),
        ('voting_district', process_id_in_election, 'voting_district', 'areas_by_id'),
        ('type', parse_as_is),
        ('vote_for_msg', parse_as_is),
        ('writeins_allowed', parse_int),
    ]

    def __init__(self, type_name, choice_cls=None, id_=None, election=None):
        assert type_name is not None
        assert election is not None

        self.id = id_
        self.type_name = type_name
        self.choice_cls = choice_cls
        self.election = election

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

    @property
    def reporting_groups(self):
        if self._reporting_groups == None:
            _reporting_groups = self.voting_district.reporting_groups
        return _reporting_groups

    @property
    def result_stat_count(self):
        """
        Helper function to get the number of result stats
        """
        return len(self.result_style.result_stat_types)

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

    def process_areas(self, value, cls):
        """
        Process source data representing a precinct or district. The
        object is entered into the Election.areas_by_id.

        Returns a list of either Precincts or Districts.

        Args:
          value: a list of dicts corresponding to the Precinct objects.
        """
        areas = []
        for data in value:
            area = load_object(cls, data)
            setattr(area, 'election', self)
            areas.append(area)
            mapped_object(self.areas_by_id, area)

        return areas

    def process_result_stat_types(self, value):
        return read_objects_to_dict(ResultStatType, value, context=context)

    def process_result_styles(self, value, context):
        return read_objects_to_dict(ResultStyle, value, context=context)

    def process_voting_groups(self, value):
        return read_objects_to_dict(VotingGroup, value)

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
            contest = Contest.from_data(data, self)
            process_header_id(contest, headers_by_id)
            index_object(contests_by_id, contest)

        return contests_by_id

    auto_attrs = [
        ('ballot_title', parse_i18n),
        ('date', parse_date, 'election_date'),
        ('election_area', parse_i18n),
        ('languages', parse_as_is),
        ('translations', parse_as_is),
        # Process precincts and districts before contests so
        # contests may reference and map the district ID
        ('districts', process_areas, 'districts', District),
        ('precincts', process_areas, 'precincts', Precinct),
        # Enter the VotingGroup and enumerated definitions
        ('voting_groups_by_id', process_voting_groups, 'voting_groups'),
        # Processing result_styles requires result_stat_types and voting_groups.
        AutoAttr('result_style_by_id', process_result_styles,
            data_key='result_styles', context_keys=('result_stat_types_by_id', )),
        # Process headers before contests since the contest data references
        # the headers but not vice versa.
        ('headers_by_id', process_headers, 'headers'),
        ('contests_by_id', process_contests, 'contests'),
    ]

    def __init__(self):
        self.areas_by_id = OrderedDict()
        self.result_detail_dir = "./resultdata"
        self.result_detail_format_filepath = "{}/results.{}.psv"

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

    def get_result_detail_filename(self,contest_id):
        """
        Returns the file path and name for detailed results source data
        to be loaded, based on the contest ID. The directory and/or file
        name formatting can be configured in the election settings.
        """
        return self.result_detail_format_filepath.format(
            self.result_detail_dir,contest_id)


    def load_results_details(self, filedir=None, filename_format=None):
        """
        Loads results details for all contests in the election. If
        filedir or filename_format is specified, the prior
        default values are reset.

        Args:
            filedir: The directory containing the detailed results data
            filename_format: Format string with {} for contest id to
                             create the results source file name.
        """

        if filedir:
            self.result_detail_dir = filedir

        if filename_format:
            self.result_detail_format_filepath = filename_format

        for c in self.contests:
            c.load_results_details()
