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
import datetime
import json
import logging
import os
from pathlib import Path
from pprint import pprint
import re
import sys

import babel.dates
import dateutil.parser
import jinja2
from jinja2 import (contextfilter, contextfunction, Environment, FileSystemLoader,
    TemplateSyntaxError)
from jinja2.utils import Namespace
import yaml


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

    parser.add_argument('--version',action='version',version='%(prog)s '+VERSION)
    parser.add_argument('-v','--verbose',action='store_true',
                        help='enable verbose info printout')
    parser.add_argument('-t',dest='test',action='store_true',
                        help='test mode, print files to expand')
    parser.add_argument('--debug',action='store_true',
                        help='enable debug printout')
    parser.add_argument('--config-path', '-c', dest='config_path', metavar='PATH',
                        help='path to the configuration file to use')
    parser.add_argument('--json-path', '-j', dest='jsonfile', metavar='PATH',
                        action='append',
                        help='load the specified json data to template global')
    parser.add_argument('--yaml-path', '-y', dest='yamlfile', metavar='PATH',
                        action='append',
                        help='load the specified yaml data to template global')
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

def generate_output_name():
    """
    Return a name of the form "build_20180511_224339".
    """
    now = datetime.datetime.now()
    name = 'build_{:%Y%m%d_%H%M%S}'.format(now)

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


@contextfilter
def translate(context, label):
    """
    Return the translation using the currently set language.
    """
    options = context['options']
    lang = options.lang

    all_trans = context['translations']
    translations = all_trans[label]
    translated = translations[lang]
    return translated


@contextfunction
def subtemplate(context, template_name, file_name):
    jinja_env = context.environment

    process_template(jinja_env, template_name=template_name, rel_output_path=file_name,
        context=context)


#--- Template global setup: ---

def create_jinja_env(template_dirs, output_dir):
    """
    Create and return the Jinja2 Environment object.

    Args:
      output_dir: a Path object.
    """
    jinja_env = Environment(
        loader=FileSystemLoader(template_dirs),
        autoescape=jinja2.select_autoescape(['html', 'xml']),
        # Enable the expression-statement extension:
        # http://jinja.pocoo.org/docs/2.10/templates/#expression-statement
        extensions=['jinja2.ext.do'],
    )

    # Using a Namespace object lets us change the context inside a
    # template, e.g. by calling "{% set options.lang = lang %}" from
    # within a with block.  Doing this lets us access the option values
    # from within a custom filter, without having to pass the option
    # values explicitly.
    options = Namespace()
    # Apparently we need to set using index rather than attribute notation.
    options['output_dir'] = output_dir

    jinja_env.globals.update(options=options, subtemplate=subtemplate)

    # The following dictionary of filter and test functions will be auto-edited.
    # [Do not change these, instead edit the docstrings in the function def]
    filters = dict(format_date=format_date, translate=translate)
    tests = {}

    jinja_env.filters.update(filters)
    jinja_env.tests.update(tests)

    return jinja_env


#--- Template processing: ---

def process_template(jenv:Environment, template_name:str, rel_output_path:Path,
    context:dict=None, test_mode:bool=False):
    """
    Creates the specified output file using the named template,
    where `data` provides the template context. The template
    and included templates will be located within the template
    search path, already setup via configuration data.

    Args:
      jenv: the Jinja2 Environment object to use.
      template_name: template to expand.
      rel_output_path: the output path (relative to the output directory
        configured in the Jinja2 Environment object), or else '-'.
      context: optional context data.
    """
    if context is None:
        context = {}

    if test_mode:
        print(
            f'Will process_template {template_name} to create {output_path})')
        return

    options = jenv.globals['options']
    output_dir = options.output_dir
    output_path = output_dir / rel_output_path

    _log.debug(f'process_template: {template_name} -> {output_path}')

    template = jenv.get_template(template_name)

    # PDF output renders using html, create a .pdf.html file
    if output_path.suffix == '.pdf':
        pdf_path = output_path
        output_path += '.html'
    else:
        pdf_path = ''

    output_dir = output_path.parent
    if not output_dir.exists():
        output_dir.mkdir()

    output_text = template.render(context)
    output_path.write_text(output_text)
    _log.info(f'Created {output_path} from template {template_name}')

    if pdf_path:
        # Convert the html file to pdf_path
        #[TODO]
        return

#--- Top level processing: ---

# TODO: render the directory recursively.
def render_template_dir(template_dir, output_dir, jinja_env, test_mode=False):
    """
    Render the templates inside the given template directory.

    Args:
      template_dir: a Path object.
      output_dir: a Path object.
      jinja_env: a Jinja2 Environment object.
      test_mode: a boolean.
    """
    # Process templates
    for template_path in template_dir.iterdir():
        if template_path.is_dir():
            # TODO: process directories recursively.
            continue

        file_name = template_path.name
        process_template(jinja_env, template_name=file_name, rel_output_path=file_name,
            test_mode=test_mode)


def run(config_path=None, json_paths=None, yaml_paths=None, template_dir=None,
    extra_template_dirs=None, output_parent=None, output_dir_name=None,
    fresh_output=False, test_mode=False):
    """
    Args:
      config_path: optional path to the config file, as a string.
      template_dir: a directory containing the templates to render.
      extra_template_dirs: optional extra directories to search for
        templates (e.g. for the subtemplate tag).  This should be a list
        of path-like objects.
      json_paths: paths to JSON files, as a list of strings.
      yaml_paths: paths to YAML files, as a list of strings.
      output_parent: the parent of the output directory.
      output_dir_name: the name to give the output directory inside the
        output parent.  Defaults to a name generated using the current
        datetime.
    """
    if json_paths is None:
        json_paths = []
    if yaml_paths is None:
        yaml_paths = []
    if extra_template_dirs is None:
        extra_template_dirs = []
    if output_parent is None:
        output_parent = DEFAULT_OUTPUT_PARENT_DIR
    if output_dir_name is None:
        output_dir_name = generate_output_name()

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
    jinja_env = create_jinja_env(template_dirs, output_dir=output_dir)

    # Use the jinja global dict for root election data
    jinja_globals = jinja_env.globals

    # Process data loader arguments
    for json_path in json_paths:
        load_json(jinja_globals, json_path)

    for yaml_path in yaml_paths:
        load_yaml(jinja_globals, yaml_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    render_template_dir(template_dir, output_dir=output_dir, jinja_env=jinja_env,
        test_mode=test_mode)

    _log.info(f'writing the output directory to stdout: {output_dir}')
    print(output_dir)


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
    template_dir = ns.template_dir
    extra_template_dirs = ns.extra_template_dirs
    json_paths = ns.jsonfile
    yaml_paths = ns.yamlfile

    output_parent = ns.output_parent
    output_dir_name = ns.output_dir_name
    fresh_output = ns.output_fresh_parent

    test_mode = ns.test

    run(config_path=config_path, json_paths=json_paths, yaml_paths=yaml_paths,
        template_dir=template_dir, extra_template_dirs=extra_template_dirs,
        output_parent=output_parent, output_dir_name=output_dir_name,
        fresh_output=fresh_output, test_mode=test_mode)


if __name__ == '__main__':
    main()
