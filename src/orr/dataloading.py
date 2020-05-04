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
import json
import itertools
import logging
from pathlib import Path

import orr.datamodel as datamodel
from orr.datamodel import AREA_ID_ALL, VOTING_GROUP_ID_ALL, WINNING_STATUSES
import orr.tsvio as tsvio
from orr.tsvio import TSVLines, TSVReader
from orr.datamodel import (Candidate, Choice, Contest, Election, Header,
    ResultStatType, ResultStyle, ResultsMapping, Turnout, VotingGroup)
import orr.utils as utils
from orr.utils import truncate


_log = logging.getLogger(__name__)


INPUT_FILE_NAME = 'election.json'

# The default directory containing the detailed results data files,
# relative to the input directory.
DEFAULT_RESULTS_DIR_NAME = 'resultdata'

# The name of the results file, inside the input results directory.
RESULTS_FILE_NAME = 'results.json'

# The format string for the name of the file in the results directory
# containing the detailed results for a contest.
CONTEST_RESULTS_FILE_NAME_FORMAT = 'results-{}.tsv'


def load_context(input_dir, input_results_dir, build_time):
    """
    Read the input data, and return the context to use for Jinja2.

    Args:
      input_dir: the directory containing the election.json file, as a
        Path object.
      input_results_dir: the directory containing the detailed results
        data files, as a Path object.
      build_time: a datetime object representing the current build time,
        e.g. datetime.datetime.now().

    Returns a dict with keys:

      areas_by_id:
      build_time:
      election:
      languages:
      parties_by_id:
      result_stat_types_by_id:
      result_styles_by_id:
      translations:
      voting_groups_by_id:
    """
    context = dict(build_time=build_time)

    path = input_dir / INPUT_FILE_NAME
    data = utils.read_json(path)

    cls_info = dict(context=context)
    root_loader = RootLoader(input_dir=input_dir, input_results_dir=input_results_dir)

    # This load_object() call returns a ModelRoot object, but we don't need
    # or use that object.  Instead, the context is the entry way we provide
    # for access to the election data from the top level.
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


def parse_int(obj, value):
    """
    Remove and parse an int string from the given data.
    """
    _log.debug(f'parsing int: {value}')
    if value is None or value == '':
        value = None
    else:
        try: value = int(value)
        except ValueError: RuntimeError(
                f'invalid int value for obj {obj!r}: {value}')
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
    Defines a key-value to read when loading JSON data, and how to load it.
    """

    # TODO: allow attr_name to be None to indicate that no attribute
    #  should be set.
    def __init__(self, attr_name, load_value, data_key=None, context_keys=None,
        unpack_context=False, required=False):
        """
        Args:
          attr_name: the name of the attribute to set.
          load_value: the function to call when loading.  The function
            should have the signature load_value(loader, data, ...),
            where loader is a Loader object.
          data_key: the name of the key to access from the JSON to obtain
            the data value to pass to load_value(), or False if no data
            is needed.  If None (the default), defaults to attr_name.
          context_keys: the name of the context keys that processing this
            attribute depends on.  Defaults to not depending on the context.
          unpack_context: whether to unpack the context argument into
            kwargs when calling the load_value() function.
          required: whether the data_key is required to be present in the
            JSON.
        """
        if data_key is None:
            data_key = attr_name
        if context_keys is None:
            context_keys = []

        self.attr_name = attr_name
        self.context_keys = set(context_keys)
        self.data_key = data_key
        self.load_value = load_value
        self.required = required
        self.unpack_context = unpack_context

    def __repr__(self):
        # Using __qualname__ instead of __name__ includes also the class
        # name and not just the function / method name.
        try:
            func_name = self.load_value.__qualname__
        except AttributeError:
            func_name = repr(self.load_value)

        return f'<AutoAttr {self.data_key!r}: attr_name={self.attr_name!r}, load_value={func_name}>'

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

    def process_key(self, loader, data, context):
        """
        Parse and process the value in the given data dict corresponding
        to the current AutoAttr instance.

        Args:
          loader: an instance of a Loader class.
          data: the dict of data containing the key-value to process.
          context: the current Jinja2 context.
        """
        key = self.data_key
        if key == False:
            # Then no value should be accessed.
            value = None
        elif key in data:
            value = data.pop(key)
        elif self.required:
            msg = f'key {key!r} missing from data; remaining keys: {sorted(data)}'
            raise RuntimeError(msg)
        else:
            # Then there is no value to process.
            return

        kwargs = self.make_load_value_kwargs(context)

        # TODO: can we eliminate needing to pass obj if load_value doesn't
        #  depend on it?
        value = self.load_value(loader, value, **kwargs)

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
    Read from JSON data a list of objects, and return an OrderedDict mapping
    id to object.

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


def process_auto_attr(loader, model_obj, attr, data, context):
    """
    Process an attribute in a Loader's auto_attrs list.

    Args:
      loader: an instance of a Loader class.
      model_obj: the data model object on which to set an attribute.
      attr: an element of loader.auto_attrs, which can be a tuple or
        AutoAttr object.
      data: the dict of data containing the key-values to process.
      context: the current Jinja2 context.
    """
    if type(attr) != AutoAttr:
        assert type(attr) == tuple
        attr = AutoAttr(*attr)

    _log.debug(f'processing auto_attr {attr!r} for: {model_obj!r}')
    try:
        value = attr.process_key(loader, data=data, context=context)
    except Exception:
        raise RuntimeError(f'while processing auto_attr {attr!r} for: {model_obj!r}')

    try:
        setattr(model_obj, attr.attr_name, value)
    except Exception:
        raise RuntimeError(f"couldn't set {attr_name!r} on {model_obj!r}")


# TODO: test this.
def format_abbreviated_dict(mapping):
    """
    Return a string formatting a dict for brief display.
    """
    items = []
    for key, value in mapping.items():
        if type(value) in (dict, list):
            value = type(value).__name__
        else:
            value = repr(value)

        # Truncate the value in case e.g. a string is really long.
        value = str(value)[:100]
        item = f'* {key}: {value}'
        items.append(item)

    return '\n'.join(items)


# TODO: make context required?
# TODO: rename cls_info to init_kwargs?
# TODO: expose "strict" via the command-line.
def load_object(loader, data, cls_info=None, context=None, strict=False):
    """
    Load and return an object in our data model.

    This function instantiates an instance of the data model class
    associated with the given loader (`loader.model_class`).  It then
    sets attributes on the instance using the loader's `auto_attrs` class
    attribute and the given deserialized json data.

    Args:
      loader: an instance of a Loader class.
      data: the dict of data containing the key-values to process.
      cls_info: a dict of keyword arguments to pass to the class constructor
        before processing attributes.
      context: the current Jinja2 context.
    """
    if type(loader) == type:
        msg = f'loader argument must be an instance of a Loader class: {loader}'
        raise TypeError(msg)

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
        model_obj = model_cls(**cls_info)
    except Exception:
        raise RuntimeError(f'error with model class {model_cls!r}: {cls_info!r}')

    assert not hasattr(loader, 'model_object')
    # Set the object being loaded on the loader.
    loader.model_object = model_obj

    # Make a (shallow) copy of the data because process_auto_attr() changes
    # it while processing.  We want a copy of the original in case an error
    # occurs.
    original_data = data.copy()

    try:
        # Set all of the (remaining) object attributes -- iterating over all
        # of the auto_attrs and parsing the corresponding JSON key values.
        for attr in auto_attrs:
            process_auto_attr(loader, model_obj, attr, data=data, context=context)
    except Exception:
        # Include data about the object that failed in the error message.
        formatted = format_abbreviated_dict(original_data)
        raise RuntimeError(f'json data has key values:\n{formatted}')

    # Check that all keys in the JSON have been processed.
    if data:
        msg = f'unrecognized keys for model object {model_obj!r}: {sorted(data.keys())}'
        if strict:
            raise RuntimeError(msg)
        else:
            _log.warning(msg)

    if hasattr(loader, 'finalize'):
        # Perform class-specific init after data is loaded
        model_obj.finalize()

    return model_obj


def get_contest_results_path(contest):
    """
    Return the path to the input file containing the detailed results for
    a contest.
    """
    election = contest.election
    input_results_dir = election.input_results_dir

    file_name = CONTEST_RESULTS_FILE_NAME_FORMAT.format(contest.id)
    path = input_results_dir / file_name

    return path


def parse_choices(choices_data, choices_by_id):
    """
    Parse a value in the winning_data dict.

    Returns a list of Choice objects.
    """
    id_names = tsvio.split_line(choices_data)
    choice_ids = [id_name.split(':', maxsplit=1)[0] for id_name in id_names]
    choices = [choices_by_id[choice_id] for choice_id in choice_ids]

    return choices


def process_winning_status(contest, winning_data):
    """
    Process the results.json 'choices' list of vote summary data
    in a contest or turnout.
    """
    for winning_status, choices_data in winning_data.items():
        if winning_status not in WINNING_STATUSES:
            raise RuntimeError(
                f'unrecognized winning_status value: {winning_status!r}\n'
                f' winning_data: {winning_data!r}'
            )
        is_successful = winning_status in ('winning',)
        choices = parse_choices(choices_data, choices_by_id=contest.choices_by_id)
        for choice in choices:
            choice.winning_status = winning_status

    winning_choices = [
        choice for choice in contest.iter_choices() if choice.winning_status == 'winning'
    ]

    return winning_choices


def row_to_ints(values):
    # Convert "" to None but "0" to 0.
    return [None if value == '' else int(value) for value in values]


# TODO: instead of passing `repeat_groups`, pass in a list of groups
#  that can be checked here instead of by the caller?
def _iter_rows(parsed_rows, expected_group_ids, repeat_groups=None, should_exhaust=True):
    """
    Yield, for each row, the converted `row[2:]`.

    Args:
      parsed_rows: an iterator of 3-tuples (line_number, group_id, totals),
        starting with the row after the header row.
      repeat_groups: the number of times to repeat each group before
        proceeding to the next group.  Defaults to 1.
    """
    if repeat_groups is None:
        repeat_groups = 1

    expected_group_ids = itertools.chain.from_iterable(
        itertools.repeat(group_id, times=repeat_groups) for group_id in expected_group_ids
    )

    for expected_group_id in expected_group_ids:
        result = next(parsed_rows)

        try:
            line_number, group_id, remaining = result
        except Exception:
            raise RuntimeError(f'error on: {result}')

        # Check that the reporting group portion matches what is expected.
        if group_id != expected_group_id:
            msg = (
                f'unexpected row header at line {line_number}:\n'
                f'  expected: {expected_group_id!r})\n'
                f'       got: {group_id}\n'
                f'    totals: {remaining}'
            )
            raise RuntimeError(msg)

        yield remaining

    if should_exhaust:
        # Then check that there are no more rows.
        try:
            line_number, group_id, remaining = next(parsed_rows)
        except StopIteration:
            pass
        else:
            msg = (
                f'found one or more extra rows starting at line {line_number}:\n'
                f'  group_id: {group_id}\n'
                f'    totals: {remaining}'
            )
            raise RuntimeError(msg)


def read_rcv_totals(parsed_rows, round_count):
    """
    Args:
      parsed_rows: an iterator of 3-tuples (line_number, group_id, totals),
        starting with the row after the header row.
      round_count: the number of RCV rounds.
    """
    if not round_count:
        return

    expected_group_ids = iter(
        # The rows start with the last round and end with round 1.
        (f'RCV{round}', VOTING_GROUP_ID_ALL) for round in range(round_count, 0, -1)
    )

    for totals in _iter_rows(parsed_rows, expected_group_ids=expected_group_ids,
            should_exhaust=False):
        # The empty string (converted to None) is used to signify that
        # the candidate has been eliminated.  Otherwise, the candidate is
        # still in the running and the value should be a numeric vote total.
        yield totals


def load_turnout_tsv(turnout, tsv_lines, summary=False):
    """
    Args:
      summary: a boolean of whether summary results are being loaded, as
        opposed to detailed results.  Defaults to False.

    Returns:
      turnout_results: a 3-D matrix (list of list of lists) indexed by:
        reporting group (area-voting_group pair) -> party -> result stat.
    """
    # This needs to be a list rather than an iterator because we need to
    # iterate over it more than once below.
    expected_group_ids = [
        g.group_id for g in turnout.iter_reporting_groups(summary_only=summary)
    ]

    headers, parsed_rows = tsv_lines.get_parsed_rows()

    party_ids = [party.id for party in turnout.parties]
    party_count = len(party_ids)

    # We need to pass an iterator separate from the one used below.
    row_data = _iter_rows(parsed_rows, expected_group_ids=expected_group_ids,
        repeat_groups=party_count)

    results = []
    for group_id in expected_group_ids:
        totals_by_party = []
        for expected_party_id in party_ids:
            try:
                party_id, totals = next(row_data)
            except StopIteration:
                msg = (
                    f'ran out of rows at line {tsv_lines.line_num!r}\n'
                    f'  expected_group_id: {group_id!r}'
                    f'  expected_party_id: {expected_party_id!r}'
                )
                raise RuntimeError(msg)

            if party_id != expected_party_id:
                msg = (
                    f'unexpected party id at line {tsv_lines.line_num!r}\n'
                    f'  expected_party_id: {expected_party_id}\n'
                    f'    actual_party_id: {party_id}'
                )
                raise RuntimeError(msg)

            totals_by_party.append(totals)

        results.append(totals_by_party)

    return results


def load_results_tsv(contest, tsv_lines, summary=False):
    """
    Args:
      tsv_lines: a TSVLines object.

    Returns: (rcv_totals, results)
      results: This is a matrix (list of lists), where the rows correspond
        to reporting groups (area-voting_group pair), and the columns
        correspond to result stats and choices.
      summary: a boolean of whether summary results are being loaded, as
        opposed to detailed results.  Defaults to False.
    """
    assert type(contest) == Contest

    # What reporting groups are expected, as an iterator of ReportingGroup objects.
    expected_groups = contest.iter_reporting_groups(summary_only=summary)

    headers, parsed_rows = tsv_lines.get_parsed_rows()

    numeric_column_count = contest.result_stat_count + contest.choice_count

    # Simple check, just validate the column count
    # We could validate the header if we like later
    if len(headers) != 2 + numeric_column_count:
        raise RuntimeError(
            f'Mismatched column heading in tsv data:\n'
            f'* columns={tsv_lines.num_columns!r} stats={contest.result_stat_count} choices={contest.choice_count}\n'
            f'* line={tsv_lines.line!r}\n'
            f'* contest.choices_by_id={dict(contest.choices_by_id)!r}'
        )

    if contest.is_rcv:
        # The RCV rounds are first, starting with the last round.
        rcv_totals = list(read_rcv_totals(parsed_rows, round_count=contest.rcv_rounds))
        # Call reversed() so the first round occurs first.
        rcv_totals = list(reversed(rcv_totals))
    else:
        rcv_totals = None

    expected_group_ids = iter(group.group_id for group in expected_groups)

    results = []
    for totals in _iter_rows(parsed_rows, expected_group_ids=expected_group_ids):
        results.append(totals)

    unused_groups = list(expected_groups)
    if unused_groups:
        # Truncate the list of leftover groups to prevent a super long message.
        remaining = ' '.join(repr(str(group)) for group in unused_groups[:10])
        raise RuntimeError(
            f'found {len(unused_groups)} unused reporting groups (after row {row_number!r}): '
            f'{remaining}...'
        )

    return (rcv_totals, results)


def load_reportable_common(reportable, data, convert):
    """
    Args:
      convert: a function to convert `row[2:]` for each row after
        the header row.
    """
    # TODO: should we add a ContestResults class to our data model?
    total_precincts = data.get('total_precincts')
    reportable.total_precincts = parse_int(reportable, total_precincts)

    precincts_reporting = data.get('precincts_reporting')
    reportable.precincts_reporting = parse_int(reportable, precincts_reporting)

    no_voter_precincts = data.get('no_voter_precincts')
    reportable.no_voter_precincts = parse_as_is(reportable, no_voter_precincts)

    summary_lines = iter(data['results_summary'])
    tsv_lines = TSVLines(summary_lines, convert=convert)

    return tsv_lines


def load_turnout_summary(turnout_loader, data):
    """
    Load the summary results (e.g. TSV lines in results.json) for turnout.
    """
    turnout = turnout_loader.model_object
    election = turnout.election

    def convert(remaining):
        return (remaining[0], row_to_ints(remaining[1:]))

    tsv_lines = load_reportable_common(turnout, data=data, convert=convert)

    eligible_voters = data.get('eligible_voters')
    turnout.eligible_voters = eligible_voters

    results = load_turnout_tsv(turnout, tsv_lines=tsv_lines, summary=True)

    return results


def load_contest_summary(contest_loader, data):
    """
    Load the summary results (e.g. TSV lines in results.json) for a contest.
    """
    contest = contest_loader.model_object
    election = contest.election

    tsv_lines = load_reportable_common(contest, data=data, convert=row_to_ints)

    # We need to get and set the number of rcv rounds before reading the
    # round data.
    rcv_rounds = data.get('rcv_rounds')
    if contest.is_rcv and rcv_rounds is None:
        raise RuntimeError(
            f'got is_rcv={contest.is_rcv!r} and rcv_rounds={rcv_rounds!r} for: {contest!r}'
        )

    if rcv_rounds is not None:
        rcv_rounds = parse_int(contest, rcv_rounds)
        contest.rcv_rounds = rcv_rounds

        # TODO: also process the "rcv_eliminations" key.

    rcv_totals, results = load_results_tsv(contest, tsv_lines=tsv_lines, summary=True)
    contest.rcv_totals = rcv_totals

    approval_met = data.get('approval_met')
    contest.approval_met = approval_met

    winning_data = data.get('winning_status')
    process_winning_status(contest, winning_data)

    return results


# TODO: don't initialize contest.results here.  Instead,
#  make this function return a detailed results object that can
#  be thrown away after use.
def load_contest_results(contest):
    """
    Load the detailed results for this contest with reporting groups with
    a breakdown by precinct/district.

    Args:
      contest: a Contest object.
    """
    path = get_contest_results_path(contest)

    _log.debug(f'load_results_details({path})')

    # TODO: don't initialize contest.results here.  Instead,
    #  make this function return a detailed results object that can
    #  be thrown away after use.
    contest.results = []
    contest.results_details_loaded = True

    with TSVReader(path, convert=row_to_ints) as tsv_lines:
        rcv_totals, results = load_results_tsv(contest, tsv_lines)

        contest.results = results


class VotingGroupLoader:

    model_class = datamodel.VotingGroup

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('text', parse_i18n),
    ]


class ResultStatTypeLoader:

    model_class = datamodel.ResultStatType

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('heading', parse_i18n),
        ('description', parse_i18n),
        # Save the dict to a private attribute so "text" can be a property.
        # TODO: make this public after heading is removed.
        ('_text', parse_i18n, 'text'),
        ('is_percent', parse_bool),
    ]


def text_ids_to_objects(text_ids, objects_by_id):
    """
    Convert a space-separated list of object ids into objects.

    Args:
      text_ids: a space-separated list of object ids, as a string.
      objects_by_id: the dict of all objects of a single type, mapping
        object id to object.

    Returns: (objects, indexes_by_id)
      objects: the objects as a list.
    """
    ids = datamodel.parse_text_ids(text_ids)
    objects = [objects_by_id[_id] for _id in ids]

    return objects


def make_index_map(values):
    """
    Return an `indexes_by_value` dict mapping the value to its (0-based)
    index in the list.
    """
    return {value: index for index, value in enumerate(values)}


def make_indexes_by_id(objects):
    """
    Return a dict mapping object id to its (0-based) index in the list.
    """
    return make_index_map(obj.id for obj in objects)


# We want a name other than load_result_stat_types() for uniqueness reasons.
def load_stat_types(result_style_loader, text_ids, result_stat_types_by_id):
    """
    Return the list of ResultStatType objects for a ResultStyle.

    Args:
      result_style_loader: a ResultStyleLoader object.
    """
    result_style = result_style_loader.model_object
    assert type(result_style) == ResultStyle

    stat_types = text_ids_to_objects(text_ids, result_stat_types_by_id)

    result_style.stat_id_to_index = make_indexes_by_id(stat_types)

    return stat_types


# We want a name other than load_voting_groups() for uniqueness reasons.
def load_result_voting_groups(result_style_loader, text_ids, voting_groups_by_id):
    """
    Args:
      result_style_loader: a ResultStyleLoader object.
    """
    result_style = result_style_loader.model_object
    assert type(result_style) == ResultStyle

    groups = text_ids_to_objects(text_ids, voting_groups_by_id)

    result_style.vg_id_to_index = make_indexes_by_id(groups)

    return groups


def load_turnout_parties(turnout_loader, party_ids, parties_by_id):
    turnout = turnout_loader.model_object
    assert type(turnout) is Turnout

    parties = text_ids_to_objects(party_ids, parties_by_id)

    turnout._party_id_to_index = make_indexes_by_id(parties)

    return parties


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


def load_reporting_groups(area_loader, vg_ids, voting_groups_by_id):
    """
    Args:
      data: a space-delimited string of voting group ids, e.g. "ED MV".
    """
    voting_groups = text_ids_to_objects(vg_ids, voting_groups_by_id)

    return voting_groups


def load_reporting_area_ids(area_loader, data, context=None):
    """
    Args:
      data: a space-delimited string of area ids, e.g. "ALL PCT1141 ...".
    """
    return datamodel.parse_text_ids(data)


class AreaLoader:

    model_class = datamodel.Area

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('id_ext', parse_id, '_id_ext'),
        ('classification', parse_as_is),
        ('name', parse_i18n),
        ('short_name', parse_i18n),
        ('is_vbm', parse_bool),
        ('has_no_voters', parse_bool),
        ('consolidated_ids', parse_as_is),
        AutoAttr('reporting_groups', load_reporting_groups,
            data_key='reporting_group_ids', context_keys=('voting_groups_by_id',),
            unpack_context=True),
        # Save the ids as private attributes so we can convert them to
        # objects in `load_areas()`.
        AutoAttr('_reporting_area_ids', load_reporting_area_ids,
            data_key='reporting_area_ids'),
    ]


def load_party(loader, party_id, parties_by_id):
    """
    Args:
      loader: the current active loader (e.g. a CandidateLoader or
        ContestLoader object).
    """
    return parties_by_id[party_id]


class PartyLoader:

    model_class = datamodel.Party

    auto_attrs = [
        ('id', parse_id, '_id'),
        # Save to a private attribute so we can use a property.
        ('_name', parse_i18n, 'name'),
        ('contest_party_crossover', parse_as_is),
        ('heading', parse_as_is)
    ]


class HeaderLoader:

    model_class = Header

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('id_ext', parse_id, '_id_ext'),
        ('ballot_title', parse_i18n),
        ('heading_text', parse_i18n),
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
        ('id_ext', parse_id, '_id_ext'),
        ('sequence', parse_int),
        ('ballot_title', parse_i18n),
    ]


# Candidate loading

class CandidateLoader:

    model_class = Candidate

    auto_attrs = [
        ('id', parse_id, '_id'),
        ('id_ext', parse_id, '_id_ext'),
        ('sequence', parse_int),
        ('ballot_title', parse_i18n),
        ('ballot_designation', parse_i18n),
        ('ballot_party_label', parse_i18n),
        # Pass `unpack_context=True` since `load_party()` accepts a
        # `parties_by_id` argument and not a full `context` argument.
        AutoAttr('candidate_party', load_party, data_key='candidate_party_id',
            context_keys=('parties_by_id',), unpack_context=True),
        ('is_writein', parse_bool),
    ]


# Contest loading

# Dict mapping contest data "_type" name to choice loader class.
CONTEST_TO_CHOICE_LOADER = {
    'office': CandidateLoader,
    'measure': ChoiceLoader,
    'retention': ChoiceLoader,
    'ynoffice': ChoiceLoader,
}

def load_single_choice(data, choice_loader_cls, cls_info, context=None):
    """
    Common processing to enter a candidate or measure choice

    Args:
      choice_loader_cls: the loader class to use to load the contest's
        choices (can be ChoiceLoader or CandidateLoader).
      cls_info: the dict of kwargs to pass to the Choice constructor.
    """
    choice_loader = choice_loader_cls()
    choice = load_object(choice_loader, data, cls_info=cls_info, context=context)

    return choice


def load_choices(contest_loader, choices_data, context=None):
    """
    Scan an input data list of contest choice entries to create.

    Args:
      contest_loader: a ContestLoader object.

    Returns:
      choices_by_id: a dict mapping id to Choice object.
    """
    # First determine the loader class to use to load the contest's
    # choices (can be ChoiceLoader or CandidateLoader).
    contest = contest_loader.model_object
    assert type(contest) == Contest
    type_name = contest.type_name

    try:
        choice_loader_cls = CONTEST_TO_CHOICE_LOADER[type_name]
    except KeyError:
        raise RuntimeError(f'invalid contest type name: {type_name!r}')

    cls_info = dict(contest=contest)
    load_data = functools.partial(load_single_choice, choice_loader_cls=choice_loader_cls,
        cls_info=cls_info, context=context)
    choices_by_id = load_objects_to_mapping(load_data, choices_data, should_index=True)

    return choices_by_id


def load_approval_choice(contest_loader, approval_choice_id):
    """
    Return the approval choice, as a Choice object.
    """
    contest = contest_loader.model_object
    assert type(contest) == Contest

    approval_choice = contest.choices_by_id[approval_choice_id]

    return approval_choice


def load_result_style(contest_loader, value, result_styles_by_id):
    return result_styles_by_id[value]


def load_results_mapping(contest_loader, data):
    contest = contest_loader.model_object
    assert type(contest) is Contest

    choices = list(contest.iter_choices())

    return ResultsMapping(result_style=contest.result_style, choices=choices)


def load_voting_district(contest_loader, value, areas_by_id):
    return areas_by_id[value]


def make_contest_results_loader(contest_loader, data):
    """
    Return the function to set as contest._load_contest_results_data.
    """
    return load_contest_results


def load_turnout_choices(contest_loader, value, parties_by_id):
    return parties_by_id


class TurnoutLoader:

    model_class = Turnout

    # TODO: finish ordering these into two groups, with the first being
    #  for ReportableMixin.
    auto_attrs = [
        ('id', parse_id, '_id'),
        ('ballot_title', parse_i18n),
        AutoAttr('parties', load_turnout_parties, data_key='turnout_party_ids',
            context_keys=('parties_by_id',), unpack_context=True),
        AutoAttr('result_style', load_result_style,
            context_keys=('result_styles_by_id',), unpack_context=True, required=True),
        AutoAttr('voting_district', load_voting_district,
            context_keys=('areas_by_id',), unpack_context=True, required=True),
        ('type', parse_as_is),
        AutoAttr('_results_summary', load_turnout_summary, data_key='results'),
    ]


def load_turnout_object(election_loader, turnout_data, context):
    """
    Process the source data for the election turnout item.

    Returns the turnout object.

    Args:
      election_loader: an ElectionLoader object.
      turnout_data: the turnout element of the election.
    """
    areas_by_id = context['areas_by_id']
    voting_groups_by_id = context['voting_groups_by_id']

    result_stat_types_by_id = context['result_stat_types_by_id']
    eligible_voters_stat = result_stat_types_by_id['RSEli']

    cls_info = dict(election=election_loader.model_object,
        areas_by_id=areas_by_id, voting_groups_by_id=voting_groups_by_id,
        eligible_voters_stat=eligible_voters_stat)

    return load_object(TurnoutLoader(), turnout_data, cls_info=cls_info, context=context)


class ContestLoader:

    model_class = Contest

    # TODO: finish ordering these into two groups, with the first being
    #  for ReportableMixin.
    auto_attrs = [
        ('id', parse_id, '_id'),
        ('id_ext', parse_id, '_id_ext'),
        ('approval_threshold', parse_as_is),
        ('ballot_subtitle', parse_i18n),
        ('ballot_title', parse_i18n),
        # Don't pass `unpack_context=True` since `load_choices()` accepts
        # a `context` argument (not the unpacked keys).
        AutoAttr('choices_by_id', load_choices, data_key='choices',
            context_keys=('parties_by_id',)),
        ('approval_choice', load_approval_choice, 'approval_choice_id'),
        AutoAttr('contest_party', load_party, data_key='contest_party_id',
          context_keys=('parties_by_id',), unpack_context=True),
        # This is needed only while loading.
        # TODO: can we eliminate having to store this as an attribute?
        AutoAttr('_header_id', parse_as_is, data_key='header_id'),
        ('instructions_text', parse_as_is),
        ('is_partisan', parse_as_is),
        ('name', parse_i18n),
        ('short_description', parse_i18n),
        ('votes_allowed', parse_as_is),
        ('number_elected', parse_as_is),
        ('contest_party_crossover', parse_as_is),
        ('question_text', parse_i18n),
        AutoAttr('result_style', load_result_style,
            context_keys=('result_styles_by_id',), unpack_context=True, required=True),
        AutoAttr('results_mapping', load_results_mapping, data_key=False),
        AutoAttr('voting_district', load_voting_district,
            context_keys=('areas_by_id',), unpack_context=True, required=True),
        ('runoff_date', parse_date),
        ('runoff_type', parse_as_is),
        ('success', parse_as_is),
        ('type', parse_as_is),
        ('url_state_results', parse_as_is),
        ('vote_for_msg', parse_as_is),
        ('writeins_allowed', parse_int),

        # Handle results-related attributes.
        AutoAttr('_results_summary', load_contest_summary, data_key='results'),

        # Pass data_key=False since this does not read from the json data.
        AutoAttr('_load_contest_results_data', make_contest_results_loader, data_key=False),
    ]

def load_single_contest(data, election, context):
    """
    Create and return a Header object from data.
    """
    try:
        type_name = data.pop('_type')
    except KeyError:
        raise RuntimeError(f"key '_type' missing from data: {data}")

    areas_by_id = context['areas_by_id']
    voting_groups_by_id = context['voting_groups_by_id']

    cls_info = dict(type_name=type_name, election=election,
        areas_by_id=areas_by_id, voting_groups_by_id=voting_groups_by_id)

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


def load_headers(election_loader, headers_data):
    """
    Process the source data representing the header items.

    Returns an OrderedDict mapping header id to Header object.

    Args:
      election_loader: an ElectionLoader object.
      headers_data: a list of dicts corresponding to the Header objects.
    """
    def load_data(data):
        return load_object(HeaderLoader(), data)

    headers_by_id = load_objects_to_mapping(load_data, headers_data, should_index=True)

    for header in headers_by_id.values():
        link_with_header(header, headers_by_id=headers_by_id)

    return headers_by_id


def load_contests(election_loader, contests_data, context):
    """
    Process the source data representing the contest items.

    Returns an OrderedDict mapping contest id to Contest object.

    Args:
      election_loader: an ElectionLoader object.
      contests_data: a list of dicts corresponding to the Contest objects.
    """
    election = election_loader.model_object
    assert type(election) == Election

    load_data = functools.partial(load_single_contest, election=election, context=context)
    # This is an OrderedDict mapping contest_id to Contest.
    contests_by_id = load_objects_to_mapping(load_data, contests_data, should_index=True)

    for contest in contests_by_id.values():
        link_with_header(contest, headers_by_id=election.headers_by_id)

    return contests_by_id


class ElectionLoader:

    model_class = Election

    auto_attrs = [
        ('ballot_title', parse_i18n),
        ('date', parse_date, 'election_date'),
        ('election_area', parse_i18n),
        ('url_state_results', parse_as_is),
        ('no_voter_precincts', parse_as_is),
        # Process headers before contests since the contest data references
        # the headers but not vice versa.
        ('headers_by_id', load_headers, 'headers'),
        AutoAttr('contests_by_id', load_contests, data_key='contests',
            context_keys=('areas_by_id', 'parties_by_id', 'result_styles_by_id', 'voting_groups_by_id')),
        AutoAttr('turnout', load_turnout_object, data_key='turnout',
            context_keys=('areas_by_id', 'parties_by_id', 'result_stat_types_by_id',
                'result_styles_by_id', 'voting_groups_by_id')),

        # Results attributes
        AutoAttr('results_id', parse_as_is, data_key='_results_id'),
        AutoAttr('results_title', parse_i18n, data_key='_results_title'),
        AutoAttr('reporting_time', parse_date_time, data_key='_reporting_time'),
    ]


# Root context loading

class ModelRoot:

    """
    A helper class for loading of all of the input data and populating
    the Jinja2 context.

    Instance attributes:

      context:
    """

    def __init__(self, context):
        """
        Args:
          context: the current Jinja2 context.
        """
        name_values = [
            ('context', context),
        ]
        for name, value in name_values:
            # Call super() to bypass our override.
            super().__setattr__(name, value)

    # Override __setattr__ to cause load_object() to add attr values to
    # the Jinja2 context rather than storing them to instance attributes.
    def __setattr__(self, name, value):
        self.context[name] = value


def load_result_stat_types(root_loader, types_data):
    """
    Args:
      root_loader: a RootLoader object.
    """
    def load_data(data):
        return load_object(ResultStatTypeLoader(), data)

    return load_objects_to_mapping(load_data, types_data)


def load_voting_groups(root_loader, groups_data):
    """
    Create and return an OrderedDict mapping VotingGroup id to VotingGroup object.

    Args:
      root_loader: a RootLoader object.
    """
    def load_data(data):
        return load_object(VotingGroupLoader(), data)

    voting_groups_by_id = load_objects_to_mapping(load_data, groups_data)

    return voting_groups_by_id


def load_all_result_styles(root_loader, styles_data, context):
    """
    Create and return an OrderedDict mapping ResultStyle id to ResultStyle object.

    Args:
      root_loader: a RootLoader object.
    """
    def load_data(data):
        return load_object(ResultStyleLoader(), data, context=context)

    result_styles_by_id = load_objects_to_mapping(load_data, styles_data)

    return result_styles_by_id


def load_areas(root_loader, areas_data, context):
    """
    Process source data representing an area (e.g. precinct or district).
    """
    # Get the default voting group.
    voting_groups_by_id = context['voting_groups_by_id']
    total_voting_group = voting_groups_by_id[VOTING_GROUP_ID_ALL]

    def load_data(data):
        return load_object(AreaLoader(), data, context=context)

    areas_by_id = load_objects_to_mapping(load_data, areas_data)

    # Now that we have all the areas by id, we can convert the
    # reporting_area_ids to Area objects.
    areas = iter(areas_by_id.values())
    # Skip the ALL area because we can't set reporting_areas on it.
    area = next(areas)
    assert area.is_all

    for area in areas:
        # TODO: remove area.reporting_groups?
        if not area.reporting_groups:
            # Set the voting groups default ("TO").
            area.reporting_groups = [total_voting_group]

        area_ids = area._reporting_area_ids
        if not area_ids:
            continue

        reporting_areas = [areas_by_id[area_id] for area_id in area_ids]
        area.reporting_areas = reporting_areas

    return areas_by_id


def load_parties(root_loader, party_data):
    def load_data(data):
      return load_object(PartyLoader(), data)

    return load_objects_to_mapping(load_data, party_data)


def load_summary_data(election_data, input_results_dir):
    """
    Load the summary results (`results.json` data) into the election_data dict.

    Returns whether results files are available.

    Args:
      election_data: the election_data argument passed to `load_election()`.
      input_results_dir: the directory containing the detailed results
        data files, as a Path object.
    """
    results_path = input_results_dir / RESULTS_FILE_NAME
    results_available = results_path.exists()

    if not results_available:
        return False

    results_data = utils.read_json(results_path)

    # TODO: make the rest of this function into a separate function?

    # Temporarily store the contest results data by contest id.
    contests_results = results_data.pop('contests')
    contest_results_by_id = {}
    for contest_results in contests_results:
        contest_id = contest_results['_id']
        contest_results_by_id[contest_id] = contest_results

    # Write the contest results data for each contest into the general
    # contest data.
    contests_data = election_data['contests']
    for contest_data in contests_data:
        contest_id = contest_data['_id']
        contest_results = contest_results_by_id[contest_id]
        contest_data['results'] = contest_results

    turnout_results = results_data.pop('turnout')
    turnout_data = election_data['turnout']
    turnout_data['results'] = turnout_results

    # Store the top-level results attributes under `election_data['results']`.
    for key in ['_reporting_time', '_results_format', '_results_id', '_results_title']:
        assert key not in election_data

    election_data.update(results_data)

    return True


def load_election(root_loader, election_data, context):
    """
    Args:
      root_loader: a RootLoader object.
    """
    input_results_dir = root_loader.input_results_dir

    results_available = load_summary_data(election_data, input_results_dir=input_results_dir)

    cls_info = dict(input_dir=root_loader.input_dir, input_results_dir=input_results_dir)
    election_loader = ElectionLoader()
    election = load_object(election_loader, election_data, cls_info=cls_info, context=context)
    election._results_available = results_available

    return election


class RootLoader:

    model_class = ModelRoot

    auto_attrs = [
        ('languages', parse_as_is),
        ('translations', parse_as_is),
        # Set "result_stat_types_by_id" and "voting_groups_by_id" now since
        # processing "election" depends on them.
        ('result_stat_types_by_id', load_result_stat_types, 'result_stat_types'),
        ('voting_groups_by_id', load_voting_groups, 'voting_groups'),
        AutoAttr('areas_by_id', load_areas, 'areas',
            context_keys=('voting_groups_by_id',)),
        # Processing result_styles requires result_stat_types and voting_groups.
        AutoAttr('result_styles_by_id', load_all_result_styles, data_key='result_styles',
            context_keys=('result_stat_types_by_id', 'voting_groups_by_id')),
        ('parties_by_id', load_parties, 'party_names'),
        # The `result_stat_types_by_id` contest key is needed for turnout.
        AutoAttr('election', load_election,
            context_keys=('areas_by_id', 'parties_by_id', 'result_stat_types_by_id',
                'result_styles_by_id', 'voting_groups_by_id')),
    ]

    def __init__(self, input_dir, input_results_dir):
        """
        Args:
          input_dir: the directory containing the election.json file, as a
            Path object.
          input_results_dir: the directory containing the detailed results
            data files, as a Path object.
        """
        self.input_dir = input_dir
        self.input_results_dir = input_results_dir
