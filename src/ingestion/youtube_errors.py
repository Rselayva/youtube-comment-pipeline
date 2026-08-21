class YouTubeAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        resource_id: str | None,
        status_code: int | None,
        reason: str | None,
    ):
        super().__init__(message)
        self.resource_id = resource_id
        self.video_id = resource_id
        self.status_code = status_code
        self.reason = reason


class YouTubeRateLimitError(YouTubeAPIError):
    pass


class YouTubeQuotaExceededError(YouTubeAPIError):
    pass


class YouTubeCommentsDisabledError(YouTubeAPIError):
    pass


class YouTubeVideoNotFoundError(YouTubeAPIError):
    pass


class YouTubeParentCommentNotFoundError(YouTubeAPIError):
    pass
