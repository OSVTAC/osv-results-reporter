#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Open Source Voting Results Reporter (ORR) - election results report generator
# Copyright (C) 2018  Carl Hage
# Copyright (C) 2018, 2019  Chris Jerdonek
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
Program to create HTML/PDF/XLS files from election results data.
Documentation: [TODO]
"""

import argparse
from datetime import datetime
import logging
import os
from pathlib import Path
from pprint import pprint
import shutil
import sys
from textwrap import dedent

import orr.configlib as configlib
import orr.dataloading as dataloading
from orr.dataloading import DEFAULT_RESULTS_DIR_NAME
import orr.scripts.scriptcommon as scriptcommon
import orr.templating as templating
import orr.utils as utils
from orr.utils import SHA256SUMS_FILENAME, US_LOCALE


_log = logging.getLogger(__name__)

VERSION='0.0.1'     # Program version

ENCODING='utf-8'

STATIC_FILES_DIR = '_static'

#--- Command line arguments: ---

# See the definitions below for list of options

DESCRIPTION = """\
Generate HTML/PDF/XLS files from election results data.

The path to the output directory is written to stdout at the end
of the script.
"""

def parse_args():
    """
    Parse sys.argv and return a Namespace object.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                    formatter_class=argparse.RawDescriptionHelpFormatter)

    scriptcommon.add_common_args(parser)
    parser.add_argument('--version', action='version', version='%(prog)s '+VERSION)
    parser.add_argument('-t', dest='test', action='store_true',
                        help='test mode, print files to expand')
    parser.add_argument('--config-path', '-c', dest='config_path', metavar='PATH',
                        help='path to the configuration file to use')
    parser.add_argument('--output-fresh-parent', action='store_true',
                        help=('require that the output parent not already exist. '
                              'This is for running inside a Docker container.'))

    ns = parser.parse_args()

    return ns


#--- Data environment: ---

# The following routines help set/update the global environment data settings

#--- Data loaders: ---

# Data loaders retrieve a particular category of data content and
# merge into the `data` dict, if that category is not already present.
# Data loaders can be added across modules, and the docstring should
# begin with "Data Loader:" to identify documentation to be automatically
# included in the template file documentation.
# [TODO: Allow data loaders to be invoked in templates as function call]


def load_input(data, path):
    """
    Data Loader: The data loader will read arbitrary
    json or yaml formatted data from the named file
    and update/replace data to be processed with templates.
    The parsed content must be a dictionary (set of named values).
    """
    path = Path(path)
    suffix = path.suffix
    if suffix == '.json':
        newdata = utils.read_json(path)
    else:
        raise RuntimeError(f'unsupported suffix {suffix!r} for input path: {path}')

    if not isinstance(newdata, dict):
        _log.error(f'Invalid data in file {path}');
        return
    data.update(newdata)
    _log.info(f'loaded data from {path}')


#--- Top level processing: ---

def initialize_output_dir(template_dir, output_dir):
    """
    Create the output directory, copying static files if necessary.

    Args:
      template_dir: a Path object.
      output_dir: a Path object.
    """
    static_files_dir = template_dir / STATIC_FILES_DIR
    if not static_files_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        return

    if output_dir.exists():
        # TODO: add a command-line option to bypass this prompt.
        response = input(
            'Output directory already exists:\n'
            f'--> {output_dir.resolve()}\n'
            'Okay to delete (yes/no)?\n'
        )
        if response != 'yes':
            raise SystemExit('Not okay to delete: aborting.')
        shutil.rmtree(output_dir)

    shutil.copytree(static_files_dir, output_dir)


# TODO: render the directory recursively.
# TODO: put the templates in a "templates" subdirectory.
def render_template_dir(template_dir, output_dir, env, context=None, test_mode=False):
    """
    Render the templates inside the given template directory.

    Args:
      template_dir: a Path object.
      output_dir: a Path object.
      env: a Jinja2 Environment object.
      context: optional context data.
      test_mode: a boolean.
    """
    # Process templates
    for template_path in template_dir.iterdir():
        if template_path.is_dir():
            # TODO: process directories recursively, but remembering to
            #  skip directories like the "extra" directory.
            continue

        file_name = template_path.name
        utils.process_template(env, template_name=file_name, context=context,
            test_mode=test_mode)


def make_sha256sums_file(dir_path):
    shasums_file = SHA256SUMS_FILENAME
    # Don't include SHA256SUMS because its hash will necessarily be incorrect
    # after SHA256SUMS is updated.
    exclude_paths = [shasums_file]

    contents = utils.directory_sha256sum(dir_path, exclude_paths=exclude_paths)
    sha256sums_path = dir_path / shasums_file
    sha256sums_path.write_text(contents)


def run(config_path=None, input_dir=None, input_results_dir=None, template_dir=None,
    extra_template_dirs=None, output_dir=None, fresh_output=False,
    test_mode=False, build_time=None, deterministic=None, skip_pdf=False):
    """
    Args:
      config_path: optional path to the config file, as a string.
      input_dir: required path to the input directory, as a string.
      input_results_dir: optional path to the input results data directory,
        as a string.  Defaults to a directory inside the input directory.
      template_dir: a directory containing the templates to render.
      extra_template_dirs: optional extra directories to search for
        templates (e.g. for the subtemplate tag).  This should be a list
        of path-like objects.
      output_dir: the output directory, as a Path object.
      build_time: the current time, as a naive datetime object in the local
        timezone. This is exposed for testing and reproducibility purposes.
        Defaults to `datetime.now()`.
      deterministic: for deterministic PDF generation.  Defaults to False.
      skip_pdf: whether to skip PDF generation.  Defaults to False.
    """
    if build_time is None:
        build_time = datetime.now()
    if extra_template_dirs is None:
        extra_template_dirs = []

    assert output_dir is not None
    assert template_dir is not None

    output_parent = output_dir.parent

    if fresh_output and output_parent.exists():
        msg = f'--output-fresh-parent: output parent directory already exists: {output_parent}'
        raise RuntimeError(msg)

    _log.debug(f'using output directory: {output_dir}')

    # Create the jinja environment
    # Convert the path to an absolute paths to simplify troubleshooting.
    template_dir = Path(template_dir)
    _log.debug(f'using template directory: {template_dir}')

    template_dirs = [template_dir] + extra_template_dirs
    env = configlib.create_jinja_env(output_dir=output_dir, template_dirs=template_dirs,
                deterministic=deterministic, skip_pdf=skip_pdf)

    if input_dir is None:
        raise RuntimeError('--input-dir not provided')

    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise RuntimeError(f'--input-dir is not a directory: {input_dir}')

    if input_results_dir is None:
        input_results_dir = input_dir / DEFAULT_RESULTS_DIR_NAME
    input_results_dir = Path(input_results_dir)

    if not input_results_dir.is_dir():
        raise RuntimeError(f'--input-results-dir is not a directory: {input_results_dir}')

    context = dataloading.load_context(input_dir, input_results_dir=input_results_dir,
                                build_time=build_time)

    initialize_output_dir(template_dir, output_dir=output_dir)

    # TODO: allow different locales to be used (e.g. the system's default
    #  locale and/or a locale passed in via the command-line)?
    with utils.changing_locale(US_LOCALE):
        render_template_dir(template_dir, output_dir=output_dir, env=env,
            context=context, test_mode=test_mode)

    make_sha256sums_file(output_dir)

    output_data = scriptcommon.print_result(output_dir, build_time=build_time)

    return output_data


def main():
    ns = parse_args()

    options = scriptcommon.parse_common_args(ns)

    build_time = options.build_time
    log_level = options.log_level
    input_dirs = options.input_dirs
    output_dir = options.output_dir
    deterministic = options.deterministic
    skip_pdf = options.skip_pdf

    logging.basicConfig(level=log_level)

    config_path = ns.config_path

    fresh_output = ns.output_fresh_parent

    test_mode = ns.test

    input_data_dir = input_dirs.data_dir
    input_results_dir = input_dirs.results_dir

    template_dir = input_dirs.template_dir
    extra_template_dirs = input_dirs.extra_template_dirs

    run(config_path=config_path, input_dir=input_data_dir, input_results_dir=input_results_dir,
        template_dir=template_dir, extra_template_dirs=extra_template_dirs,
        output_dir=output_dir, fresh_output=fresh_output,
        test_mode=test_mode, build_time=build_time,
        deterministic=deterministic, skip_pdf=skip_pdf,
    )
