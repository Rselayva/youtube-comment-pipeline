import json

import pytest

from enrichment.topic_keywords import load_topic_keyword_dictionary


def make_dictionary() -> dict:
    return {
        "schema_version": 1,
        "dictionary_version": "test_topics_v1",
        "description": "Test topic dictionary.",
        "topics": [
            {
                "topic_id": "topic_a",
                "display_name": "Topic A",
                "keywords": ["keyword a"],
            }
        ],
    }


def write_dictionary(tmp_path, raw_dictionary):
    path = tmp_path / "topic_keywords.json"
    path.write_text(
        json.dumps(raw_dictionary, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_load_topic_keyword_dictionary_has_only_initial_topic_ids():
    topics = load_topic_keyword_dictionary()

    assert topics.schema_version == 1
    assert topics.dictionary_version == "comment_topics_v1"
    assert tuple(topics.topics_by_id) == (
        "vocal",
        "dance",
        "visual",
    )
    assert topics.keyword_to_topic_id == {
        "vocal": "vocal",
        "唱功": "vocal",
        "보컬": "vocal",
        "dance": "dance",
        "舞蹈": "dance",
        "안무": "dance",
        "visual": "visual",
        "顏值": "visual",
        "비주얼": "visual",
    }


def test_load_topic_dictionary_rejects_duplicate_topic_id(tmp_path):
    raw_dictionary = make_dictionary()
    raw_dictionary["topics"].append(raw_dictionary["topics"][0].copy())

    with pytest.raises(ValueError, match="Duplicate topic_id: topic_a"):
        load_topic_keyword_dictionary(
            write_dictionary(tmp_path, raw_dictionary)
        )


def test_load_topic_dictionary_rejects_normalized_keyword_conflict(
    tmp_path,
):
    raw_dictionary = make_dictionary()
    raw_dictionary["topics"].append(
        {
            "topic_id": "topic_b",
            "display_name": "Topic B",
            "keywords": ["ＫＥＹＷＯＲＤ Ａ"],
        }
    )

    with pytest.raises(
        ValueError,
        match=r"conflicts with topic\[topic_a\]",
    ):
        load_topic_keyword_dictionary(
            write_dictionary(tmp_path, raw_dictionary)
        )


def test_load_topic_dictionary_rejects_empty_keywords(tmp_path):
    raw_dictionary = make_dictionary()
    raw_dictionary["topics"][0]["keywords"] = []

    with pytest.raises(ValueError, match="must be a non-empty list"):
        load_topic_keyword_dictionary(
            write_dictionary(tmp_path, raw_dictionary)
        )


def test_load_topic_dictionary_rejects_unsupported_schema(tmp_path):
    raw_dictionary = make_dictionary()
    raw_dictionary["schema_version"] = 2

    with pytest.raises(
        ValueError,
        match="Unsupported topic dictionary schema_version: 2",
    ):
        load_topic_keyword_dictionary(
            write_dictionary(tmp_path, raw_dictionary)
        )
