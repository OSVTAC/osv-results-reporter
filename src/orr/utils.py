import json


def read_json(path):
    with open(path) as f:
        data = json.load(f)

    return data
