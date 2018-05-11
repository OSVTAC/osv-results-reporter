# orr - OEMS HTML/PDF/XLS report generator for election data

Initial checkin. Documentation TODO.

See doc/orr.md for a description of the orr application
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

* Run the program:

```
$ ./src/orr.py -h
$ ./src/orr.py -v -c sampledata/config-orr.yml -j sampledata/results.json test.html
```

* See doc dir
