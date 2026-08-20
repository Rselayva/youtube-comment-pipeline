import json
from pathlib import Path


def read_raw_comment_pages(paths: list[Path]) -> list[dict]:
    raw_documents = []

    for path in paths:
        with path.open(encoding="utf-8") as input_file:
            raw_documents.append(json.load(input_file))

    return raw_documents
