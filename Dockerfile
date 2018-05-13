FROM python:3.6-slim

# Put all of our files in an application-specific directory.
WORKDIR app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY sampledata/ sampledata/
COPY src/ src/
COPY templates/ templates/

# Pass --output-fresh-parent as a check to ensure that the parent
# of the output directory is empty when running using Docker.
# This way we know we're copying only one directory when we run--
# $ docker cp orr_builder:/app/_build/. _build
ENTRYPOINT ["python", "src/orr", "--output-fresh-parent"]
