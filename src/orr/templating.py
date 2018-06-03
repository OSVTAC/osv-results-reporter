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
Includes custom template filters and context functions.
"""

import functools
import logging
from pathlib import Path

from jinja2 import (contextfilter, contextfunction, environmentfilter,
    environmentfunction, Environment)

import orr.utils as utils
import orr.writers.pdfwriting as pdfwriting
import orr.writers.tsvwriting as tsvwriting
from orr.writers.xlsxwriting import XLSXBook


_log = logging.getLogger(__name__)

ENGLISH_LANG = 'en'


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


# TODO: move this function to a different module.
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
    rendered = utils.strip_trailing_whitespace(rendered)
    output_path.write_text(rendered)
    _log.info(f'Created {output_path} from template {template_name}')


@environmentfilter
def output_file_uri(env, rel_path):
    """
    Return an (absolute) file URI to an output path.

    This template filter can be used to add hyperlinks to allow browsing
    the rendered files on the local file system.

    Args:
      env: a Jinja2 Environment object.
      rel_path: a path relative to the output directory configured in the
        Jinja2 Environment object. This can be any path-like object.
    """
    output_path = get_output_path(env, rel_path)
    output_path = output_path.resolve()
    uri = output_path.as_uri()

    return uri


# TODO: support other hash algorithms.
@environmentfilter
def secure_hash(env, rel_path):
    """
    Return a secure hash of the contents of the file, using SHA-256.

    Returns the hash as a hexadecimal string.

    Args:
      env: a Jinja2 Environment object.
      rel_path: a path relative to the output directory configured in the
        Jinja2 Environment object. This can be any path-like object.
    """
    path = get_output_path(env, rel_path)
    sha = utils.hash_file(path)

    return sha


def _format_date(context, date, format_=None):
    lang = context['options'].lang
    try:
        return utils.format_date(date, lang=lang, format_=format_)
    except Exception:
        raise RuntimeError(f'error formatting date: {date!r}')


@contextfilter
def format_date(context, day, format_=None):
    """
    Format a date in the form "February 5, 2018" (internationalized).

    Args:
      day: a datetime.date object.
      format_: a string format parameter, either the standard "short",
        "medium", "long", or "full" (default is "long"), or a pattern in
        the Locale Data Markup Language specification.
    """
    return _format_date(context, day, format_=format_)


@contextfilter
def format_date_medium(context, day):
    """
    Format a date in the form "Feb 5, 2018" (internationalized).

    Args:
      day: a datetime.date object.
    """
    return _format_date(context, day, format_='medium')


def choose_translation(translations, lang):
    try:
        text = translations[lang]
    except KeyError:
        # Then default to English.
        _log.warning(f'missing {lang!r} translation: {translations}')
        text = translations[ENGLISH_LANG]

    return text


@contextfilter
def translate(context, value):
    """
    Return the translation using the currently set language.
    """
    options = context['options']
    lang = options.lang

    if type(value) == dict:
        text = choose_translation(value, lang)
    else:
        # Then assume the value is the key for a translation.
        try:
            all_trans = context['translations']
        except KeyError:
            raise RuntimeError(f'"translations" missing while translating: {value}')
        translations = all_trans[value]
        text = choose_translation(translations, lang)

    return text


@contextfunction
def subtemplate(context, template_name, file_name):
    """
    Render a template.
    """
    env = context.environment

    process_template(env, template_name=template_name, rel_output_path=file_name,
        context=context)


def make_contest_pairs(contests):
    """
    Return an iterable of pairs (contest_name, rows).

    Args:
      contests: an iterable of contest data, where each element is a dict
        with keys "name" and "rows".
    """
    return [(contest['name'], contest['rows']) for contest in contests]


@environmentfunction
def create_tsv_files(env, rel_dir, contests):
    """
    Create a TSV file of row data, one for each contest.

    Args:
      rel_dir: a directory relative to the output path configured in the
        given Jinja2 environment.
    """
    output_dir = get_output_dir(env)
    contests = make_contest_pairs(contests)

    yield from tsvwriting.make_tsv_directory(output_dir, rel_dir, contests)


def create_file(do_create, rel_path, contests, type_name, ext, env):
    """
    Create a file of contest data using the given function, and return
    a Path object.

    Args:
      do_create: a function with signature create(output_path, contests)
        that creates the file.
      rel_path: a path relative to the output directory configured in the
        Jinja2 Environment object. This can be any path-like object
        and should **not** have the file extension added (the function
        will add it).
      type_name: the name of the file type, for logging purposes.
      ext: the file extension to use, including the leading dot.
      env: a Jinja2 Environment object.
    """
    rel_path = Path(rel_path)
    # Add the suffix.
    rel_path = rel_path.with_suffix(ext)
    output_path = get_output_path(env, rel_path)

    contests = make_contest_pairs(contests)

    do_create(output_path, contests=contests)

    return rel_path


@environmentfunction
def create_xlsx(env, rel_path, contests):
    """
    Create an XLSX file of contest data, and return a path to the file
    relative to the output directory, as a Path object.

    Args:
      env: a Jinja2 Environment object.
      rel_path: a path relative to the output directory configured in the
        Jinja2 Environment object. This can be any path-like object
        and should **not** have the file extension added (the function
        will add it).
      contests: an iterable of contest data, where each element is a dict
        with keys "name" and "rows".

    The file is written to the given path, relative to the output path
    configured in the given Jinja2 environment.
    """
    def do_create(output_path, contests):
        # TODO: convert to with-block syntax.
        try:
            book = XLSXBook(output_path)
            for contest_name, rows in contests:
                book.add_sheet(contest_name, rows)
        finally:
            book.close()

    rel_path = create_file(do_create, rel_path=rel_path, contests=contests,
                        type_name='Excel', ext='.xlsx', env=env)

    return rel_path


@environmentfunction
def create_pdf(env, rel_path, contests, title=None):
    """
    Create a PDF of contest data, and return a path to the file relative
    to the output directory, as a Path object.

    Args:
      env: a Jinja2 Environment object.
      rel_path: a path relative to the output directory configured in the
        Jinja2 Environment object. This can be any path-like object
        and should **not** have the file extension added (the function
        will add it).
      contests: an iterable of contest data, where each element is a dict
        with keys "name" and "rows".
      title: an optional title to set on the PDF's properties.

    The file is written to the given path, relative to the output path
    configured in the given Jinja2 environment.
    """
    do_create = functools.partial(pdfwriting.make_pdf, title=title)

    rel_path = create_file(do_create, rel_path=rel_path, contests=contests,
                        type_name='PDF', ext='.pdf', env=env)

    return rel_path
