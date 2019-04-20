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

from pathlib import Path

import jinja2
from jinja2 import Environment, FileSystemLoader
from jinja2.utils import Namespace

import orr.templating as templating
import orr.utils as utils
from orr.utils import ENGLISH_LANG, SHA256SUMS_FILENAME


def create_jinja_env(output_dir, template_dirs=None, deterministic=None):
    """
    Create and return the Jinja2 Environment object.

    Args:
      output_dir: a path-like object.
      deterministic: for deterministic PDF generation.  Defaults to False.
    """
    if template_dirs is None:
        template_dirs = []

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

    env.globals.update(options=options,
        current_page_link=templating.current_page_link,
        create_pdf=templating.create_pdf,
        create_tsv_files=templating.create_tsv_files,
        create_xlsx=templating.create_xlsx,
        make_translator=templating.make_translator,
        subtemplate=templating.subtemplate,
        SHASUMS_PATH=SHA256SUMS_FILENAME,
    )

    filters = dict(
        output_file_uri=templating.output_file_uri,
        format_date=templating.format_date,
        format_date_medium=templating.format_date_medium,
        secure_hash=templating.secure_hash,
        translate=templating.translate,
        format_path=templating.format_path,
        contest_path_template=templating.contest_path_template,
        to_json=templating.to_json,
        to_xml=templating.to_xml,
        to_xml_attr=templating.to_xml_attr,
        format_number=utils.format_number,
        compute_percent=utils.compute_percent,
        format_percent=utils.format_percent,
        format_percent2=utils.format_percent2,
    )
    tests = {}

    env.filters.update(filters)
    env.tests.update(tests)

    return env
