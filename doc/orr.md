# ORR -  HTML/PDF/XLS Election Results Generator

## Introduction

ORR is designed to be able to create a variety of different HTML, PDF,
XML, JSON, XLS, etc. files based on user-editable templates (currently
Jinja2 templates). Templates can be constructed to represet a variety
of summary and detailed results data files.

PDF files are created using HTML5 as a rendering engine using HTML
templates that include CSS with print-media pagination. Templates
can be used to create XML and JSON, but some software utilities and
filters can be used to simplify XML or JSON specific notations.

Users can customize the output data generated via configuration file
settings as well as editing or creating new templates. Software plug-ins
can be added to support new data models or data transformations if
needed.

[TODO: Figure out how XLS files should be created and user
customized.]

## Configuration Files

[More TODO] The file `config-orr.yml` in the current directory is
read with information on how ORR is tailored to the particular
installation, information about the locality and Election Administration
to be added to election data, information about election dates and
definitions, and customization of the output files to be generated
with the data sources and templates to be used.

The `config-orr.yml` can be edited by hand as needed using the
configuration file documentation. In the future, some GUI or
commands may be added to edit config files and setup new elections
with election-specific configurations.

The `-c` command line option can be used to specify a different
configuration file to load. Each configuration file can include
the `include_config:` option, that provides one or more additional
files to load, each name separated by space or newlines. Each
subsequent configuration file read can provide default definitions
not already set. Using multiple configuration files allows election-specific
definitions to be combined with a site-wide definitions.

Configuration file entries can be used to set template variables
as defined in the documentation.

## Command Line Arguments

When `orr` is invoked, the command line arguments specify a template
file to be processed and optional output file. If no output file is given,
the output file will be the same name as the template file.

If the `orr_out_dir:` configuration file option is defined, the
output file name will be relative to that directory if not an
absolute path.

Templates are located by scanning a search path defined by the
`orr_template_paths:` configuration file setting, or if not
defined, `../templates` will be assumed.

Specific input data to be included can be specified with optional
command line arguments. The `-j jsonfilename` option defines the name
of a json data file to be loaded into the template globals. The
`-y yamlfilename` can load yaml data. \[Note: yaml and json must
be a dictionary (set of named values), and cannot contain the advanced
yaml object notation.]

The `-j` or `-y` options can be repeated to overlay data from multiple
files.






