# Jinja2 Templates

This document describes our use of Jinja2 templates, including documenting
our custom tags.

TODO: add more detail.

## Environment filters

* `output_file_uri(rel_path)`

## Context filters

* `translate(context, label)`

## Environment functions

* `create_pdf(rel_path, contests, title=None)`

* `create_tsv_files(rel_dir, contests)`

* `create_xlsx(rel_path, contests)`

## Context functions

* `subtemplate(template_name, file_name)`
