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


def split_line(
    line:str,       # line to be split into fields
) -> List[str]:  # Returns mapped field list
    """
    Removes trailing whitespace, splits fields by the tab character,
    then returns a list of strings with unmapped line end and delimiter
    character translations.
    """
    line = line.rstrip()

    return [f.translate(unmap_tsv_data) for f in line.split(TAB_CHAR)]


class TSVLines:

    def __init__(self, lines, read_header=True, path=None):
        """
        Args:
          lines: an iterator of lines.
          path: the path for logging purposes.
        """
        self.lines = lines

        self.headers = None
        self.line_num = 0
        self.line = None
        self.read_header = read_header

    def __repr__(self):
        return f'<TSVLines: {self.path!r}>'

    def _store_line(self, line):
        self.line_num += 1
        self.line = line.rstrip()

    def _parse_line(self, line:str) -> List[str]:
        """
        Convert a line and return a list of strings for each
        field. If fewer columns are found than defined in the header,
        the list is extended with null strings. (If whitespace is trimmed
        from a line, the missing \t get mapped to null strings.)
        """
        parts = split_line(line)
        if len(parts) < self.num_columns:
            # Extend the list with null strings to match header count
            parts.extend([''] * (self.num_columns - len(parts)))

        return parts

    @property
    def num_columns(self):
        return len(self.headers)

    def __iter__(self):
        lines = self.lines

        # First read the header line if configured to do so.
        if self.read_header:
            # The first line is a header with field names and column count
            line = next(lines)
            self._store_line(line)
            self.headers = split_line(line)

        yield self.headers

        # Read the remaining lines.
        for line in lines:
            self._store_line(line)
            yield self._parse_line(line)


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

    def __init__(self, path:str, read_header:bool=True):
        """
        Creates a tsv reader object. The opened file is passed in as f
        (so a with/as statement can provide a file open context).
        If read_header is true, the first line is assumed to be a
        header. If the sep column separating character is not supplied,
        the characters '\t|,' will be searched in the header line (if
        read) to automatically set the separator, otherwise tab is assumed.

        Args:
          path: the path to open, as a path-like object.
        """
        self.path = path
        self.read_header = read_header

    def __enter__(self):
        path = self.path
        stream = open(path, encoding=UTF8_ENCODING)
        self.stream = stream

        return TSVLines(stream, path=path)

    def __exit__(self, type, value, traceback):
        """
        Defines an context manager exit to so this can be used in a with/as
        """
        self.stream.close()
        self.stream = None

    def __repr__(self):
        return f'<TSVReader {self.path}>'
