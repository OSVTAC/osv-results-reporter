FROM python:3.6-slim

# Put all of our files in an application-specific directory.
WORKDIR app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY src/ src/

ENTRYPOINT ["python", "src/orr.py"]
