#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# orr.py - template-based HTML/PDF/XLS election results report generator
#
# Copyright (C) 2018  Carl Hage
# Copyright (C) 2018  Chris Jerdonek
#
# This program is free software: you can redistribute it and/or modify
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
# Contact info:
#
# The author(s) can be reached at--
#
#   Carl Hage <ch@carlhage.com>
#   Chris Jerdonek <chris.jerdonek@gmail.com>
#

"""
Program to create HTML/PDF/XLS files from election results data.
Documentation: [TODO]
"""

import argparse
import json
import logging
import os
from pathlib import Path
from pprint import pprint
import re
import sys

import babel.dates
import dateutil.parser
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateSyntaxError
import yaml


_log = logging.getLogger(__name__)

VERSION='0.0.1'     # Program version

DEFAULT_CONFIG_FILE_NAME = 'config-orr.yml'
DEFAULT_OUTPUT_DIR = '_build'

ENCODING='utf-8'


#--- Command line arguments: ---

# See the definitions below for list of options

DESCRIPTION = """\
generate HTML/PDF/XLS files from election results data
"""

def parse_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument('--version',action='version',version='%(prog)s '+VERSION)
    parser.add_argument('-v','--verbose',action='store_true',
                        help='enable verbose info printout')
    parser.add_argument('-t',dest='test',action='store_true',
                        help='test mode, print files to expand')
    parser.add_argument('--debug',action='store_true',
                        help='enable debug printout')
    parser.add_argument('-c', dest='config_path', metavar='configfile',
                        default=DEFAULT_CONFIG_FILE_NAME,
                        help='path to the configuration file to use')
    parser.add_argument('-j', dest='jsonfile', metavar='jsonfile',
                        action='append',
                        help='load the specified json data to template global')
    parser.add_argument('-y', dest='yamlfile', metavar='yamlfile',
                        action='append',
                        help='load the specified yaml data to template global')
    parser.add_argument('--output-dir',
                        help=f'output directory. Defaults to: {DEFAULT_OUTPUT_DIR}.')
    parser.add_argument('--output-name', metavar='outputname',
                        help=('name of the output file to create. '
                              'Defaults to the name of the template file.'))
    parser.add_argument('templatefilename',
                        help='template file name to process')

    args = parser.parse_args()
    return args

#--- Utility Routines: ---


#--- Configuration file processing: ---

# Config attributes that are space separated lists
# TODO: use structured YAML data rather than character delimited.
CONFIG_SP_SEP_LIST_ATTRS = ['orr_template_paths']


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

        self.finalize_config()

    def load_config_file(self,filepath:str):
        """
        Loads the parsed contents of the specified file.

        Returns: the parsed data, as a dict.

        Raises an exception if the file is not present or is invalid.

        Args:
          filepath: Full file path to load
        """
        _log.info(f'Loading config data from {filepath}')
        if filepath=='-':
            config = yaml.safe_load(sys,stdin)
        else:
            with open(filepath) as f:
                config = yaml.safe_load(f)
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

        if newconfig is None: return;

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

    def finalize_config(self):
        """
        Validate config data after loading, and add default values if needed.
        """
        # Add built-in defaults
        self.overlay_config({
            "orr_template_paths":"../templates"})

        # Validate config data
        # [TODO]

        # Convert from string notations
        for attr_name in CONFIG_SP_SEP_LIST_ATTRS:
            if not hasattr(self, attr_name):
                continue

            value = getattr(self, attr_name, '')
            values = value.split()
            setattr(self, attr_name, values)

    def get_template_paths(self):
        """
        Return the list of template paths to pass to Jinja, as a list of
        absolute paths.
        """
        config_dir = self._config_path.parent
        # Convert the paths to absolute paths.
        paths = [(config_dir / path).resolve() for path in self.orr_template_paths]

        return paths


#--- Data environment: ---

# The following routines help set/update the global environment data settings

#--- Data loaders: ---

# Data loaders retrieve a particular category of data content and
# merge into the `data` dict, if that category is not already present.
# Data loaders can be added across modules, and the docstring should
# begin with "Data Loader:" to identify documentation to be automatically
# included in the template file documentation.
# [TODO: Allow data loaders to be invoked in templates as function call]

def load_json(data,filepath):
    """
    Data Loader: The json data loader will read arbitrary
    json-formatted data from the named file
    and update/replace data to be processed with templates.
    The json content must be a dictionary (set of named values).
    """
    _log.debug(f'load_json({filepath})')
    with open(filepath) as f:
        newdata = json.load(f)
    if not isinstance(newdata,dict):
        _log.error(f'Invalid data in json file {filepath}');
        return
    data.update(newdata)
    _log.info(f'loaded json data from {filepath}')
    #_log.debug(str(data.keys()))

def load_yaml(data,filepath):
    """
    Data Loader: The yaml data loader will read arbitrary
    yaml-formatted data from the named file
    and update/replace data to be processed with templates.
    The yaml content must be a dictionary (set of named values).
    """
    _log.debug(f'load_yaml({filepath})')
    with open(filepath) as f:
        newdata = yaml.safe_load(f)
    if not isinstance(newdata,dict):
        _log.error(f'Invalid data in yaml file {filepath}');
        return
    data.update(newdata)
    _log.info(f'loaded yaml data from {filepath}')
    #_log.debug(str(data.keys()))


#--- Template filters and tests: ---

# Define filter and test function docstrings beginning with "Template Filter: "
# or "Template Test: ", so template documentation can be auto-extracted,
# and names for the filters or tests can be collected.

def format_date(value,format_str:str='medium'):
    """
    Template Filter: Converts a date value (str or datetime) into
    the internationalized representation. A format parameter
    can be supplied, either the standard short, medium, long, or
    full (default is medium), or a pattern in the Locale Data
    Markup Language specification.
    """

    if isinstance(value,str):
        value = dateutil.parser.parse(value)

    return(babel.dates.format_date(value,format_str))


# The following dictionary of filter and test functions will be auto-edited.
# [Do not change these, instead edit the docstrings in the function def]
filters = {"format_date":format_date}
tests = {}

#--- Template global setup: ---

def init_edata(edata:dict):
    """
    This routine is called to initialize built-in template variables.
    """

def init_jenv(jenv:Environment):
    """
    This routine is called after creating the template processing
    environment to add filters, tests, etc.
    """
    jenv.filters.update(filters)
    jenv.tests.update(tests)

#--- Template processing: ---

def process_template(jenv:Environment,
                     template_name:str,     # Template to expand
                     output_path:Path,   # Output file to write or '-'
                     ctx:dict=None,  # Context data or None
                     test_mode:bool=False,
                     ):
    """
    Creates the specified output file using the named template,
    where `data` provides the template context. The template
    and included templates will be located within the template
    search path, already setup via configuration data.
    """
    if test_mode:
        print(
            f'Will process_template {template_name} to create {output_path})')
        return

    _log.debug(f'process_template({template_name}, {output_path})')

    try:
        template = jenv.get_template(template_name)
    except TemplateSyntaxError as exc_info:
        _log.error("Template Syntax Error",exc_info)
        return

    # PDF output renders using html, create a .pdf.html file
    if output_path.suffix == '.pdf':
        pdf_path = output_path
        output_path += '.html'
    else: pdf_path = ''

    if ctx is None: ctx = {}

    output_dir = output_path.parent
    if not output_dir.exists():
        output_dir.mkdir()

    output_text = template.render(ctx)
    output_path.write_text(output_text)
    _log.info(f'Created {output_path} from template {template_name}')


    if pdf_path:
        # Convert the html file to pdf_path
        #[TODO]
        return

#--- Top level processing: ---

def run(config_path, json_paths=None, yaml_paths=None, output_dir=None,
    output_name=None, template_name=None, test_mode=False):
    """
    Args:
      config_path: path to the config file, as a Path object.
      json_paths: paths to JSON files, as a list of strings.
      yaml_paths: paths to YAML files, as a list of strings.
      output_dir: the output directory, as a path-like object.
      output_name: name of the output file.  Defaults to the name of the
        template.
      template_name: name of the template file.
    """
    if json_paths is None:
        json_paths = []
    if yaml_paths is None:
        yaml_paths = []
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    if output_name is None:
        output_name = template_name

    config = Config(config_path)

    output_dir = Path(output_dir)
    output_path = output_dir / output_name
    _log.debug(f'using output path: {output_path}')

    # Create the jinja environment
    template_paths = config.get_template_paths()
    _log.debug(f'using template paths: {template_paths}')

    jenv = Environment(loader=FileSystemLoader(template_paths),
        autoescape=select_autoescape(['html', 'xml']))

    # Use the jinja global dict for root election data
    edata = jenv.globals

    # Allow config data to be template accessible
    edata['config'] = config

    # Initialize built-in template variables
    init_edata(edata)

    # Add filters and tests
    init_jenv(jenv)

    # Process data loader arguments
    for json_path in json_paths:
        load_json(edata, json_path)

    for yaml_path in yaml_paths:
        load_yaml(edata, yaml_path)

    # Process template
    process_template(jenv, template_name=template_name, output_path=output_path,
        test_mode=test_mode)


def main():
    args = parse_args()

    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    else:
        level = logging.ERROR

    logging.basicConfig(level=level)

    config_path = Path(args.config_path)
    json_paths = args.jsonfile
    yaml_paths = args.yamlfile

    output_dir = args.output_dir
    output_name = args.output_name
    template_name = args.templatefilename
    test_mode = args.test

    run(config_path=config_path, json_paths=json_paths, yaml_paths=yaml_paths,
        output_dir=output_dir, output_name=output_name,
        template_name=template_name, test_mode=test_mode)


if __name__ == '__main__':
    main()
