from ingestion.youtube_client import get_comments


VIDEO_ID = "aFrQIJ5cbRc"


def main():
    first_page = get_comments(VIDEO_ID)

    print("First page:")
    print(len(first_page["items"]))

    next_page_token = first_page.get("nextPageToken")

    if next_page_token:
        second_page = get_comments(
            VIDEO_ID,
            page_token=next_page_token,
        )

        print("Second page:")
        print(len(second_page["items"]))


if __name__ == "__main__":
    main()
