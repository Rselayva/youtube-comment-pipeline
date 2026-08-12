from ingestion.youtube_client import get_comments


VIDEO_ID = "aFrQIJ5cbRc"


def main():
    comments = get_comments(VIDEO_ID)

    print(comments)


if __name__ == "__main__":
    main()