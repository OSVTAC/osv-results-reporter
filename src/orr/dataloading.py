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
from orr.datamodel import (load_object, load_objects_to_mapping, parse_date,
    parse_i18n, AutoAttr, Contest, Header)


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
