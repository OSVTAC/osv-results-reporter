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
Contains functions to help configure ORR.
"""

import functools
from pathlib import Path

import jinja2
from jinja2 import contextfilter, Environment, FileSystemLoader
from jinja2.utils import Namespace

import orr.templating as templating
import orr.utils as utils
from orr.utils import ENGLISH_LANG, SHASUMS_PATH


def create_jinja_env(output_dir, template_dirs=None, translation_data=None,
    deterministic=None, gzip_path=None, skip_pdf=False):
    """
    Create and return the Jinja2 Environment object.

    Args:
      output_dir: a path-like object.
      translation_data: optionally, the dict of data read from the template
        directory's `translations.json`.
      deterministic: for deterministic PDF generation.  Defaults to False.
      gzip_path: the path the tar.gz file will be written to.
      skip_pdf: whether to skip PDF generation.  Defaults to False.
    """
    if template_dirs is None:
        template_dirs = []
    if translation_data is None:
        translation_data = {}

    env = Environment(
        loader=FileSystemLoader(template_dirs),
        autoescape=jinja2.select_autoescape(['html', 'xml']),
        # Enable the expression-statement extension:
        # http://jinja.pocoo.org/docs/2.10/templates/#expression-statement
        extensions=['jinja2.ext.do'],
        # Remove excess whitespace with lstrip_blocks and trim_blocks.
        lstrip_blocks=True,
        trim_blocks=True,
    )

    # Using a Namespace object lets us change the context inside a
    # template, e.g. by calling "{% set options.lang = lang %}" from
    # within a with block.  Doing this lets us access the option values
    # from within a custom filter, without having to pass the option
    # values explicitly.
    options = Namespace()
    # Jinja requires you to set using index rather than attribute notation.
    options['output_dir'] = Path(output_dir)
    # Initialize with a default of English.
    options['lang'] = ENGLISH_LANG
    options['deterministic'] = deterministic
    options['skip_pdf'] = skip_pdf

    languages = translation_data.get('languages')
    phrases = translation_data.get('translations')

    env.globals.update(options=options,
        current_page_link=templating.current_page_link,
        create_pdf=templating.create_pdf,
        create_tsv_files=templating.create_tsv_files,
        create_xlsx=templating.create_xlsx,
        get_relative_href=templating.get_relative_href,
        home_href=templating.get_home_href,
        make_translator=templating.make_translator,
        subtemplate=templating.subtemplate,
        # Convert the Path objects to strings.
        gzip_path=str(gzip_path),
        shasums_path=str(SHASUMS_PATH),
        languages_data=languages,
        phrases_data=phrases,
    )
    # We need to update by index since "raise" is a Python keyword.
    env.globals['raise'] = templating.debug_raise

    translate_phrase = contextfilter(functools.partial(templating.translate_phrase, phrases=phrases))

    filters = dict(
        output_file_uri=templating.output_file_uri,
        format_date=templating.format_date,
        format_date_medium=templating.format_date_medium,
        format_datetime=templating.format_datetime,
        secure_hash=templating.secure_hash,
        lang_to_phrase_id=templating.lang_to_phrase_id,
        # Using "TD" and "TP" makes it easier to find all usages in our
        # template code.
        TD=templating.translate_data,
        TP=translate_phrase,
        default_contest_path=templating.default_contest_path,
        format_number=utils.format_number,
        compute_fraction=utils.compute_fraction,
        compute_percent=utils.compute_percent,
        format_percent=utils.format_percent,
        format_percent2=utils.format_percent2,
        nobreak=utils.make_non_breaking,
        to_element_id=templating.to_element_id,
        to_fragment=utils.to_fragment,
    )
    tests = {}

    env.filters.update(filters)
    env.tests.update(tests)

    return env
