class YouTubeAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        video_id: str,
        status_code: int | None,
        reason: str | None,
    ):
        super().__init__(message)
        self.video_id = video_id
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
