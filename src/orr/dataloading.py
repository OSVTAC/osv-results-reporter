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
Support for loading our data model from input data.

The main function this module exposes is load_context().
"""

from collections import OrderedDict
from datetime import datetime
import functools
import logging

import orr.datamodel as datamodel
import orr.tsvio as tsvio
# TODO: move all but the model classes themselves into this module.
from orr.datamodel import (parse_int, Candidate, Choice, Contest, Header,
    ResultStatType, VotingGroup)
import orr.utils as utils
from orr.utils import truncate


_log = logging.getLogger(__name__)


def load_context(input_dir, build_time):
    """
    Read the input data, and return the context to use for Jinja2.

    Args:
      input_dir: the directory containing the input data, as a Path object.
      build_time: a datetime object representing the current build time,
        e.g. datetime.datetime.now().

    Returns a dict with keys:

      areas_by_id:
      build_time:
      election:
      languages:
      result_stat_types_by_id:
      result_styles_by_id:
      translations:
      voting_groups_by_id:
    """
    context = dict(build_time=build_time)

    path = input_dir / 'election.json'
    data = utils.read_json(path)

    # Inject the Election and Contest data loader methods defined
    # in this module.
    setattr(datamodel.Contest,
            'load_results_details',load_results_details)
    setattr(datamodel.Election,
            'load_all_results_details',load_all_results_details)
    setattr(datamodel.Election,
            'load_contest_status',load_contest_status)

    cls_info = dict(context=context, input_dir=input_dir)
    root_loader = RootLoader()
    load_object(root_loader, data, cls_info=cls_info, context=context)

    return context


def parse_as_is(obj, value):
    """
    Return the given value as is, without any validation, etc.
    """
    _log.debug(f'parsing as is: {truncate(value)}')
    return value


# TODO: add validation.
def parse_id(obj, value):
    """
    Remove and parse an id string from the given data.
    """
    _log.debug(f'parsing id: {value}')
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


def parse_date_time(obj, dt_string):
    """
    Remove and parse a date time from the given data.

    Args:
      dt_string: a datetime string in the format "2016-11-08 hh:mm:ss".
    """
    _log.debug(f'processing parse_date_time: {dt_string}')
    dt = utils.parse_datetime(dt_string)

    return dt


# TODO: add validation.
def parse_i18n(obj, value):
    """
    Remove and parse an i18n string from the given data.
    """
    _log.debug(f'processing parse_i18n: {truncate(value)}')
    return value


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

    def __repr__(self):
        # Using __qualname__ instead of __name__ includes also the class
        # name and not just the function / method name.
        try:
            func_name = self.load_value.__qualname__
        except AttributeError:
            func_name = repr(self.load_value)

        return f'<AutoAttr {self.attr_name!r}: data_key={self.data_key!r}, load_value={func_name}>'

    def make_load_value_kwargs(self, context):
        """
        Create and return the kwargs to pass to the load_value() function.

        Args:
          context: the current Jinja2 context.
        """
        context_keys = self.context_keys

        # Check that the context has the needed specified keys
        if context_keys and not context_keys <= set(context):
            missing = context_keys - set(context)
            msg = (f'context does not have keys {sorted(missing)} '
                   f'while calling {self.load_value}: {sorted(context)}')
            raise RuntimeError(msg)

        # Only pass the context keys that are needed / recognized.
        context = {key: context[key] for key in context_keys}

        if self.unpack_context:
            kwargs = context
        elif context:
            kwargs = dict(context=context)
        else:
            kwargs = {}

        return kwargs

    def process_key(self, obj, data, context):
        """
        Parse and process the value in the given data dict corresponding
        to the current AutoAttr instance.

        Args:
          data: the dict of data containing the key-value to process.
          context: the current Jinja2 context.
        """
        value = data.pop(self.data_key, None)
        if value is None:
            return

        kwargs = self.make_load_value_kwargs(context)

        # TODO: can we eliminate needing to pass obj if load_value doesn't
        #  depend on it?
        value = self.load_value(obj, value, **kwargs)

        return value


def index_objects(objects):
    """
    Set the index attribute on a sequence of objects, starting with 0.
    """
    for index, obj in enumerate(objects):
        obj.index = index


def add_object_by_id(mapping, obj):
    """
    Add an object to a dict mapping object id to object.

    Args:
      mapping: a dict to lookup by obj.id
      obj: object to be added
    """
    if not obj.id:
        raise RuntimeError(f'object does not have an id: {obj!r}')
    if obj.id in mapping:
        raise RuntimeError(f'duplicate object id: {obj!r}')

    mapping[obj.id] = obj


def create_mapping_by_id(objects):
    """
    Create and return an ordered dict mapping object id to object.
    """
    objects_by_id = OrderedDict()

    for obj in objects:
        add_object_by_id(objects_by_id, obj)

    return objects_by_id


def load_objects_to_mapping(load_data, seq, should_index=False):
    """
    Read from JSON data a list of objects, and return a dict mapping id
    to object.

    Args:
      load_data: a function with signature load_data(data) that returns
        an object of the proper type.
      seq: an iterable of data items to pass to load_data().
      should_index: whether to set the index attribute on the resulting
        objects (using 0-based indices).
    """
    objects = [load_data(data) for data in seq]
    if should_index:
        index_objects(objects)

    objects_by_id = create_mapping_by_id(objects)

    return objects_by_id


def process_auto_attr(loader, obj, attr, data, context):
    """
    Process an attribute in obj.auto_attrs.

    Args:
      loader: an instance of a Loader class.
      attr: an element of obj.auto_attrs.
      data: the dict of data containing the key-values to process.
      context: the current Jinja2 context.
    """
    if type(attr) != AutoAttr:
        assert type(attr) == tuple
        attr = AutoAttr(*attr)

    _log.debug(f'processing auto_attr {attr!r} for: {obj!r}')
    try:
        value = attr.process_key(obj, data=data, context=context)
    except Exception:
        raise RuntimeError(f'while processing auto_attr {attr!r} for: {obj!r}')

    try:
        setattr(obj, attr.attr_name, value)
    except Exception:
        raise RuntimeError(f"couldn't set {attr_name!r} on {obj!r}")


# TODO: make context required?
# TODO: rename cls_info to init_kwargs?
def load_object(loader, data, cls_info=None, context=None):
    """
    Set the attributes configured in the object's `auto_attrs` class
    attribute, from the given deserialized json data.

    Args:
      loader: an instance of a Loader class.
      data: the dict of data containing the key-values to process.
      cls_info: a dict of keyword arguments to pass to the class constructor
        before processing attributes.
      context: the current Jinja2 context.
    """
    if cls_info is None:
        cls_info = {}
    if context is None:
        context = {}

    auto_attrs = loader.auto_attrs
    model_cls = loader.model_class

    try:
        # This is where we use composition over inheritance.
        # We inject additional attributes and behavior into the class
        # constructor.
        obj = model_cls(**cls_info)
    except Exception:
        raise RuntimeError(f'error with model class {model_cls!r}: {cls_info!r}')

    # Set all of the (remaining) object attributes -- iterating over all
    # of the auto_attrs and parsing the corresponding JSON key values.
    for attr in auto_attrs:
        process_auto_attr(loader, obj, attr, data=data, context=context)

    # Check that all keys in the JSON have been processed.
    if data:
        raise RuntimeError(f'unrecognized keys for obj {obj!r}: {sorted(data.keys())}')

    if hasattr(loader, 'finalize'):
        # Perform class-specific init after data is loaded
        obj.finalize()

    return obj


#--- Results Data Loading Routines ---

def load_contest_status(election, filename=None):
    """
    Loads contest results status from a tsv file. Returns '' so
    this can be called from templates. No action is taken if
    the contest status has been loaded.

        Args:
            filename: The file containing the contest results data,
                to override the default.

    """
    # Skip if data has been loaded
    if hasattr(election,'_contest_status_loaded'):
        return ''

    if filename:
        election.result_contest_status_filename = filename

    tsvio.overlay_tsv_data(election.result_contest_status_filename,
                           election.contests_by_id, 'contest_id',
                     dict(
                        reporting_time=parse_date_time,
                        total_precincts=parse_int,
                        precincts_reporting=parse_int,
                        rcv_rounds=parse_int))

    # Use _contest_status_loaded as a marker data has been loaded
    election._contest_status_loaded = True

    return ''


def load_results_details(contest, filename=None):
    """
    Load the detailed results for this contest with reporting groups with
    a breakdown by precinct/district.

    Args:
        filename: name of a specific result file to load. If not
                    specified, the name will be composed with the
                    election.get_result_detail_filename.
    """
    if hasattr(contest,'results'):
        return ''

    if not filename:
        filename = contest.result_detail_filename

    _log.debug(f'load_results_details({filename})')

    contest.choice_count = len(contest.choices_by_id)
    contest.reporting_group_count = len(contest.reporting_groups)
    contest.results = []
    contest.rcv_results = [ [None] * contest.rcv_rounds ]
    with tsvio.Reader(filename) as reader:
        # Simple check, just validate the column count
        # We could validate the header if we like later
        if reader.num_columns != 2 + contest.result_stat_count + contest.choice_count:
            raise RuntimeError(
                f'Mismatched column heading in {filename}: {reader.line} stats={contest.result_stat_count} choices={contest.choice_count}')

        # RCV rounds are first
        next_rcv_round = contest.rcv_rounds
        for cols in reader.readlines():
            #_log.debug(f'col {cols}')
            if len(cols) != reader.num_columns:
                raise RuntimeError(
                    f'Mismatched columns in {filename}: {reader.line}')
            if next_rcv_round:
                # Separate the RCV results array
                if cols[0] != f'RCV{next_rcv_round}':
                    raise RuntimeError(
                        f'Mismatched RCV line {next_rcv_round} in {filename}: {line}')
                contest.rcv_results[next_rcv_round] = cols[2:]
                next_rcv_round -= 1
            else:
                # We could verify the reporting group but will skip
                contest.results.append([ int(v) for v in cols[2:]])

        if len(contest.results) != contest.reporting_group_count:
            raise RuntimeError(
                f'Mismatched reporting groups in {filename}')


    # Return a null string so this can be called in a template
    return ''

def load_all_results_details(election, filedir=None, filename_format=None):
    """
    Loads results details for all contests in the election. If
    filedir or filename_format is specified, the prior
    default values are reset.

    Returns '' so this routine can be called from Jinja

    Args:
        filedir: The directory containing the detailed results data
        filename_format: Format string with {} for contest id to
                            create the results source file name.
    """
    if filedir:
        election.result_detail_dir = filedir

    if filename_format:
        election.result_detail_format_filepath = filename_format

    for c in election.contests:
        c.load_results_details()

    return ''

# VotingGroup loading

class VotingGroupLoader:

    model_class = datamodel.ResultStatType

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('heading', parse_i18n),
    ]


#--- Loaders for datamodel Classes ---

# ResultStatType loading

class ResultStatTypeLoader:

    model_class = datamodel.ResultStatType

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('heading', parse_i18n),
        ('is_percent', parse_bool),
    ]


# ResultStyle loading

def make_index_map(values):
    """
    Return an `indexes_by_value` dict mapping the value to its (0-based)
    index in the list.
    """
    return {value: index for index, value in enumerate(values)}


# TODO: remove this?
def make_id_to_index_map(objlist):
    """
    An `indexes_by_id` dict mapping an object id to list index is created
    for a list of objects. The index converts the id to the index
    in the list 0..len(objlist)-1
    """
    return make_index_map(obj.id for obj in objlist)


def process_index_idlist(objects_by_id, idlist):
    """
    Parse a space-separated list of object IDS into objects.

    Args:
      idlist: a space-separated list of IDS, as a string.
      objects_by_id: the dict of all objects of a single type, mapping
        object id to object.

    Returns: (objects, indexes_by_id)
      objects: the objects as a list.
      indexes_by_id: a dict mapping object id to its (0-based) index in
        the list.
    """
    ids = datamodel.parse_idlist(idlist)
    indexes_by_id = make_index_map(ids)
    objects = [objects_by_id[object_id] for object_id in ids]

    return objects, indexes_by_id


# We want a name other than load_result_stat_types() for uniqueness reasons.
def load_stat_types(result_style, value, result_stat_types_by_id):
    result_stat_types, indexes_by_id = process_index_idlist(result_stat_types_by_id, value)
    result_style.result_stat_type_index_by_id = indexes_by_id

    return result_stat_types


# We want a name other than load_voting_groups() for uniqueness reasons.
def load_result_voting_groups(result_style, value, voting_groups_by_id):
    voting_groups, indexes_by_id = process_index_idlist(voting_groups_by_id, value)
    result_style.voting_group_indexes_by_id = indexes_by_id

    return voting_groups


class ResultStyleLoader:

    model_class = datamodel.ResultStyle

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('description', parse_i18n),
        ('is_rcv', parse_bool),
        AutoAttr('voting_groups', load_result_voting_groups,
            data_key='voting_group_ids', context_keys=('voting_groups_by_id',),
            unpack_context=True),
        AutoAttr('result_stat_types', load_stat_types,
            data_key='result_stat_type_ids', context_keys=('result_stat_types_by_id',),
            unpack_context=True),
    ]


# Area loading

class AreaLoader:

    model_class = datamodel.Area

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('classification', parse_as_is),
        ('name', parse_i18n),
        ('short_name', parse_i18n),
        ('is_vbm', parse_bool),
        ('consolidated_ids', parse_as_is),
        ('reporting_group_ids', parse_as_is),
    ]


# Header loading

class HeaderLoader:

    model_class = Header

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_title', parse_i18n),
        ('classification', parse_as_is),
        # This is needed only while loading.
        # TODO: can we eliminate having to store this as an attribute?
        AutoAttr('_header_id', parse_as_is, data_key='header_id'),
    ]


# Choice loading

class ChoiceLoader:

    model_class = Choice

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_title', parse_i18n),
    ]


# Candidate loading

class CandidateLoader:

    model_class = Candidate

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_title', parse_i18n),
        ('ballot_designation', parse_i18n),
        ('candidate_party', parse_i18n),
    ]


# Contest loading

# Dict mapping contest data "_type" name to choice loader class.
BALLOT_ITEM_CLASSES = {
    'office': CandidateLoader,
    'measure': ChoiceLoader,
    'ynoffice': ChoiceLoader,
}

def load_single_choice(contest, data):
    """
    Common processing to enter a candidate or measure choice

    Args:
      choice_cls: the class to use to instantiate the choice.
    """
    choice_cls = contest.choice_cls
    choice_loader = choice_cls()
    choice = load_object(choice_loader, data)
    choice.contest = contest     # Add back reference

    return choice


def load_choices(contest, choices_data):
    """
    Scan an input data list of contest choice entries to create.

    Args:
      choice_cls: the class to use to instantiate the choice (e.g.
        Candidate or Choice).
    """
    load_data = functools.partial(load_single_choice, contest)
    choices_by_id = load_objects_to_mapping(load_data, choices_data, should_index=True)

    return choices_by_id


# We want a name other than load_result_styles() for uniqueness reasons.
def load_contest_result_style(contest, value, result_styles_by_id):
    return result_styles_by_id[value]


def load_voting_district(contest, value, areas_by_id):
    return areas_by_id[value]


class ContestLoader:

    model_class = Contest

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_subtitle', parse_i18n),
        ('ballot_title', parse_i18n),
        # TODO: this should be parsed out.
        ('choice_names', parse_as_is),
        ('choices_by_id', load_choices, 'choices'),
        # This is needed only while loading.
        # TODO: can we eliminate having to store this as an attribute?
        AutoAttr('_header_id', parse_as_is, data_key='header_id'),
        ('instructions_text', parse_as_is),
        ('is_partisan', parse_as_is),
        ('number_elected', parse_as_is),
        ('question_text', parse_as_is),
        AutoAttr('result_style', load_contest_result_style,
            context_keys=('result_styles_by_id',), unpack_context=True),
        AutoAttr('voting_district', load_voting_district,
            context_keys=('areas_by_id',), unpack_context=True),
        ('type', parse_as_is),
        ('vote_for_msg', parse_as_is),
        ('writeins_allowed', parse_int),
    ]


def load_single_contest(data, election, context):
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

    areas_by_id = context['areas_by_id']
    voting_groups_by_id = context['voting_groups_by_id']

    cls_info = dict(type_name=type_name,
        choice_cls=choice_cls, election=election, areas_by_id=areas_by_id,
        voting_groups_by_id=voting_groups_by_id)

    contest_loader = ContestLoader()
    contest = load_object(contest_loader, data, cls_info=cls_info, context=context)

    return contest


# Election loading

def add_child_to_header(header, item):
    """
    Link a child ballot item with its parent.

    Args:
      header: the parent header, as a Header object.
      item: a Contest or Header object.
    """
    assert type(item) in (Contest, Header)

    header.ballot_items.append(item)
    item.parent_header = header  # back reference


def link_with_header(item, headers_by_id):
    """
    Add the two-way association between a ballot item (header or contest)
    and its header, if it has a header.

    Args:
      item: a Header or Contest object.
    """
    header_id = item._header_id

    if not header_id:
        # Then there is nothing to do.
        return

    # Add this ballot item to the header's ballot item list.
    try:
        header = headers_by_id[header_id]
    except KeyError:
        msg = f'Header id {header_id!r} not found for item: {item!r}'
        raise RuntimeError(msg)

    add_child_to_header(header, item)


def load_headers(election, headers_data):
    """
    Process the source data representing the header items.

    Returns an OrderedDict mapping header id to Header object.

    Args:
      headers_data: a list of dicts corresponding to the Header objects.
    """
    load_data = functools.partial(load_object, HeaderLoader)
    headers_by_id = load_objects_to_mapping(load_data, headers_data, should_index=True)

    for header in headers_by_id.values():
        link_with_header(header, headers_by_id=headers_by_id)

    return headers_by_id


def load_contests(election, contests_data, context):
    """
    Process the source data representing the contest items.

    Returns an OrderedDict mapping contest id to Contest object.

    Args:
      contests_data: a list of dicts corresponding to the Contest objects.
    """
    load_data = functools.partial(load_single_contest, election=election, context=context)
    contests_by_id = load_objects_to_mapping(load_data, contests_data, should_index=True)

    for contest in contests_by_id.values():
        link_with_header(contest, headers_by_id=election.headers_by_id)

    return contests_by_id


class ElectionLoader:

    model_class = datamodel.Election

    auto_attrs = [
        ('ballot_title', parse_i18n),
        ('date', parse_date, 'election_date'),
        ('election_area', parse_i18n),
        # Process headers before contests since the contest data references
        # the headers but not vice versa.
        ('headers_by_id', load_headers, 'headers'),
        AutoAttr('contests_by_id', load_contests, data_key='contests',
            context_keys=('areas_by_id', 'result_styles_by_id', 'voting_groups_by_id')),
    ]


# Root context loading

class ModelRoot:

    """
    A helper class for loading of all of the input data and populating
    the Jinja2 context.

    Instance attributes:

      context:
      input_dir:
    """

    def __init__(self, context, input_dir):
        """
        Args:
          context: the current Jinja2 context.
          input_dir: the directory containing the input data, as a Path object.
        """
        name_values = [
            ('context', context),
            ('input_dir', input_dir),
        ]
        for name, value in name_values:
            # Call super() to bypass our override.
            super().__setattr__(name, value)

    # Override __setattr__ to cause load_object() to add attr values to
    # the Jinja2 context rather than storing them to instance attributes.
    def __setattr__(self, name, value):
        self.context[name] = value


def load_result_stat_types(root, types_data):
    """
    Args:
      root: a ModelRoot object.
    """
    load_data = functools.partial(load_object, ResultStatTypeLoader)
    return load_objects_to_mapping(load_data, types_data)


def load_voting_groups(root, groups_data):
    """
    Args:
      root: a ModelRoot object.
    """
    load_data = functools.partial(load_object, VotingGroupLoader)
    return load_objects_to_mapping(load_data, groups_data)


def load_result_styles(root, styles_data, context):
    """
    Args:
      root: a ModelRoot object.
    """
    load_data = functools.partial(load_object, ResultStyleLoader, context=context)
    return load_objects_to_mapping(load_data, styles_data)


def load_areas(root, areas_data):
    """
    Process source data representing an area (e.g. precinct or district).
    """
    load_data = functools.partial(load_object, AreaLoader)
    areas_by_id = load_objects_to_mapping(load_data, areas_data)

    return areas_by_id


def load_election(root, election_data, context):
    """
    Args:
      root: a ModelRoot object.
    """
    cls_info = dict(input_dir=root.input_dir)
    election_loader = ElectionLoader()
    return load_object(ElectionLoader, election_data, cls_info=cls_info, context=context)


class RootLoader:

    model_class = ModelRoot

    auto_attrs = [
        ('languages', parse_as_is),
        ('translations', parse_as_is),
        # Set "result_stat_types_by_id" and "voting_groups_by_id" now since
        # processing "election" depends on them.
        ('result_stat_types_by_id', load_result_stat_types, 'result_stat_types'),
        ('voting_groups_by_id', load_voting_groups, 'voting_groups'),
        # Processing result_styles requires result_stat_types and voting_groups.
        AutoAttr('result_styles_by_id', load_result_styles, data_key='result_styles',
            context_keys=('result_stat_types_by_id', 'voting_groups_by_id')),
        ('areas_by_id', load_areas, 'areas'),
        AutoAttr('election', load_election,
            context_keys=('areas_by_id', 'result_styles_by_id', 'voting_groups_by_id')),
    ]

