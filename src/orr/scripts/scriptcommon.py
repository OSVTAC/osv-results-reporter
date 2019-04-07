# -*- coding: utf-8 -*-
#
# Open Source Voting Results Reporter (ORR) - election results report generator
# Copyright (C) 2019  Chris Jerdonek
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
Script-related functions shared by both orr and orr-docker.
"""

from datetime import datetime
import json
import logging
from pathlib import Path

import orr.utils as utils
from orr.utils import DEFAULT_JSON_DUMPS_ARGS


DEFAULT_OUTPUT_PARENT_DIR = '_build'


def generate_output_name(dt):
    """
    Return a name of the form "build_20180511_224339".

    Args:
      dt: a datetime object.
    """
    name = 'build_{:%Y%m%d_%H%M%S}'.format(dt)

    return name


def add_common_args(parser):
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='enable verbose info printout')
    parser.add_argument('--debug', action='store_true', help='enable debug printout')
    parser.add_argument('--output-parent', metavar='DIR',
                        help=('the directory in which to write the output directory. '
                              f'Defaults to: {DEFAULT_OUTPUT_PARENT_DIR}.'))
    parser.add_argument('--output-dir-name', metavar='NAME',
                        help=('the name to give the output directory inside '
                              'the parent output directory. '
                              'Defaults to a name generated using the current datetime.'))
    parser.add_argument('--build-time', metavar='DATETIME',
                        help=('the datetime to use as the build time, '
                              'in the format "2018-06-01 20:48:12". '
                              'Defaults to the current datetime.'))


def parse_common_args(ns):
    """
    Return: (output_dir, build_time)
    """
    build_time = ns.build_time
    output_parent = ns.output_parent
    output_dir_name = ns.output_dir_name

    if ns.debug:
        level = logging.DEBUG
    elif ns.verbose:
        level = logging.INFO
    else:
        level = logging.ERROR

    if build_time is None:
        build_time = datetime.now()
    else:
        build_time = utils.parse_datetime(build_time)

    if output_parent is None:
        output_parent = DEFAULT_OUTPUT_PARENT_DIR

    if output_dir_name is None:
        output_dir_name = generate_output_name(build_time)

    output_parent = Path(output_parent)
    output_dir = output_parent / output_dir_name

    return (output_dir, build_time, level)


def print_result(output_dir, build_time):
    """
    Print and return the output data.
    """
    output_data = dict(
        build_time=build_time.isoformat(),
        output_dir=str(output_dir),
    )

    # TODO: allow changing the stdout output format (e.g. YAML or text)?
    output = json.dumps(output_data, **DEFAULT_JSON_DUMPS_ARGS)

    # TODO: allow suppressing stdout?
    print(output)

    return output_data
