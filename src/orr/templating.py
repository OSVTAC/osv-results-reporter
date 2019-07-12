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

import datetime
import functools
import json
import logging
from pathlib import Path

from jinja2 import (contextfilter, contextfunction, environmentfilter,
    environmentfunction, Undefined)

from orr.datamodel import SubstitutionString
import orr.utils as utils
from orr.utils import ENGLISH_LANG
import orr.writers.pdfwriting.pdfwriter as pdfwriter
import orr.writers.tsvwriting as tsvwriting
from orr.writers.xlsxwriting import XLSXBook


_log = logging.getLogger(__name__)


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
    output_path = utils.get_output_path(env, rel_path)
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
    path = utils.get_output_path(env, rel_path)
    sha = utils.hash_file(path)

    return sha


def _format_date(context, date, format_=None):
    lang = utils.get_language(context)

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
def translate(context, value, lang=None):
    """
    Return the translation using the currently set language.
    """
    if lang is None:
        lang = utils.get_language(context)

    if type(value) == dict:
        return choose_translation(value, lang)

    if isinstance(value, SubstitutionString):
        data = tuple(translate(context, part, lang=lang) for part in value.data)
        return value.format_string.format(*data)

    # Then assume the value is the key for a translation.
    try:
        all_trans = context['translations']
    except KeyError:
        raise RuntimeError(f'"translations" missing while translating: {value}')

    translations = all_trans[value]

    return choose_translation(translations, lang)


@contextfilter
def to_element_id(context, text):
    text = translate(context, text, lang=ENGLISH_LANG)
    return utils.make_element_id(text)


@contextfilter
def format_path(context, path_template, lang=None):
    """
    Format a path template, and return a string path.

    Args:
      path_template: a path as a format string.  The format string should
        have at most one replacement field -- for a language abbreviation.
    """
    if lang is None:
        lang = utils.get_language(context)

    return path_template.format(lang)


@contextfunction
def current_page_link(context, lang=None):
    """
    Return a link to the current page (optionally specifying a language
    version), as a link relative to the current page.

    Args:
      lang: an optional language abbreviation.  Defaults to the context's
        current language.
    """
    rel_path_template = context['rel_path_template']
    rel_path = Path(format_path(context, path_template=rel_path_template, lang=lang))
    filename = rel_path.name

    return filename


def contest_path_template(contest, dir_path=None):
    """
    Create and return a relative path template for a contest.

    The return value is a format string with the following as an example:
    "results-detail/contest-403-{}.html".
    """
    if dir_path is None:
        dir_path = ''

    return str(Path(dir_path) / f'contest-{contest.id}-{{}}.html')


@contextfunction
def make_translator(context):
    return functools.partial(translate, context)


@contextfunction
def subtemplate(context, template_name, rel_path_template):
    """
    Render a template.

    Args:
      rel_path_template: the output path to which to write the rendered
        template, as a format string.  The format string should have at most
        one replacement field -- for a language abbreviation.
           When formatted, it should be a path relative to the output
        directory configured in the Jinja2 Environment object.  An example
        value is "results-detail/contest-403-{}.html".
    """
    env = context.environment

    utils.process_template(env, template_name=template_name,
                rel_path_template=rel_path_template, context=context)


# TODO: turn this into a generator-iterator so not all data needs to be
#  loaded into memory at once.
def make_contest_pairs(contests, translate=None):
    """
    Return an iterable of pairs (contest_name, rows).

    Args:
      contests: an iterable of Contest objects.
      translate: a function that has the same signature as our
        translate() contextfilter.
    """
    pairs = []
    for contest in contests:
        names = translate(contest.ballot_title)
        headings = contest.detail_headings(translate=translate)
        rows = [headings]
        rows.extend(contest.detail_rows('CHOICES *'))
        pair = (names, rows)
        pairs.append(pair)

    return pairs


@environmentfunction
def create_tsv_files(env, rel_dir, contests):
    """
    Create a TSV file of row data, one for each contest.

    Args:
      rel_dir: a directory relative to the output path configured in the
        given Jinja2 environment.
    """
    output_dir = utils.get_output_dir(env)
    contests = make_contest_pairs(contests)

    yield from tsvwriting.make_tsv_directory(output_dir, rel_dir, contests)


def create_file(do_create, rel_path, contests, type_name, ext, env, translate=None):
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
    output_path = utils.get_output_path(env, rel_path)

    contests = make_contest_pairs(contests, translate=translate)

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
def create_pdf(env, rel_path, contests, title=None, translate=None):
    """
    Create a PDF of contest data, and return a path to the file relative
    to the output directory, as a Path object.

    Args:
      env: a Jinja2 Environment object.
      rel_path: a path relative to the output directory configured in the
        Jinja2 Environment object. This can be any path-like object
        and should **not** have the file extension added (the function
        will add it).
      contests: an iterable of Contest objects.
      title: an optional title to set on the PDF's properties.
      translate: a function that has the same signature as our
        translate() contextfilter.

    The file is written to the given path, relative to the output path
    configured in the given Jinja2 environment.
    """
    if type(contests) == Undefined:
        raise RuntimeError('contests argument is undefined')

    options = env.globals['options']
    if options.skip_pdf:
        _log.info(f'skipping PDF generation for path: {rel_path}')
        return ''

    deterministic = options.deterministic

    do_create = functools.partial(pdfwriter.make_pdf, title=title, deterministic=deterministic)

    rel_path = create_file(do_create, rel_path=rel_path, contests=contests,
                        type_name='PDF', ext='.pdf', env=env, translate=translate)

    return rel_path
