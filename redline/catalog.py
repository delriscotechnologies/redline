from importlib.resources import files

from .models import parse_json


def list_techniques():
    return parse_json(files("redline").joinpath("catalog.json").read_text(encoding="utf-8"))


def get_technique(technique_id):
    for entry in list_techniques():
        if entry["id"] == technique_id:
            return entry
    raise ValueError(f"unknown catalog entry: {technique_id}")
