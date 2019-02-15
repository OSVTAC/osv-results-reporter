FROM python:3.6-slim

RUN apt-get clean && apt-get update \
    && apt-get install -y locales

# Upgrade to the latest pip.
RUN pip install pip==18.1

# Put all of our files in an application-specific directory.
WORKDIR /usr/src/app

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

COPY debian/ debian/

# Install locales.
RUN cp debian/locale.gen /etc/locale.gen \
    && locale-gen \
    # Display all installed locales to simplify troubleshooting.
    && locale -a

COPY sampledata/ sampledata/
COPY scripts/ scripts/
COPY src/ src/
COPY templates/ templates/

# Add a marker file so we can check from within Python whether we
# are running inside the Docker container.
RUN touch src/orr/in_docker.py

# Installing via pip lets us invoke the program using the console-script
# entry-point "orr" defined in setup.py.
RUN pip install ./src

# Pass --output-fresh-parent as a check to ensure that the parent
# of the output directory is empty when running using Docker.
# This way we know we're copying only one directory when we run--
# $ docker cp orr_builder:/app/_build/. _build
ENTRYPOINT ["orr", "--output-fresh-parent"]
