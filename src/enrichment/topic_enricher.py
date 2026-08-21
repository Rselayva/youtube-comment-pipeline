import re

from enrichment.entity_aliases import normalize_alias
from enrichment.topic_keywords import TopicKeywordDictionary


def _find_keyword_spans(
    normalized_text: str,
    keyword: str,
) -> list[tuple[int, int]]:
    normalized_keyword = normalize_alias(keyword)
    escaped_keyword = re.escape(normalized_keyword)

    if normalized_keyword.isascii():
        pattern = (
            rf"(?<![A-Za-z0-9_]){escaped_keyword}(?![A-Za-z0-9_])"
        )
    else:
        pattern = escaped_keyword

    return [match.span() for match in re.finditer(pattern, normalized_text)]


def _find_matched_keywords(
    comment_text: str,
    keywords: tuple[str, ...],
) -> tuple[str, ...]:
    normalized_text = normalize_alias(comment_text)
    candidates = [
        (start, end, keyword)
        for keyword in keywords
        for start, end in _find_keyword_spans(normalized_text, keyword)
    ]
    candidates.sort(key=lambda candidate: (-(candidate[1] - candidate[0]), candidate[0]))

    selected_spans = []
    matched_keywords = set()

    for start, end, keyword in candidates:
        if any(
            start < selected_end and selected_start < end
            for selected_start, selected_end in selected_spans
        ):
            continue

        selected_spans.append((start, end))
        matched_keywords.add(keyword)

    return tuple(
        keyword for keyword in keywords if keyword in matched_keywords
    )


def enrich_comment_topics(
    comment: dict,
    topics: TopicKeywordDictionary,
) -> list[dict]:
    comment_text = comment.get("comment_text")
    if not isinstance(comment_text, str):
        raise ValueError("comment_text must be a string")

    topic_records = []

    for topic in topics.topics_by_id.values():
        matched_keywords = _find_matched_keywords(
            comment_text,
            topic.keywords,
        )
        if not matched_keywords:
            continue

        topic_records.append(
            {
                "comment_id": comment["comment_id"],
                "video_id": comment["video_id"],
                "topic_id": topic.topic_id,
                "display_name": topic.display_name,
                "matched_keywords": matched_keywords,
                "topic_count": 1,
                "published_at": comment["published_at"],
                "ingested_at": comment["ingested_at"],
                "dictionary_version": topics.dictionary_version,
            }
        )

    return topic_records


def enrich_comment_dataset_topics(
    comments: list[dict],
    topics: TopicKeywordDictionary,
) -> list[dict]:
    return [
        topic_record
        for comment in comments
        for topic_record in enrich_comment_topics(comment, topics)
    ]
