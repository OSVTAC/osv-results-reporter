# orr - OEMS HTML/PDF/XLS report generator for election data

Initial checkin. Documentation TODO.

See [`doc/orr.md`](doc/orr.md) for a description of the orr application
and how it can be used to create collections of html/pdf/xml/xls
files from election data.

Following an election orr can be used to create results summary
pages on election night, and detailed Statement of Vote reports
with precinct detail on each contest.

To install:

* Requires python version 3.6

```
$ pip install -e ./src
```

To run:

```
$ orr -h
```

* The templates dir has named jinja templates

```
$ orr -v --json sampledata/results.json --output-dir html
```

  The above writes the output to the directory `_build`.

* Open `_build/html/index.html` in a browser.

* See doc dir

## Docker (experimental)

```
$ docker build -t orr .
$ docker run orr -h
```

To render a template directory to the build directory using Docker:

```
$ docker build -t orr . \
    && docker rm orr_builder; echo "removed container: orr_builder" \
    && docker run --name orr_builder orr --json sampledata/results.json \
    && docker cp orr_builder:/app/_build/. _build
```

TODO: change the above to a bash script?

## Copyright

Copyright (C) 2018  Carl Hage

Copyright (C) 2018  Chris Jerdonek


## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.


## Contact

The authors can be reached at--

* Carl Hage <ch@carlhage.com>
* Chris Jerdonek <chris.jerdonek@gmail.com>
