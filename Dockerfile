FROM python:3.6-slim

# Put all of our files in an application-specific directory.
WORKDIR app

# Only copy the requirements file before installing requirements so that
# updating our Python code doesn't force the requirements to be reinstalled.
COPY src/requirements.txt src/

# In our Docker image, we want to install pinned requirements for
# reproducibility, so install the concrete requirements prior to installing
# from setup.py.
#   Consequently, installing from setup.py below shouldn't result in
# installing any additional packages aside from the orr project itself.
# This is because pip should find already installed all the requirements
# listed in install_requires.
RUN pip install -r src/requirements.txt

COPY sampledata/ sampledata/
COPY src/ src/
COPY templates/ templates/

# Installing via pip lets us invoke the program using the console-script
# entry-point "orr" defined in setup.py.
RUN pip install ./src

# Pass --output-fresh-parent as a check to ensure that the parent
# of the output directory is empty when running using Docker.
# This way we know we're copying only one directory when we run--
# $ docker cp orr_builder:/app/_build/. _build
ENTRYPOINT ["orr", "--output-fresh-parent"]
