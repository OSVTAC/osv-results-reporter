# Open Source Voting Results Reporter (ORR)

[![Build Status](https://travis-ci.org/OSVTAC/osv-results-reporter.svg?branch=master)](https://travis-ci.org/OSVTAC/osv-results-reporter)

## Election results report generator (HTML/PDF/XLS)

See [`doc/orr.md`](doc/orr.md) for a description of the orr application
and how it can be used to create collections of html/pdf/xml/xls
files from election data.

Following an election orr can be used to create results summary
pages on election night, and detailed Statement of Vote reports
with precinct detail on each contest.

This is an official project of San Francisco's [Open Source Voting System
Technical Advisory Committee][osvtac] (OSVTAC).


### To install

* Requires python version 3.6

```
$ pip install -e ./src
```


### To run

For command-line help:

```
$ orr -h
```

For a small HTML example demonstrating much of the functionality:

```
$ orr -v --input-dir sampledata/minimal-test \
      --template-dir templates/demo-template \
      --extra-template templates/demo-template/extra \
      --output-subdir minimal-test
```

Then open `_build/minimal-test/index.html` in a browser. The example above
includes:

* 3 contests
* 4 languages
* a details page for each contest
* a PDF "Statement of Vote"

This example can also be seen published on the web here:
https://osvtac.github.io/osv-results-demo/

The `templates` directory contains more sample Jinja2 templates.

See the `doc` directory for more info.


### To run tests

The following runs the test suite, including an "end-to-end" test of a
non-trivial template directory (the "demo-template" one):

```
$ python -m unittest discover orr
```

To run an individual test, e.g.:

```
$ python -m unittest orr orr.tests.test_utils.UtilsModuleTest.test_compute_percent
```

For available options for running tests:

```
$ python -m unittest -h
```


### To update the end-to-end test

To regenerate the test expectation for the end-to-end test and see
a diff with what is currently in source control:

```
$ ./scripts/update-test-expectation.sh
```


## Docker (experimental)

```
$ orr-docker -h
```

To render a template directory to the build directory using Docker:

```
$ orr-docker --input-dir sampledata/minimal-test \
        --template-dir templates/demo-template \
        --extra-template templates/demo-template/extra \
        --output-subdir minimal-test
```

To run tests:

```
$ docker build -t orr . \
    && docker run --entrypoint python orr -m unittest discover orr
```


TODO: change the above to a bash script?

## History

Work on this project started informally around the beginning of May 2018.
The [Open Source Voting System Technical Advisory Committee][osvtac]
(OSVTAC) adopted it as an official project by unanimous vote at its
June 14, 2018 meeting.  The source code was first made public on June 18,
2018 under OSVTAC's GitHub account.

Note that because OSVTAC is an official meeting body of the City and
County of San Francisco, members must follow San Francisco's [Sunshine
Ordinance][sunshine-ordinance] and California's [Brown Act][brown-act].
Thus, members are limited in the extent to which they can collaborate
with one another outside of meetings.


## Copyright

Copyright (C) 2018  Carl Hage

Copyright (C) 2018, 2019  Chris Jerdonek


## License

This file is part of Open Source Voting Results Reporter (ORR).

ORR is free software: you can redistribute it and/or modify
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


[brown-act]: https://en.wikipedia.org/wiki/Brown_Act
[osvtac]: https://osvtac.github.io/
[sunshine-ordinance]: https://www.sfcityattorney.org/good-government/sunshine/sunshine-ordinance/
