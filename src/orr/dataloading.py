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
"""

from collections import OrderedDict
import functools

import orr.datamodel as datamodel
# TODO: move all but the model classes themselves into this module.
from orr.datamodel import (load_object,
    parse_as_is, parse_bool, parse_date, parse_i18n, parse_id, parse_int,
    AutoAttr, Candidate, Choice, Contest, Header, ResultStatType,
    ResultStyle, VotingGroup)


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
    choice = load_object(choice_cls, data)
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

    contest = load_object(ContestLoader, data, cls_info=cls_info, context=context)

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


# ModelRoot loading

def load_result_stat_types(root, types_data):
    """
    Args:
      root: a ModelRoot object.
    """
    load_data = functools.partial(load_object, ResultStatType)
    return load_objects_to_mapping(load_data, types_data)


def load_voting_groups(root, groups_data):
    """
    Args:
      root: a ModelRoot object.
    """
    load_data = functools.partial(load_object, VotingGroup)
    return load_objects_to_mapping(load_data, groups_data)


def load_result_styles(root, styles_data, context):
    """
    Args:
      root: a ModelRoot object.
    """
    load_data = functools.partial(load_object, ResultStyle, context=context)
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
    return load_object(ElectionLoader, election_data, cls_info=cls_info, context=context)


class RootLoader:

    model_class = datamodel.ModelRoot

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
