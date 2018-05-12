# orr - OEMS HTML/PDF/XLS report generator for election data

Initial checkin. Documentation TODO.

See [`doc/orr.md`](doc/orr.md) for a description of the orr application
and how it can be used to create collections of html/pdf/xml/xls
files from election data.

Following an election orr can be used to create results summary
pages on election night, and detailed Statement of Vote reports
with precinct detail on each contest.

To run:

* Requires python version 3.6

```
$ pip install -r requirements.txt
```

* Put src/orr.py in search path or reference explicitly

* The templates dir has named jinja templates

* Run the program (which writes the output to the directory `_build`):

```
$ ./src/orr.py -h
$ ./src/orr.py -v --json sampledata/results.json
```

* Open `_build/index.html` in a browser.

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
