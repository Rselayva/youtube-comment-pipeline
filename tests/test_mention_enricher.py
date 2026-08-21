from datetime import datetime, timezone

import pytest

from enrichment.entity_aliases import load_entity_alias_dictionary
from enrichment.mention_enricher import (
    count_alias_mentions,
    enrich_comment_dataset_mentions,
    enrich_comment_mentions,
)


ALIASES = load_entity_alias_dictionary()
TIMESTAMP = datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc)


def make_comment(comment_id: str, comment_text: str) -> dict:
    return {
        "comment_id": comment_id,
        "video_id": "video-1",
        "author_name": "Test Author",
        "comment_text": comment_text,
        "like_count": 0,
        "total_reply_count": 0,
        "published_at": TIMESTAMP,
        "updated_at": TIMESTAMP,
        "ingested_at": TIMESTAMP,
    }


def test_count_alias_mentions_normalizes_case_width_and_whitespace():
    text = "LILY lily ＬＩＬＹ Member   A"

    assert count_alias_mentions(text, "LILY") == 3
    assert count_alias_mentions(text, "member a") == 1


def test_count_alias_mentions_uses_boundaries_for_latin_aliases():
    text = "BAE is great, but BAE123 and baes are different tokens"

    assert count_alias_mentions(text, "BAE") == 1


def test_count_alias_mentions_allows_korean_suffixes():
    assert count_alias_mentions("해원이 최고야", "해원") == 1


def test_enrich_comment_mentions_outputs_group_and_member_alias_rows():
    comment = make_comment(
        "comment-1",
        "#NMIXX 엔믹스 LILY와 릴리, BAE123 말고 bae! 해원이 최고",
    )

    mentions = enrich_comment_mentions(comment, ALIASES)
    mention_keys = {
        (mention["entity_type"], mention["entity_id"]): (
            mention["matched_aliases"],
            mention["mention_count"],
        )
        for mention in mentions
    }

    assert mention_keys == {
        ("group", "nmixx"): (("NMIXX", "엔믹스"), 1),
        ("member", "nmixx_lily"): (("LILY", "릴리"), 1),
        ("member", "nmixx_haewon"): (("해원",), 1),
        ("member", "nmixx_bae"): (("BAE",), 1),
    }
    assert all(mention["group_id"] == "nmixx" for mention in mentions)
    assert all(
        mention["dictionary_version"] == "nmixx_v2"
        for mention in mentions
    )
    assert all(mention["published_at"] is TIMESTAMP for mention in mentions)


def test_enrich_comment_mentions_does_not_infer_group_from_member():
    comment = make_comment("comment-1", "KYUJIN 규진")

    mentions = enrich_comment_mentions(comment, ALIASES)

    assert {mention["entity_type"] for mention in mentions} == {"member"}
    assert sum(mention["mention_count"] for mention in mentions) == 1
    assert mentions[0]["matched_aliases"] == ("KYUJIN", "규진")


def test_enrich_comment_mentions_matches_chinese_member_aliases():
    comment = make_comment(
        "comment-1",
        "莉莉和吳海嫄，薛侖娥、裴眞率、金智佑、張圭珍",
    )

    mentions = enrich_comment_mentions(comment, ALIASES)

    assert {mention["entity_id"] for mention in mentions} == {
        "nmixx_lily",
        "nmixx_haewon",
        "nmixx_sullyoon",
        "nmixx_bae",
        "nmixx_jiwoo",
        "nmixx_kyujin",
    }
    assert sum(mention["mention_count"] for mention in mentions) == 6


def test_enrich_comment_mentions_counts_separated_short_aliases():
    comment = make_comment("comment-1", "海嫄和嫄都很有趣")

    mentions = enrich_comment_mentions(comment, ALIASES)

    assert len(mentions) == 1
    assert mentions[0]["matched_aliases"] == ("嫄", "海嫄")
    assert mentions[0]["mention_count"] == 1


def test_enrich_comment_mentions_counts_each_entity_once_per_comment():
    comment = make_comment(
        "comment-1",
        "NMIXX NMIXX, 海嫄、吳海嫄，海嫄真的很棒",
    )

    mentions = enrich_comment_mentions(comment, ALIASES)

    assert [mention["entity_id"] for mention in mentions] == [
        "nmixx",
        "nmixx_haewon",
    ]
    assert [mention["mention_count"] for mention in mentions] == [1, 1]
    assert mentions[0]["matched_aliases"] == ("NMIXX",)
    assert mentions[1]["matched_aliases"] == ("海嫄", "吳海嫄")


def test_enrich_comment_dataset_mentions_flattens_comments_in_order():
    comments = [
        make_comment("comment-1", "NMIXX"),
        make_comment("comment-2", "JIWOO"),
        make_comment("comment-3", "No entity mention"),
    ]

    mentions = enrich_comment_dataset_mentions(comments, ALIASES)

    assert [mention["comment_id"] for mention in mentions] == [
        "comment-1",
        "comment-2",
    ]
    assert [mention["entity_type"] for mention in mentions] == [
        "group",
        "member",
    ]


def test_enrich_comment_mentions_preserves_original_comment():
    comment = make_comment("comment-1", "NMIXX")

    enrich_comment_mentions(comment, ALIASES)

    assert comment["comment_text"] == "NMIXX"
    assert "mentions" not in comment


def test_enrich_comment_mentions_rejects_non_string_comment_text():
    comment = make_comment("comment-1", "NMIXX")
    comment["comment_text"] = None

    with pytest.raises(ValueError, match="comment_text must be a string"):
        enrich_comment_mentions(comment, ALIASES)
