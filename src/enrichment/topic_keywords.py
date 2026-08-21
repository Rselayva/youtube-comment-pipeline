import json
from dataclasses import dataclass
from pathlib import Path

from enrichment.entity_aliases import normalize_alias


DEFAULT_TOPIC_KEYWORDS_PATH = Path("config/topic_keywords.json")
SUPPORTED_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TopicKeyword:
    topic_id: str
    display_name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class TopicKeywordDictionary:
    schema_version: int
    dictionary_version: str
    description: str
    topics_by_id: dict[str, TopicKeyword]
    keyword_to_topic_id: dict[str, str]


def _require_non_empty_string(value, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")

    return value.strip()


def _load_keywords(raw_keywords, topic_id: str) -> tuple[str, ...]:
    if not isinstance(raw_keywords, list) or not raw_keywords:
        raise ValueError(f"topic[{topic_id}].keywords must be a non-empty list")

    keywords = []
    normalized_keywords = set()

    for raw_keyword in raw_keywords:
        keyword = _require_non_empty_string(
            raw_keyword,
            f"topic[{topic_id}].keyword",
        )
        normalized_keyword = normalize_alias(keyword)
        if normalized_keyword in normalized_keywords:
            raise ValueError(
                f"topic[{topic_id}] contains duplicate keyword: {keyword}"
            )

        normalized_keywords.add(normalized_keyword)
        keywords.append(keyword)

    return tuple(keywords)


def load_topic_keyword_dictionary(
    path: Path = DEFAULT_TOPIC_KEYWORDS_PATH,
) -> TopicKeywordDictionary:
    with path.open(encoding="utf-8") as input_file:
        raw_dictionary = json.load(input_file)

    schema_version = raw_dictionary.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported topic dictionary schema_version: "
            f"{schema_version}"
        )

    dictionary_version = _require_non_empty_string(
        raw_dictionary.get("dictionary_version"),
        "dictionary_version",
    )
    description = _require_non_empty_string(
        raw_dictionary.get("description"),
        "description",
    )
    raw_topics = raw_dictionary.get("topics")
    if not isinstance(raw_topics, list) or not raw_topics:
        raise ValueError("topics must be a non-empty list")

    topics_by_id = {}
    keyword_to_topic_id = {}

    for raw_topic in raw_topics:
        topic_id = _require_non_empty_string(
            raw_topic.get("topic_id"),
            "topic.topic_id",
        )
        if topic_id in topics_by_id:
            raise ValueError(f"Duplicate topic_id: {topic_id}")

        display_name = _require_non_empty_string(
            raw_topic.get("display_name"),
            f"topic[{topic_id}].display_name",
        )
        keywords = _load_keywords(raw_topic.get("keywords"), topic_id)

        for keyword in keywords:
            normalized_keyword = normalize_alias(keyword)
            existing_topic_id = keyword_to_topic_id.get(normalized_keyword)
            if existing_topic_id is not None:
                raise ValueError(
                    f"Keyword '{keyword}' conflicts with topic[{existing_topic_id}]"
                )
            keyword_to_topic_id[normalized_keyword] = topic_id

        topics_by_id[topic_id] = TopicKeyword(
            topic_id=topic_id,
            display_name=display_name,
            keywords=keywords,
        )

    return TopicKeywordDictionary(
        schema_version=schema_version,
        dictionary_version=dictionary_version,
        description=description,
        topics_by_id=topics_by_id,
        keyword_to_topic_id=keyword_to_topic_id,
    )
