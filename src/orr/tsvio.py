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
Subroutine definitions and reader class to process delimited text files.
Data represented in unquoted tab (\t), pipe (|), or comma-delimited files
can be read and parsed using routines in this module. The reader can
optionally automatically determine the delimiter used, and save the
header array. No quotes are used, so to represent newlines and the
delimiter character, any newline or delimiter characters in field strings
are mapped to/from UTF-8 substitutes.

When reading lines and splitting into a string array, trimmed delimiters
at the end of the line will read as null strings for the full width
defined by a header line.

A TSVReader object maintains a context with delimiter, line number,
number of columns, and header name array.

This module does not use general libraries to avoid unneeded complexity.

TSV writing capability will be added later.
"""

from typing import Dict, Tuple, List, TextIO

from orr.utils import UTF8_ENCODING


TAB_CHAR = '\t'

TSV_SOURCE_CHAR_MAP = '\n\t'
TSV_FILE_CHAR_MAP = '␤␉'

map_tsv_data = str.maketrans(TSV_SOURCE_CHAR_MAP,TSV_FILE_CHAR_MAP)
unmap_tsv_data = str.maketrans(TSV_FILE_CHAR_MAP,TSV_SOURCE_CHAR_MAP)


def split_line(line):
    """
    Removes trailing whitespace, splits fields by the tab character,
    then returns a list of strings with unmapped line end and delimiter
    character translations.
    """
    line = line.rstrip()

    return [f.translate(unmap_tsv_data) for f in line.split(TAB_CHAR)]


class TSVLines:

    def __init__(self, lines, path=None, convert=None):
        """
        Args:
          lines: an iterator of lines.
          path: the path for logging purposes.
          convert: a function to convert `row[2:]` for each row after
            the header row.
        """
        if convert is None:
            convert = lambda row: row

        assert convert is not None
        self.lines = lines
        self.path = path
        self.convert = convert

        self.headers = None
        self.line_num = 0
        self.line = None

    def __repr__(self):
        return f'<TSVLines: {self.path!r} convert={self.convert!r}>'

    @property
    def num_columns(self):
        return len(self.headers)

    def _store_line(self, line):
        self.line_num += 1
        self.line = line.rstrip()

    def _split_line(self, line):
        self._store_line(line)

        return split_line(line)

    def __iter__(self):
        lines = self.lines

        # The first line is a header with field names and column count
        line = next(lines)

        headers = self._split_line(line)
        # TODO: remove this debug check.
        if headers[0] not in ('area_id',):
            raise RuntimeError(f'unexpected header row: {headers!r}')

        self.headers = headers

        # Yield the headers first.
        yield headers

        # Read the remaining lines.
        for line in lines:
            fields = self._split_line(line)

            if len(fields) < self.num_columns:
                # Extend the list with null strings to match header count
                fields.extend((self.num_columns - len(fields)) * [''])
            elif len(fields) > self.num_columns:
                raise RuntimeError(
                    f'too many columns in line {self.line_num!r}:\n'
                    f' expected {self.num_columns} got {len(fields)}\n'
                    f' {self}\n'
                    f' line: {line!r}'
                )

            yield fields

    def _make_group_id_rows(self, rows, start):
        """
        Yields triples: (line_number, group_id, remaining)
          line_number: the line number, starting with the given `start`.
          group_id: a composite reporting group id, as a 2-tuple
            (area_id, voting_group_id).
          remaining: the remaining values, as a list of strings.
        """
        for line_number, row in enumerate(rows, start=start):
            try:
                group_id = tuple(row[:2])
                remaining = self.convert(row[2:])
            except Exception:
                msg = (
                    f'parsing failed at line {line_number}:\n'
                    f'  line: {self.line!r}\n'
                    f' split: {row}'
                )
                raise RuntimeError(msg)

            yield (line_number, group_id, remaining)

    def get_parsed_rows(self):
        """
        Returns: (headers, parsed_rows)
          headers: the headers, as a list.
          parsed_rows: an iterator of 3-tuples (line_number, group_id, remaining).
        """
        rows = iter(self)
        headers = next(rows)

        parsed_rows = self._make_group_id_rows(rows, start=2)

        return (headers, parsed_rows)


class TSVReader:

    """
    The TSVReader class maintains header, delimiter, linecount and
    routines to read and convert delimited text lines.

    Attributes:
        f:          file object read
        sep:        delimiter separating fields
        header:     list of header strings
        num_columns: number of fields in the header or 0 if not read
        line_num:   line number in file
    """

    def __init__(self, path, convert):
        """
        Creates a tsv reader object. The opened file is passed in as f
        (so a with/as statement can provide a file open context).

        Args:
          path: the path to open, as a path-like object.
          convert: a function to convert `row[2:]` for each row after
            the header row.
        """
        self.convert = convert
        self.path = path

    def __enter__(self):
        path = self.path
        stream = open(path, encoding=UTF8_ENCODING)
        self.stream = stream

        return TSVLines(stream, path=path, convert=self.convert)

    def __exit__(self, type, value, traceback):
        """
        Defines an context manager exit to so this can be used in a with/as
        """
        self.stream.close()
        self.stream = None

    def __repr__(self):
        return f'<TSVReader {self.path}>'
