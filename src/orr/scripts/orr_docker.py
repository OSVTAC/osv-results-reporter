# -*- coding: utf-8 -*-
#
# Open Source Voting Results Reporter (ORR) - election results report generator
# Copyright (C) 2019  Chris Jerdonek
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
Entry-point script to run ORR using Docker.
"""

import argparse
import logging
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from subprocess import Popen
import sys
from tempfile import TemporaryDirectory
from textwrap import dedent

import orr.scripts.scriptcommon as scriptcommon
from orr.scripts.scriptcommon import InputDirs
from orr.utils import UTF8_ENCODING


_log = logging.getLogger(__name__)

DOCKER_OUTPUT_PARENT = '/tmp/orr'
DOCKER_OUTPUT_DIR_NAME = 'output'

DESCRIPTION = """\
Wrapper script to run orr in a Docker container.
"""


def parse_args():
    """
    Parse sys.argv and return a Namespace object.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                    formatter_class=argparse.RawDescriptionHelpFormatter)

    scriptcommon.add_common_args(parser)

    source_dir_help = dedent("""\
    the directory containing the Dockerfile to build.  Normally this should
    be the directory to the repository root of a clone of the ORR repository.
    Defaults to the current working directory (".").
    """)
    parser.add_argument('--source-dir', metavar='DIR', help=source_dir_help)

    parser.add_argument('--skip-docker-build', action='store_true',
        help='whether to skip building the Docker image.')
    parser.add_argument('--orr_args', nargs=argparse.REMAINDER,
        help='extra arguments to pass to the underlying orr command.')

    ns = parser.parse_args()

    return ns


def run_subprocess(args, check=True, desc=None, **kwargs):
    command = ' '.join(shlex.quote(arg) for arg in args)
    if desc is None:
        desc = ''
    else:
        desc = f' ({desc})'
    msg = dedent(f"""\
    running command{desc}:

        $ {command}
    """)
    _log.info(msg)
    # Redirect stderr to stdout, and capture stdout.
    with Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
               encoding=UTF8_ENCODING, **kwargs) as proc:
        while True:
            line = proc.stdout.readline()
            if not line:
                # Then the subprocess is done.
                break
            # Write the output to stderr so as not to interfere with stdout.
            sys.stderr.write(line)

        # Wait for the child process to terminate.
        proc.wait()

        if check and proc.returncode:
            msg = f'subprocess ended with return code: {proc.returncode}'
            raise RuntimeError(msg)


def make_docker_path(rel_path):
    """
    Return an absolute path inside the Docker container.

    Args:
      rel_path: a path relative to the container's app directory.
    """
    return str(Path('/app') / rel_path)


def build_docker_image(source_dir, tag):
    msg = dedent(f"""\
    building Docker image:
             tag: {tag}
      source_dir: {source_dir}
    """)
    _log.info(msg)

    # Convert the path object to a string.
    args = ['docker', 'build', '-t', tag, str(source_dir)]
    run_subprocess(args)


def remove_container(container_name):
    args = ['docker', 'rm', container_name]
    # Don't pass check=True to prevent an error if the container doesn't exist.
    run_subprocess(args, check=False)


def copy_to_temp(temp_dir, source_dir, rel_dest_dir, desc):
    dest_dir = temp_dir / rel_dest_dir

    msg = dedent(f"""\
    copying directory to temp directory:

          desc: {desc}
       src_dir: {source_dir}
      dest_dir: {dest_dir}
    """)
    _log.info(msg)
    shutil.copytree(source_dir, dest_dir)


def copy_input_dirs(temp_dir, input_dirs):
    """
    Return: (rel_root_dir, rel_input_dirs)
      rel_root_dir: a path relative to the temp directory, as a Path object.
      rel_input_dirs: input paths relative to the temp directory, as an InputDirs
        object.
    """
    input_data_dir, results_dir, template_dir, extra_template_dirs = input_dirs

    rel_input_root = Path('input')
    rel_data_dir = rel_input_root / 'input_data'
    rel_template_dir = rel_input_root / 'template'
    # This is the parent directory for the extra template directories.
    rel_extra_templates_dir = rel_input_root / 'extra_templates'
    rel_extra_template_dirs = []

    dir_infos = [
        (input_data_dir, rel_data_dir, 'input data directory'),
        (template_dir, rel_template_dir, 'template directory'),
    ]
    if results_dir is None:
        rel_results_dir = None
    else:
        rel_results_dir = rel_input_root / 'input_results_data'
        info = (results_dir, rel_results_dir, 'input results directory')
        dir_infos.append(info)

    extra_count = len(extra_template_dirs)
    for i, extra_template_dir in enumerate(extra_template_dirs, start=1):
        rel_extra_template_dir = rel_extra_templates_dir / f'extra-{i}'
        dir_info = (
            extra_template_dir, rel_extra_template_dir,
            f'extra template directory ({i} of {extra_count})'
        )
        dir_infos.append(dir_info)
        rel_extra_template_dirs.append(rel_extra_template_dir)

    for source_dir, rel_dest_dir, desc in dir_infos:
        copy_to_temp(temp_dir, source_dir=source_dir, rel_dest_dir=rel_dest_dir,
            desc=desc)

    rel_input_dirs = InputDirs(data_dir=rel_data_dir, results_dir=rel_results_dir,
                               template_dir=rel_template_dir,
                               extra_template_dirs=rel_extra_template_dirs)

    return (rel_input_root, rel_input_dirs)


def make_dockerfile_text(base_image, rel_input_root):
    docker_input_dir = make_docker_path(rel_input_root)
    rel_input_root = str(rel_input_root)
    # Docker requires that the COPY <dest> end in a slash when the
    # destination path is a directory.
    if not docker_input_dir.endswith('/'):
        docker_input_dir += '/'

    text = dedent(f"""\
    FROM {base_image}

    COPY {rel_input_root} {docker_input_dir}
    """)

    return text


def create_dockerfile(base_image, temp_dir, rel_input_root):
    dockerfile_text = make_dockerfile_text(base_image, rel_input_root=rel_input_root)
    dockerfile_path = temp_dir / 'Dockerfile'
    dockerfile_path.write_text(dockerfile_text)


def build_temp_image(base_image, input_dirs, container, temp_tag):
    """
    Args:
      input_dirs: the input directories, as an InputDirs object.
      container: the name to give the container being created.
    """
    with TemporaryDirectory(prefix='orr_builder_') as temp_dir:
        temp_dir = Path(temp_dir)
        rel_input_root, rel_input_dirs = copy_input_dirs(temp_dir, input_dirs=input_dirs)
        create_dockerfile(base_image, temp_dir=temp_dir, rel_input_root=rel_input_root)
        build_docker_image(temp_dir, tag=temp_tag)

    return (rel_input_root, rel_input_dirs)


def run_orr(orr_args, image_name, container):
    """
    Args:
      image_name: the name of the Docker image to run.
      container: the name to give the container being created.
    """
    input_dir = Path('submodules/osv-sample-data/2018-11-06/out-orr/')
    input_dir = input_dir.resolve()
    docker_input_dir = '/app/input-dir'

    args = [
        'docker', 'run', '--name', container, image_name,
        # These are the arguments to pass to orr.
        '--output-parent', DOCKER_OUTPUT_PARENT,
        '--output-subdir', DOCKER_OUTPUT_DIR_NAME,
    ]
    args.extend(orr_args)
    run_subprocess(args)


def copy_output_dir(output_dir, container_name):
    """
    Copy the build output directory from the container to the host.

    Args:
      output_dir: the output directory on the host machine (as opposed to
        inside the Docker container).
    """
    # Append a "." so the contents of the directory will be copied,
    # rather than the directory itself.
    src_dir = os.path.join(DOCKER_OUTPUT_PARENT, DOCKER_OUTPUT_DIR_NAME, '.')
    docker_src = f'{container_name}:{src_dir}'

    output_parent_dir = output_dir.parent
    if not output_parent_dir.exists():
        _log.info('creating output parent directory: {output_parent_dir}')
        output_parent_dir.mkdir()

    desc = 'copying build output from container to host'
    # Convert the Path object to a string.
    args = ['docker', 'cp', docker_src, str(output_dir)]
    run_subprocess(args, desc=desc)


def make_base_orr_args(ns, options):
    orr_args = ns.orr_args or []

    if options.log_level <= logging.DEBUG:
        orr_args.append('--debug')
    elif options.log_level <= logging.INFO:
        orr_args.append('--verbose')

    return orr_args


def main():
    ns = parse_args()

    options = scriptcommon.parse_common_args(ns, default_log_level=logging.INFO)

    build_time = options.build_time
    log_level = options.log_level
    input_dirs = options.input_dirs
    output_dir = options.output_dir

    logging.basicConfig(level=log_level)

    skip_docker_build = ns.skip_docker_build
    source_dir = ns.source_dir

    if source_dir is None:
        source_dir = os.curdir

    source_dir = Path(source_dir)
    if not (source_dir / 'Dockerfile').exists():
        resolved_path = source_dir.resolve()
        raise RuntimeError(
            f'--source-dir does not contain a file "Dockerfile": {source_dir} '
            f'(resolves to: {resolved_path})'
        )

    image_tag = 'orr'
    container_name = 'orr_builder'

    if skip_docker_build:
        _log.info('skipping building Docker image')
    else:
        build_docker_image(source_dir, tag=image_tag)

    remove_container(container_name)

    temp_tag = 'orr_builder_temp'
    rel_input_root, input_dirs = build_temp_image(image_tag, input_dirs=input_dirs,
                                    container=container_name, temp_tag=temp_tag)

    orr_args = make_base_orr_args(ns, options)

    # Add the input directory arguments.
    orr_args.extend(('--input-dir', str(input_dirs.data_dir)))
    if input_dirs.results_dir is not None:
        orr_args.extend(('--input-results-dir', str(input_dirs.results_dir)))

    # Add the template directory arguments.
    orr_args.extend(('--template-dir', str(input_dirs.template_dir)))
    extra_template_dirs = input_dirs.extra_template_dirs
    if extra_template_dirs:
        orr_args.append('--extra-template-dirs')
        orr_args.extend(str(extra_dir) for extra_dir in extra_template_dirs)

    run_orr(orr_args, image_name=temp_tag, container=container_name)

    copy_output_dir(output_dir, container_name=container_name)

    output_data = scriptcommon.print_result(output_dir, build_time=build_time)

    _log.info(f'done: {image_tag}')
