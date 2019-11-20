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

from collections import namedtuple
from datetime import datetime
import json
import logging
from pathlib import Path
from textwrap import dedent

from orr.dataloading import DEFAULT_RESULTS_DIR_NAME, INPUT_FILE_NAME
import orr.utils as utils
from orr.utils import DEFAULT_JSON_DUMPS_ARGS


DEFAULT_TEMPLATE_DIR = 'templates'

DEFAULT_OUTPUT_PARENT_DIR = '_build'

# Attributes:
#   results_dir: an optional directory corresponding to the
#     --input-results-dir value passed.
InputDirs = namedtuple('InputDirs', 'data_dir, results_dir, template_dir, extra_template_dirs')

OrrOptions = namedtuple('OrrOptions',
    'input_dirs,output_dir,build_time,log_level,deterministic,skip_pdf',
)


def generate_output_name(dt):
    """
    Return a name of the form "build_20180511_224339".

    Args:
      dt: a datetime object.
    """
    name = 'build_{:%Y%m%d_%H%M%S}'.format(dt)

    return name


def add_common_args(parser):
    """
    Add the command options shared by both "orr" and "orr-docker".
    """
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='enable verbose info printout')
    parser.add_argument('--debug', action='store_true', help='enable debug printout')

    input_help = dedent(f"""\
    path to the directory containing the input data files (e.g. the
    {INPUT_FILE_NAME} file).
    """)
    parser.add_argument('--input-dir', metavar='PATH', help=input_help)
    results_dir_help = dedent(f"""\
    optional path to a directory with the detailed results files.
    Defaults to the "{DEFAULT_RESULTS_DIR_NAME}" subdirectory of the input
    directory.
    """)
    parser.add_argument('--input-results-dir', metavar='PATH', help=results_dir_help)

    parser.add_argument('--template-dir', metavar='DIR', default=DEFAULT_TEMPLATE_DIR,
                        help=('directory containing the template files to render. '
                              f'Defaults to: {DEFAULT_TEMPLATE_DIR}.'))
    parser.add_argument('--extra-template-dirs', metavar='DIR', nargs='+',
                        help=('extra directories to search when looking for '
                              'templates, and not rendered otherwise.'))

    parser.add_argument('--output-parent', metavar='DIR',
                        help=('the directory in which to write the output directory. '
                              f'Defaults to: {DEFAULT_OUTPUT_PARENT_DIR}.'))
    parser.add_argument('--output-subdir', metavar='NAME',
                        help=('the name to give the output directory inside '
                              'the parent output directory. '
                              'Defaults to a name generated using the current datetime.'))
    parser.add_argument('--build-time', metavar='DATETIME',
                        help=('the datetime to use as the build time, '
                              'in the format "2018-06-01 20:48:12". '
                              'Defaults to the current datetime.'))
    parser.add_argument('--deterministic', action='store_true',
                        help='make PDF generation deterministic.')
    parser.add_argument('--skip-pdf', action='store_true',
                        help='skip PDF generation (useful for testing).')


def parse_common_args(ns, default_log_level=None):
    """
    Return an OrrOptions object.
    """
    if default_log_level is None:
        default_log_level = logging.ERROR

    build_time = ns.build_time
    input_data_dir = ns.input_dir
    input_results_dir = ns.input_results_dir
    output_parent = ns.output_parent
    output_subdir = ns.output_subdir
    template_dir = ns.template_dir
    extra_template_dirs = ns.extra_template_dirs
    deterministic = ns.deterministic
    skip_pdf = ns.skip_pdf

    if ns.debug:
        level = logging.DEBUG
    elif ns.verbose:
        level = logging.INFO
    else:
        level = default_log_level

    if build_time is None:
        build_time = datetime.now()
    else:
        build_time = utils.parse_datetime(build_time)

    if not input_data_dir:
        raise RuntimeError('--input-dir not provided')

    input_data_dir = Path(input_data_dir)
    if input_results_dir is not None:
        input_results_dir = Path(input_results_dir)

    if output_parent is None:
        output_parent = DEFAULT_OUTPUT_PARENT_DIR

    if output_subdir is None:
        output_subdir = generate_output_name(build_time)

    output_parent = Path(output_parent)
    output_dir = output_parent / output_subdir

    if extra_template_dirs is None:
        extra_template_dirs = []

    extra_template_dirs = [Path(path) for path in extra_template_dirs]

    input_dirs = InputDirs(data_dir=input_data_dir, results_dir=input_results_dir,
                           template_dir=template_dir,
                           extra_template_dirs=extra_template_dirs)

    options = OrrOptions(
        input_dirs, output_dir=output_dir, build_time=build_time,
        log_level=level, deterministic=deterministic, skip_pdf=skip_pdf,
    )

    return options


def format_output(output_dir, build_time, report_title=None, rel_home_page=None,
    zip_file_path=None, initial_data=None,
):
    """
    Print and return the output data.
    """
    if initial_data is None:
        initial_data = {}

    output_dir = Path(output_dir)
    # Rename the variable for clarity.
    output_data = initial_data

    if report_title is not None:
        output_data['report_title'] = report_title

    if rel_home_page is not None:
        output_data['rel_home_page'] = rel_home_page

    if zip_file_path is not None:
        path = output_dir / zip_file_path
        zip_size = path.stat().st_size
        zip_hash = utils.hash_file(path)

        output_data['zip_file'] = {
            'path': str(zip_file_path),
            'bytes': zip_size,
            'hash': str(zip_hash),
        }

    output_data.update(
        build_time=build_time.isoformat(),
        output_dir=str(output_dir),
    )

    # TODO: allow changing the stdout output format (e.g. YAML or text)?
    output = json.dumps(output_data, **DEFAULT_JSON_DUMPS_ARGS)

    return (output_data, output)
