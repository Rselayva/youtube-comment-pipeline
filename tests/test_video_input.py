import pytest

from video_input import extract_video_id, parse_cli_video_id


VIDEO_ID = "aFrQIJ5cbRc"


@pytest.mark.parametrize(
    "value",
    [
        VIDEO_ID,
        f"  {VIDEO_ID}  ",
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://m.youtube.com/watch?v={VIDEO_ID}&feature=share",
        f"https://youtu.be/{VIDEO_ID}?si=test",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://www.youtube.com/live/{VIDEO_ID}?feature=share",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
    ],
)
def test_extract_video_id_accepts_supported_inputs(value):
    assert extract_video_id(value) == VIDEO_ID


@pytest.mark.parametrize(
    ("value", "expected_error"),
    [
        ("", "Video must be an 11-character ID or YouTube URL"),
        ("too-short", "Video must be an 11-character ID or YouTube URL"),
        (
            "https://www.youtube.com/watch",
            "YouTube URL does not contain a valid video ID",
        ),
        (
            f"https://youtube.com.evil.example/watch?v={VIDEO_ID}",
            "URL host must be youtube.com or youtu.be",
        ),
        (
            "https://youtu.be/invalid",
            "YouTube URL does not contain a valid video ID",
        ),
    ],
)
def test_extract_video_id_rejects_invalid_inputs(value, expected_error):
    with pytest.raises(ValueError, match=expected_error):
        extract_video_id(value)


def test_parse_cli_video_id_returns_normalized_id():
    video_id = parse_cli_video_id(
        [f"https://www.youtube.com/watch?v={VIDEO_ID}"]
    )

    assert video_id == VIDEO_ID


def test_parse_cli_video_id_exits_before_pipeline_for_invalid_input():
    with pytest.raises(SystemExit) as error:
        parse_cli_video_id(["invalid"])

    assert error.value.code == 2
