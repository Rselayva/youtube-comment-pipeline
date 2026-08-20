import pytest

from video_input import (
    DEFAULT_MAX_PAGES,
    PipelineArguments,
    extract_video_id,
    parse_cli_args,
)


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


def test_parse_cli_args_returns_normalized_id_and_default_max_pages():
    args = parse_cli_args(
        [f"https://www.youtube.com/watch?v={VIDEO_ID}"]
    )

    assert args == PipelineArguments(
        video_id=VIDEO_ID,
        max_pages=DEFAULT_MAX_PAGES,
    )


def test_parse_cli_args_accepts_custom_max_pages():
    args = parse_cli_args([VIDEO_ID, "--max-pages", "25"])

    assert args == PipelineArguments(
        video_id=VIDEO_ID,
        max_pages=25,
    )


def test_parse_cli_args_exits_before_pipeline_for_invalid_video():
    with pytest.raises(SystemExit) as error:
        parse_cli_args(["invalid"])

    assert error.value.code == 2


@pytest.mark.parametrize("value", ["0", "-1", "101", "not-an-integer"])
def test_parse_cli_args_rejects_invalid_max_pages(value):
    with pytest.raises(SystemExit) as error:
        parse_cli_args([VIDEO_ID, "--max-pages", value])

    assert error.value.code == 2
