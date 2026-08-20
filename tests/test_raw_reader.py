import json

import pytest

from storage.raw_reader import read_raw_comment_pages


def test_read_raw_comment_pages_preserves_input_path_order(tmp_path):
    first_document = {
        "video_id": "video-1",
        "page_number": 1,
        "ingested_at": "2026-08-20T09:30:00+00:00",
        "raw_response": {"items": [{"text": "第一頁留言"}]},
    }
    second_document = {
        "video_id": "video-1",
        "page_number": 2,
        "ingested_at": "2026-08-20T09:30:00+00:00",
        "raw_response": {"items": [{"text": "Second page"}]},
    }
    first_path = tmp_path / "page_0001.json"
    second_path = tmp_path / "page_0002.json"

    for path, document in (
        (first_path, first_document),
        (second_path, second_document),
    ):
        with path.open("w", encoding="utf-8") as output_file:
            json.dump(document, output_file, ensure_ascii=False)

    raw_documents = read_raw_comment_pages(
        [second_path, first_path]
    )

    assert raw_documents == [second_document, first_document]


def test_read_raw_comment_pages_raises_for_invalid_json(tmp_path):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not valid JSON", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        read_raw_comment_pages([invalid_path])
