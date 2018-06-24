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

import functools

import orr.datamodel as datamodel
# TODO: move all but the model classes themselves into this module.
from orr.datamodel import (load_object, load_objects_to_mapping,
    parse_as_is, parse_date, parse_i18n, Area, AutoAttr, Contest,
    Header, ResultStatType, ResultStyle, VotingGroup)


def link_with_header(item, headers_by_id):
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


def load_headers(obj, headers_data):
    """
    Process the source data representing the header items.

    Returns an OrderedDict mapping header id to Header object.

    Args:
      headers_data: a list of dicts corresponding to the Header objects.
    """
    load_data = functools.partial(load_object, Header)
    headers_by_id = load_objects_to_mapping(load_data, headers_data, should_index=True)

    for header in headers_by_id.values():
        link_with_header(header, headers_by_id)

    return headers_by_id


def load_contests(election, contests_data, context):
    """
    Process the source data representing the contest items.

    Returns an OrderedDict mapping contest id to Contest object.

    Args:
      contests_data: a list of dicts corresponding to the Contest objects.
    """
    load_data = functools.partial(Contest.from_data, election=election, context=context)
    contests_by_id = load_objects_to_mapping(load_data, contests_data, should_index=True)

    for contest in contests_by_id.values():
        link_with_header(contest, election.headers_by_id)

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
    load_data = functools.partial(load_object, Area)
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
