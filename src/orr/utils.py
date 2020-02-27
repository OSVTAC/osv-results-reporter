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
import re
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import urllib.parse

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

ENGLISH_LANG = 'en'

UTF8_ENCODING = 'utf-8'
US_LOCALE = 'en_US.UTF-8'

ELEMENT_ID_SEP = '-'
# A regex pattern matching one or more consecutive hyphens (ELEMENT_ID_SEP).
ELEMENT_ID_PATTERN = re.compile('-+')

# The buffer size to use when hashing files.
HASH_BYTES = 2 ** 12  # 4K

# Our options for pretty-printing JSON for increased human readability.
DEFAULT_JSON_DUMPS_ARGS = dict(sort_keys=True, indent=4, ensure_ascii=False)

# We use a txt extension as opposed to no extension to make the file
# viewable from a browser.  When no extension is used, browsing to the
# file prompts for download rather than displaying it for viewing.
SHASUMS_PATH = Path('SHA256SUMS.txt')
ZIP_FILE_BASE = 'full-results'


def get_language(context):
    """
    Return the currently active language, as a 2-letter language code (e.g. "en").
    """
    if 'options' not in context:
        return ENGLISH_LANG

    options = context['options']
    lang = options.lang

    return lang


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


def make_non_breaking(text):
    """
    Return the string back with whitespace replaced by "&nbsp;".
    """
    return '&nbsp;'.join(text.split())


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


def compute_percent(numer, denom):
    """
    Compute a numeric percent, given a numerator and denominator.

    This function differs from the "format" variants below by returning
    a number even if the denominator is 0.  This is useful in certain
    situations (e.g. in templates) when a number is always desired.

    >>> compute_percent(1, 3)
    33.333333333333336
    >>> compute_percent(1, 0)
    0
    """
    if not denom:
        return 0

    if numer == denom:
        # Special-casing equality ensures e.g. that 100 is returned instead
        # of 99.99999999999 in certain floating-point edge cases (like 1/3).
        quotient = 1
    else:
        quotient = numer / denom

    return 100 * quotient


def format_percent(percent):
    """
    Format a percentage for display.

    >>> format_percent(12.4)
    '12.40%'
    """
    if percent is None:
        return ''
    return f'{percent:.2f}%'


def format_percent2(num, denom):
    """
    Format a percentage for display as num/denom.
    """
    if denom is None or num is None or denom == 0:
        return ''
    else:
        return(format_percent(100 * num/denom))


def _convert_fragment(char):
    if unicodedata.category(char)[0] in ('L', 'N'):  # letter or number
        return char

    return ELEMENT_ID_SEP


def make_lang_path(default_path, context, lang=None):
    """
    Create the path for the given language and context, and return a Path object.

    Args:
      default_path: the path without any language suffix.

    For example:

        >>> make_lang_path('details/contest-1.html', context={}, lang='es')
        Path('details/contest-1-es.html')
    """
    if lang is None:
        lang = get_language(context)

    # We want the return value to be a Path object.
    path = Path(default_path)

    # Only add the language code if not English.
    if lang == ENGLISH_LANG:
        return path

    name = Path(path.name)
    name = f'{name.stem}-{lang}{name.suffix}'

    return path.with_name(name)


def make_element_id(text):
    """
    Create an element id from text (e.g. to support navigation within a
    page using a fragment identifier).

    Args:
      text: the text to convert.

    Examples:

    >>> make_element_id('MEMBER - DISTRICT 17')
    'member-district-17'
    """
    element_id = ''.join(_convert_fragment(char) for char in text.lower())
    # Collapse consecutive hyphens.
    element_id = re.sub(ELEMENT_ID_PATTERN, ELEMENT_ID_SEP, element_id)
    # Strip trailing dashes (for cosmetic reasons).
    element_id = element_id.rstrip(ELEMENT_ID_SEP)

    return element_id


def to_fragment(element_id):
    """
    Convert an element id to a (quoted) fragment identifier.
    """
    try:
        quoted = urllib.parse.quote(element_id)
    except Exception:
        raise RuntimeError(f'failed with: {element_id!r}')

    return f'#{quoted}'


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


def read_json(filepath):
    """
    Data Loader: Reads the specified json file into a python data structure
    """
    _log.debug(f'load_json({filepath})')
    with open(filepath) as f:
        data = json.load(f)

    return data


def make_zip_file_name(zip_file_base):
    return f'{zip_file_base}.tar.gz'


# TODO: test this.
def create_tar_gz(source_dir, output_path, zip_file_base):
    with tarfile.open(output_path, 'w:gz') as tar:
        # The "arcname" is what the name of the directory will be after unzipping.
        tar.add(source_dir, arcname=zip_file_base)


# TODO: test this.
def gzip_directory_to(source_dir, output_dir, zip_file_base):
    zip_file_name = make_zip_file_name(zip_file_base)

    # Add a zip of the directory to the directory.
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        initial_zip, final_zip = (
            dir_path / zip_file_name for dir_path in (temp_dir, output_dir)
        )
        create_tar_gz(source_dir, initial_zip, zip_file_base=zip_file_base)
        initial_zip.rename(final_zip)


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
def compute_sha256sum(dir_path, exclude_paths=None):
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


def process_template(env:Environment, template_name:str, default_rel_output_path:str=None,
    context:dict=None, test_mode:bool=False, skip_writing=False):
    """
    Write (aka render) a template file to the given relative path.

    Returns the path to the created file, as a Path object.

    Args:
      env: a Jinja2 Environment object.
      template_name: template to expand.
      default_rel_output_path: the output path to which to write the rendered
        template, without any language suffix.  This should be a path
        relative to the output directory configured in the Jinja2 Environment
        object.  An example value is: "results-detail/contest-403.html".
      context: optional context data, as a dict or Jinja Context object.
      skip_writing: whether to skip writing the output to a file.
        This is useful for "control flow" templates whose only purpose
        is to render other templates.
    """
    if default_rel_output_path is None:
        default_rel_output_path = template_name

    if context is None:
        context = {}
    elif hasattr(context, 'get_exported'):
        # Then the context is a Context object.
        # Copy the context to a dict so we can add to it below.
        context = context.get_all()
    else:
        # Then the context is a dict.  Make a copy of it because we will
        # be changing it (adding to it) below.
        context = context.copy()

    if test_mode:
        print(
            f'Will process_template {template_name} to create {output_path})')
        return

    rel_output_path = make_lang_path(default_rel_output_path, context=context)
    output_path = get_output_path(env, rel_output_path)
    _log.debug(f'process_template: {template_name} -> {output_path}')

    template = env.get_template(template_name)

    output_dir = output_path.parent
    if not output_dir.exists():
        output_dir.mkdir()

    context.update({
        'default_rel_path': Path(default_rel_output_path),
    })
    rendered = template.render(context)

    if skip_writing:
        _log.info(f'Processed template {template_name} and skipping writing to: {output_path}')
    else:
        # Strip trailing whitespace as a normalization step to simplify
        # testing.  For example, this way we don't have to check files in
        # to our repository that have trailing whitespace.
        rendered = strip_trailing_whitespace(rendered)
        output_path.write_text(rendered)
        _log.info(f'Processed template {template_name} and wrote to: {output_path}')

    return rel_output_path
