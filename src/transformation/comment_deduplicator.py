def select_latest_comment_versions(comments: list[dict]) -> list[dict]:
    latest_comments_by_id = {}

    for comment in comments:
        comment_id = comment["comment_id"]
        current_comment = latest_comments_by_id.get(comment_id)

        if current_comment is None:
            latest_comments_by_id[comment_id] = comment
            continue

        candidate_updated_at = comment["updated_at"]
        current_updated_at = current_comment["updated_at"]
        content_changed = {
            key: value
            for key, value in comment.items()
            if key != "ingested_at"
        } != {
            key: value
            for key, value in current_comment.items()
            if key != "ingested_at"
        }

        if candidate_updated_at > current_updated_at:
            latest_comments_by_id[comment_id] = comment
        elif (
            candidate_updated_at == current_updated_at
            and content_changed
            and comment["ingested_at"] > current_comment["ingested_at"]
        ):
            latest_comments_by_id[comment_id] = comment

    return list(latest_comments_by_id.values())
