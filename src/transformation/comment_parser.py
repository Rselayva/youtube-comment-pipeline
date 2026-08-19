def parse_top_level_comment(
    comment_thread: dict,
    ingested_at: str,
) -> dict:
    thread_snippet = comment_thread["snippet"]
    top_level_comment = thread_snippet["topLevelComment"]
    comment_snippet = top_level_comment["snippet"]

    return {
        "comment_id": top_level_comment["id"],
        "video_id": comment_snippet["videoId"],
        "author_name": comment_snippet.get("authorDisplayName"),
        "comment_text": comment_snippet["textOriginal"],
        "like_count": comment_snippet["likeCount"],
        "total_reply_count": thread_snippet["totalReplyCount"],
        "published_at": comment_snippet["publishedAt"],
        "updated_at": comment_snippet["updatedAt"],
        "ingested_at": ingested_at,
    }


def parse_comment_page(raw_document: dict) -> list[dict]:
    ingested_at = raw_document["ingested_at"]
    comment_threads = raw_document["raw_response"]["items"]

    return [
        parse_top_level_comment(
            comment_thread=comment_thread,
            ingested_at=ingested_at,
        )
        for comment_thread in comment_threads
    ]
