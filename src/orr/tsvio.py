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

#--- Constants to map characters

TSV_SOURCE_CHAR_MAP = '\n\t'
TSV_FILE_CHAR_MAP = '␤␉'

PSV_SOURCE_CHAR_MAP = '\n|'
PSV_FILE_CHAR_MAP = '␤¦'

CSV_SOURCE_CHAR_MAP = '\n,'
CSV_FILE_CHAR_MAP = '␤，'

map_tsv_data = str.maketrans(TSV_SOURCE_CHAR_MAP,TSV_FILE_CHAR_MAP)
unmap_tsv_data = str.maketrans(TSV_FILE_CHAR_MAP,TSV_SOURCE_CHAR_MAP)

map_psv_data = str.maketrans(PSV_SOURCE_CHAR_MAP,PSV_FILE_CHAR_MAP)
unmap_psv_data = str.maketrans(PSV_FILE_CHAR_MAP,PSV_SOURCE_CHAR_MAP)

map_csv_data = str.maketrans(CSV_SOURCE_CHAR_MAP,CSV_FILE_CHAR_MAP)
unmap_csv_data = str.maketrans(CSV_FILE_CHAR_MAP,CSV_SOURCE_CHAR_MAP)

#--- Field manipulation routines

def split_line(
        line:str,       # line to be split into fields
        sep:str='\t',   # delimeter separating fields
        trim:str=''     # end characters to strip, default is whitespace
        ) -> List[str]:  # Returns mapped field list
    """
    Removes trailing whitespace, splits fields by the delimiter character,
    then returns a list of strings with unmapped line end and delimiter
    character translations.
    """
    # Optional end of line strip
    if trim != None: line = line.rstrip(trim)

    if sep == '\t':
        mapdata = unmap_tsv_data
    elif sep == '|':
        mapdata = unmap_psv_data
    elif sep == ',':
        mapdata  = unmap_csv_data
    else:
        mapdata = None

    return [f.translate(mapdata) if mapdata else f for f in line.split(sep)]


class Reader:

    """
    The Reader class maintains header, delimiter, linecount and
    routines to read and convert delimited text lines.

    Attributes:
        f:          file object read
        sep:        delimiter separating fields
        header:     list of header strings
        num_columns: number of fields in the header or 0 if not read
        line_num:   line number in file
    """

    def __init__(self,
                 filename:str,       # File to open
                 sep:str=None,      # delimeter separating fields
                 read_header:bool=True ):# Read and save the header
        """
        Creates a tsv reader object. The opened file is passed in as f
        (so a with/as statement can provide a file open context).
        If read_header is true, the first line is assumed to be a
        header. If the sep column separating character is not supplied,
        the characters '\t|,' will be searched in the header line (if
        read) to automatically set the separator, otherwise tab is assumed.
        """

        self.filename = filename
        self.f = open(filename, encoding='utf-8')
        if read_header:
            # The first line is a header with field names and column count
            line = self.f.readline()
            self.line_num = 1   # Reset a line counter
            if sep is None:
                # derive the delimiter from characters in the header
                for c in '\t|,':
                    if c in line:
                        sep = c
                        break
            if sep is None:
                raise RuntimeError(f'no delimiter found in the header of {self.filename}')
            self.header = split_line(line,sep)
            self.num_columns = len(self.header)
        else:
            if sep is None:
                sep = '\t' # default delimiter is a tab
            self.num_columns = 0    # 0 means no column info
            self.line_num = 0   # Reset a line counter

        self.sep = sep

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        """
        Defines an context manager exit to so this can be used in a with/as
        """
        self.f.close()

    def __repr__(self):
        return f'<tsvio.Reader {self.filename}>'

    def convline(self,line:str) -> List[str]:
        """
        Convert a line and return a list of strings for each
        field. If fewer columns are found than defined in the header,
        the list is extended with null strings. (If whitespace is trimmed
        from a line, the missing \t get mapped to null strings.)
        """
        l = split_line(line,self.sep)
        if len(l) < self.num_columns:
            # Extend the list with null strings to match header count
            l.extend([ '' ] * (self.num_columns - len(l)))
        return l

    def readline(self):
        """
        read a line and return the split line list.
        """
        self.line = self.f.readline()
        self.line_num += 1
        return self.convline(self.line)

    def readlines(self):
        """
        Interator to read a file and return the split line lists.
        """
        for line in self.f:
            self.line = line
            self.line_num += 1
            yield self.convline(line)

    def readdict(self):
        """
        Iterator to return a dict of values by header field name
        """
        for l in self.readlines():
            yield zip(self.header,l)

def overlay_tsv_data(
    filename:str,       # File to open
    obj_by_id:dict,     # Dict of objects to overlay by id
    id_attr:str,        # Name of the id attribute in the data file
    process_attrs:dict, # Dict of processing routines by source attr
    map_attrs:dict=None): # Optional dictionary mapping source->target attrs
    """
    The overlay_tsv_data routine can open and load a TSV file,
    inserting attributes into an object identified by the id_attr.
    """
    with Reader(filename) as reader:
        # Compute the index of the id_attr
        try:
            id_attr_index = reader.header.index(id_attr)
        except ValueError:
            raise RuntimeError(f'id attribute {id_attr} not found in {filename}')
        # Loop over all rows in the file
        for cols in reader.readlines():
            # Retrieve the object to set from the id_attr_index column
            try:
                obj = obj_by_id[cols[id_attr_index]]
            except KeyError:
                raise RuntimeError(f"object with id {cols[id_attr_index]} not found in {filename}:{reader.line_num}")

            # For each column, set an attribute in the obj
            for i in range(reader.num_columns):
                attr_name = reader.header[i]
                # Skip if we do not have a processing routine for this attr
                if attr_name not in process_attrs: continue

                # Invoke the processing routine to convert the string
                v = process_attrs[attr_name](obj,cols[i])

                # The attribute name can be changed from the input file
                if map_attrs and attr_name in map_attrs:
                    attr_name = map_attrs[attr_name]
                setattr(obj, attr_name, v)


