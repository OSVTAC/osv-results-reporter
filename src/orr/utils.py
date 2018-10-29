#
# Open Source Voting Results Reporter (ORR) - election results report generator
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
Simple helper functions.
"""

from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import locale
import logging
import os
from pathlib import Path
import subprocess
import sys

import babel.dates
from jinja2 import Environment


_log = logging.getLogger(__name__)

try:
    # See the Dockerfile for where we create this module.
    import orr.in_docker
except ModuleNotFoundError:
    IN_DOCKER = False
else:
    IN_DOCKER = True


UTF8_ENCODING = 'utf-8'
US_LOCALE = 'en_US.UTF-8'

# The buffer size to use when hashing files.
HASH_BYTES = 2 ** 12  # 4K

# Our options for pretty-printing JSON for increased human readability.
DEFAULT_JSON_DUMPS_ARGS = dict(sort_keys=True, indent=4, ensure_ascii=False)

SHA256SUMS_FILENAME = 'SHA256SUMS'


def get_output_dir(env):
    """
    Return the output directory, as a Path object.

    Args:
      env: a Jinja2 Environment object.
    """
    options = env.globals['options']
    output_dir = options.output_dir

    return output_dir


def get_output_path(env, rel_path):
    """
    Return the output path, as a Path object.

    Args:
      env: a Jinja2 Environment object.
      rel_path: a path relative to the output directory configured in the
        Jinja2 Environment object. This can be any path-like object.
    """
    output_dir = get_output_dir(env)
    path = output_dir / rel_path

    return path


def truncate(obj):
    """
    Return an object representation guaranteed not to exceed a reasonable
    length.  This is useful e.g. for logging.
    """
    if type(obj) != str:
        obj = repr(obj)
    if len(obj) > 40:
        # Add an ellipsis to indicate that a truncation occurred.
        return f'{obj[:40]!r}...'

    return repr(obj)


@contextmanager
def changing_cwd(dir_path):
    """
    Temporarily change the current working directory.
    """
    initial_cwd = os.getcwd()
    try:
        os.chdir(dir_path)
        yield
    finally:
        # Change back.
        os.chdir(initial_cwd)


@contextmanager
def changing_locale(loc):
    """
    Temporarily change locale.LC_ALL.
    """
    try:
        try:
            locale.setlocale(locale.LC_ALL, loc)
        except Exception:
            raise RuntimeError(f'error while setting locale to: {loc}')
        yield
    finally:
        # Change back.
        locale.resetlocale()


# TODO: rename to format_integer()?
def format_number(num):
    """
    Format a number for display using the current locale, e.g.

    >>> format_number(9999)
    '9,999'
    """
    # The "n" option adds a locale-aware thousands separator.
    if num is None: return ''
    return f'{num:n}'


def format_percent(percent):
    """
    Format a percentage for display.

    >>> format_percent(12.4)
    '12.40%'
    """
    if percent is None:
        return ''
    return f'{percent:.2f}%'

def format_percent2(num,denom):
    """
    Format a percentage for display as num/denom.
    """
    if denom is None or num is None or denom == 0:
        return ''
    else:
        return(format_percent(100*num/denom))

def read_json(filepath):
    """
    Data Loader: Reads the specified json file into a python data structure
    """
    _log.debug(f'load_json({filepath})')
    with open(filepath) as f:
        data = json.load(f)

    return data

def read_yaml(filepath):
    """
    Data Loader: Reads the specified yaml file into a python data structure
    """
    _log.debug(f'load_yaml({filepath})')
    if filepath=='-':
        data = yaml.safe_load(sys,stdin)
    else:
        with open(filepath) as f:
            data = yaml.safe_load(f)

    return data

def strip_trailing_whitespace(text):
    """
    Strip trailing whitespace from the end of each line.
    """
    lines = text.splitlines()
    text = ''.join(line.rstrip() + '\n' for line in lines)

    return text


def parse_datetime(dt_string):
    """
    Parse a string in a standard format representing a datetime, and
    return a datetime.datetime object.

    Args:
      dt_string: a datetime string in the format, "2018-06-01 20:48:12".
    """
    return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')


def format_date(date, lang, format_=None):
    """
    Args:
      date: a datetime.date object.
      lang: a 2-letter language code.
    """
    if format_ is None:
        format_ = 'long'
    return babel.dates.format_date(date, format=format_, locale=lang)


# TODO: support other hash algorithms.
def hash_file(path):
    """
    Hash the contents of a file, using SHA-256.

    Returns the result as a hexadecimal string.
    """
    hasher = hashlib.sha256()
    with open(path, mode='rb') as f:
        while True:
            data = f.read(HASH_BYTES)
            if not data:
                break
            hasher.update(data)

    sha = hasher.hexdigest()

    return sha


# TODO: test this.
def get_files_recursive(dir_path):
    """
    Return the paths to all files (but not directories) in a directory
    by searching recursively, and return them as paths relative to the
    directory being searched over.
    """
    # Change the current working directory to the directory we are recursing
    # over so the resulting paths will be relative to that.
    with changing_cwd(dir_path):
        cwd = Path('.')
        paths = sorted(str(path) for path in cwd.glob('**/*') if not path.is_dir())

    return paths


def get_sha256sum_args():
    """
    Return the initial platform-specific arguments to generate SHA256SUMS.
    """
    platform = sys.platform

    if platform == 'darwin':
        # On Mac OS X, sha256sum isn't available.
        # Also, we need to specify 256 manually here because `shasum`
        # defaults to SHA-1.
        args = ['shasum', '--algorithm', '256', '-b']
    else:
        args = ['sha256sum', '-b']

    return args


# TODO: also expose a function to check a SHA256SUMS file.
def directory_sha256sum(dir_path, exclude_paths=None):
    """
    Run sha256sum (or shasum on Mac OS X) on the files in a directory, and
    return the result as a string.

    Args:
      exclude_paths: an optional iterable of path-like objects to
        exclude from passing to sha256sum.
    """
    if exclude_paths is None:
        exclude_paths = []

    dir_path = Path(dir_path)

    # Get the paths relative to the directory we are recursing over.
    # Also, `sha256sum` breaks if passed a directory path, so we need to
    # be filtering those out, which get_files_recursive() does do.
    rel_paths = get_files_recursive(dir_path)

    # Convert the path-like objects to strings before doing the equality check.
    rel_paths = [str(rel_path) for rel_path in rel_paths]
    exclude_paths = set(str(path) for path in exclude_paths)

    rel_paths = [path for path in rel_paths if path not in exclude_paths]

    initial_args = get_sha256sum_args()
    args = initial_args.copy()
    args.extend(str(rel_path) for rel_path in rel_paths)

    _log.info(f"computing SHA256SUMS using: {' '.join(initial_args)} ...")
    proc = subprocess.run(args, stdout=subprocess.PIPE, encoding=UTF8_ENCODING,
                          check=True, cwd=dir_path)
    text = proc.stdout

    return text


def process_template(env:Environment, template_name:str, rel_output_path:Path,
    context:dict=None, test_mode:bool=False):
    """
    Creates the specified output file using the named template,
    where `data` provides the template context. The template
    and included templates will be located within the template
    search path, already setup via configuration data.

    Args:
      env: a Jinja2 Environment object.
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

    output_path = get_output_path(env, rel_output_path)

    _log.debug(f'process_template: {template_name} -> {output_path}')

    template = env.get_template(template_name)

    output_dir = output_path.parent
    if not output_dir.exists():
        output_dir.mkdir()

    rendered = template.render(context)

    # Strip trailing whitespace as a normalization step to simplify
    # testing.  For example, this way we don't have to check files in
    # to our repository that have trailing whitespace.
    rendered = strip_trailing_whitespace(rendered)
    output_path.write_text(rendered)
    _log.info(f'Created {output_path} from template {template_name}')
