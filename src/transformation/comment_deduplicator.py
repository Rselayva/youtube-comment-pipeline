def select_latest_comment_versions(comments: list[dict]) -> list[dict]:
    latest_comments_by_id = {}

    for comment in comments:
        comment_id = comment["comment_id"]
        current_comment = latest_comments_by_id.get(comment_id)

        if current_comment is None:
            latest_comments_by_id[comment_id] = comment
            continue

        candidate_version = (
            comment["updated_at"],
            comment["ingested_at"],
        )
        current_version = (
            current_comment["updated_at"],
            current_comment["ingested_at"],
        )

        if candidate_version > current_version:
            latest_comments_by_id[comment_id] = comment

    return list(latest_comments_by_id.values())
