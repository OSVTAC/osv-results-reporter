#!/usr/bin/env python3
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
Program to create HTML/PDF/XLS files from election results data.
Documentation: [TODO]
"""

import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
from pprint import pprint
import re
import sys
from textwrap import dedent

from jinja2 import TemplateSyntaxError
import yaml

import orr.configlib as configlib
import orr.dataloading as dataloading
from orr.dataloading import INPUT_FILE_NAME, DEFAULT_RESULTS_DIR_NAME
import orr.templating as templating
import orr.utils as utils
from orr.utils import DEFAULT_JSON_DUMPS_ARGS, SHA256SUMS_FILENAME, US_LOCALE


_log = logging.getLogger(__name__)

VERSION='0.0.1'     # Program version

DEFAULT_OUTPUT_PARENT_DIR = '_build'
DEFAULT_TEMPLATE_DIR = 'templates'

ENCODING='utf-8'


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

    parser.add_argument('--version', action='version', version='%(prog)s '+VERSION)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='enable verbose info printout')
    parser.add_argument('-t', dest='test', action='store_true',
                        help='test mode, print files to expand')
    parser.add_argument('--debug', action='store_true', help='enable debug printout')
    parser.add_argument('--config-path', '-c', dest='config_path', metavar='PATH',
                        help='path to the configuration file to use')
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
    parser.add_argument('--build-time', metavar='DATETIME',
                        help=('the datetime to use as the build time, '
                              'in the format "2018-06-01 20:48:12". '
                              'Defaults to the current datetime.'))
    parser.add_argument('--deterministic', action='store_true',
                        help='make PDF generation deterministic.')
    parser.add_argument('--template-dir', metavar='DIR', default=DEFAULT_TEMPLATE_DIR,
                        help=('directory containing the template files to render. '
                              f'Defaults to: {DEFAULT_TEMPLATE_DIR}.'))
    parser.add_argument('--extra-template-dirs', metavar='DIR', nargs='+',
                        help=('extra directories to search when looking for '
                              'templates, and not rendered otherwise.'))
    parser.add_argument('--output-parent', metavar='DIR',
                        help=('the directory in which to write the output directory. '
                              f'Defaults to: {DEFAULT_OUTPUT_PARENT_DIR}.'))
    parser.add_argument('--output-dir-name', metavar='NAME',
                        help=('the name to give the output directory inside '
                              'the parent output directory. '
                              'Defaults to a name generated using the current datetime.'))
    parser.add_argument('--output-fresh-parent', action='store_true',
                        help=('require that the output parent not already exist. '
                              'This is for running inside a Docker container.'))

    ns = parser.parse_args()

    return ns

#--- Utility Routines: ---

def generate_output_name(dt):
    """
    Return a name of the form "build_20180511_224339".

    Args:
      dt: a datetime object.
    """
    name = 'build_{:%Y%m%d_%H%M%S}'.format(dt)

    return name

#--- Configuration file processing: ---

class Config(dict):

    """
    [TODO]
    """

    def __init__(self, config_path:Path):
        """
        Args:
          config_path: path to the YAML configuration file to load, as a
            Path object.
        """
        self._config_path = config_path

        # Collect other include files to merge
        self.include_config = []

        local_config = self.load_config_file(config_path);
        # We could do some default operations here, e.g.
        # locating a root level config and using a search path
        # or other means to find configuration data. [TODO]

        self.overlay_config(local_config)

        while len(self.include_config)>0:
            f = self.include_config.pop(0)
            self.overlay_config(self.load_config_file(f))

    def load_config_file(self,filepath:str):
        """
        Loads the parsed contents of the specified file.

        Returns: the parsed data, as a dict.

        Raises an exception if the file is not present or is invalid.

        Args:
          filepath: Full file path to load
        """
        _log.info(f'Loading config data from {filepath}')
        config = utils.read_yaml(filepath)
        # Verify the returned data is a dict
        #[TODO]
        return config

    def overlay_config(self,newconfig:dict,replace:bool=False):
        """
        Overlays a configuration dict into the configuration data,
        either replacing any existing data (a higher level config
        replaces pre-loaded default data) or setting values only
        if not already defined (the new config provides defaults).

        Each item in newconfig is validated and possibly converted
        from a string format.

        [For future] Some config attributes might be prepended or appended,
        as defined in the config schema.

        Args:
          newconfig:    Parsed configuration data dict or None to skip
          replace:      If true, replace defined entries, otherwise not
        """
        if newconfig is None:
            return

        for k,v in newconfig.items():
            if k == 'include_config':
                # push nested whitespace separated list of config files
                self.include_config += v.split()
                continue

            if not replace and hasattr(self,k): continue;
            # Validate the new attribute value
            # [TODO]
            _log.debug(f'set Config.{k}={v}')
            setattr(self,k,v)

    def overlay_config_file(self,filepath:str,replace=False):
        """
        Shorthand combination of load_config_file() and overlay_config()
        """
        self.overlay_config(self.load_config_file(filepath),replace)

    def overlay_config_path(self,searchpath,filename:str,replace=False):
        """
        Overlay configuration files found in the search path
        """


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
    elif suffix == '.yaml':
        newdata = utils.read_yaml(path)
    else:
        raise RuntimeError(f'unsupported suffix {suffix!r} for input path: {path}')

    if not isinstance(newdata, dict):
        _log.error(f'Invalid data in file {path}');
        return
    data.update(newdata)
    _log.info(f'loaded data from {path}')


#--- Top level processing: ---

# TODO: render the directory recursively.
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
            # TODO: process directories recursively.
            continue

        file_name = template_path.name
        utils.process_template(env, template_name=file_name, rel_output_path=file_name,
            context=context, test_mode=test_mode)


def make_sha256sums_file(dir_path):
    shasums_file = SHA256SUMS_FILENAME
    # Don't include SHA256SUMS because its hash will necessarily be incorrect
    # after SHA256SUMS is updated.
    exclude_paths = [shasums_file]

    contents = utils.directory_sha256sum(dir_path, exclude_paths=exclude_paths)
    sha256sums_path = dir_path / shasums_file
    sha256sums_path.write_text(contents)


def run(config_path=None, input_dir=None, input_results_dir=None, template_dir=None,
    extra_template_dirs=None, output_parent=None, output_dir_name=None,
    fresh_output=False, test_mode=False, build_time=None, deterministic=None):
    """
    Args:
      config_path: optional path to the config file, as a string.
      input_dir: required path to the input directory, as a string.
      input_results_dir: optional path the the input results data directory,
        as a string.  Defaults to a directory inside the input directory.
      template_dir: a directory containing the templates to render.
      extra_template_dirs: optional extra directories to search for
        templates (e.g. for the subtemplate tag).  This should be a list
        of path-like objects.
      output_parent: the parent of the output directory.
      output_dir_name: the name to give the output directory inside the
        output parent.  Defaults to a name generated using the current
        datetime.
      build_time: this is exposed to permit reproducible builds more easily.
      deterministic: for deterministic PDF generation.  Defaults to False.
    """
    if extra_template_dirs is None:
        extra_template_dirs = []
    if output_parent is None:
        output_parent = DEFAULT_OUTPUT_PARENT_DIR
    if build_time is None:
        build_time = datetime.now()

    if output_dir_name is None:
        output_dir_name = generate_output_name(build_time)

    assert template_dir is not None

    if config_path is None:
        config = None
    else:
        config_path = Path(config_path)
        config = Config(config_path)

    output_parent = Path(output_parent)

    if fresh_output and output_parent.exists():
        msg = f'--output-fresh-parent: output parent directory already exists: {output_parent}'
        raise RuntimeError(msg)

    output_dir = output_parent / output_dir_name
    _log.debug(f'using output directory: {output_dir}')

    # Create the jinja environment
    # Convert the path to an absolute paths to simplify troubleshooting.
    template_dir = Path(template_dir)
    _log.debug(f'using template directory: {template_dir}')

    template_dirs = [template_dir] + extra_template_dirs
    env = configlib.create_jinja_env(output_dir=output_dir, template_dirs=template_dirs,
                                     deterministic=deterministic)

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

    output_dir.mkdir(parents=True, exist_ok=True)

    # TODO: allow different locales to be used (e.g. the system's default
    #  locale and/or a locale passed in via the command-line)?
    with utils.changing_locale(US_LOCALE):
        render_template_dir(template_dir, output_dir=output_dir, env=env,
            context=context, test_mode=test_mode)

    make_sha256sums_file(output_dir)

    output_data = dict(
        build_time=build_time.isoformat(),
        output_dir=str(output_dir),
    )

    # TODO: allow changing the stdout output format (e.g. YAML or text)?
    output = json.dumps(output_data, **DEFAULT_JSON_DUMPS_ARGS)

    # TODO: allow suppressing stdout?
    print(output)

    return output_data


def main():
    ns = parse_args()

    if ns.debug:
        level = logging.DEBUG
    elif ns.verbose:
        level = logging.INFO
    else:
        level = logging.ERROR

    logging.basicConfig(level=level)

    config_path = ns.config_path
    deterministic = ns.deterministic
    template_dir = ns.template_dir
    extra_template_dirs = ns.extra_template_dirs
    input_dir = ns.input_dir
    input_results_dir = ns.input_results_dir
    build_time = ns.build_time

    output_parent = ns.output_parent
    output_dir_name = ns.output_dir_name
    fresh_output = ns.output_fresh_parent

    test_mode = ns.test

    if build_time is not None:
        build_time = utils.parse_datetime(build_time)

    run(config_path=config_path, input_dir=input_dir, input_results_dir=input_results_dir,
        template_dir=template_dir, extra_template_dirs=extra_template_dirs,
        output_parent=output_parent, output_dir_name=output_dir_name,
        fresh_output=fresh_output, test_mode=test_mode, build_time=build_time,
        deterministic=deterministic)
