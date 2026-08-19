from unittest.mock import call, patch

from transformation.comment_parser import (
    parse_comment_page,
    parse_top_level_comment,
)


def test_parse_top_level_comment_flattens_youtube_thread():
    comment_thread = {
        "id": "thread-1",
        "snippet": {
            "totalReplyCount": 3,
            "topLevelComment": {
                "id": "comment-1",
                "snippet": {
                    "videoId": "video-1",
                    "textDisplay": "Displayed comment text",
                    "textOriginal": "Original comment text",
                    "authorDisplayName": "Test Author",
                    "likeCount": 12,
                    "publishedAt": "2026-08-18T09:00:00Z",
                    "updatedAt": "2026-08-18T10:00:00Z",
                },
            },
        },
    }

    parsed_comment = parse_top_level_comment(
        comment_thread=comment_thread,
        ingested_at="2026-08-19T08:00:00+00:00",
    )

    assert parsed_comment == {
        "comment_id": "comment-1",
        "video_id": "video-1",
        "author_name": "Test Author",
        "comment_text": "Original comment text",
        "like_count": 12,
        "total_reply_count": 3,
        "published_at": "2026-08-18T09:00:00Z",
        "updated_at": "2026-08-18T10:00:00Z",
        "ingested_at": "2026-08-19T08:00:00+00:00",
    }


@patch("transformation.comment_parser.parse_top_level_comment")
def test_parse_comment_page_parses_every_thread(mock_parse_top_level_comment):
    first_thread = {"id": "thread-1"}
    second_thread = {"id": "thread-2"}
    first_comment = {"comment_id": "comment-1"}
    second_comment = {"comment_id": "comment-2"}
    mock_parse_top_level_comment.side_effect = [
        first_comment,
        second_comment,
    ]
    raw_document = {
        "ingested_at": "2026-08-19T08:00:00+00:00",
        "raw_response": {
            "items": [first_thread, second_thread],
        },
    }

    parsed_comments = parse_comment_page(raw_document)

    assert parsed_comments == [first_comment, second_comment]
    assert mock_parse_top_level_comment.call_args_list == [
        call(
            comment_thread=first_thread,
            ingested_at="2026-08-19T08:00:00+00:00",
        ),
        call(
            comment_thread=second_thread,
            ingested_at="2026-08-19T08:00:00+00:00",
        ),
    ]
