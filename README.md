# YouTube Comment Pipeline

An end-to-end data engineering project that collects YouTube comments,
processes and enriches the data, and produces analytics-ready datasets.

## Project Goals

- Collect YouTube video and comment data
- Build an ETL data pipeline
- Perform data cleaning and transformation
- Analyze sentiment and keywords
- Store data using a layered data architecture
- Create analytics-ready datasets
- Build data visualizations

## Tech Stack

- Python
- SQL
- PySpark
- Databricks
- Delta Lake
- Apache Airflow
- Docker
- Power BI

## Architecture

```text
YouTube Data API
  -> Raw / Bronze JSON
  -> top-level comment parsing and validation
  -> incremental Silver JSONL
  -> group and member mention enrichment
  -> Gold group and member share-of-voice metrics
```

The default workflow processes top-level comments only. It retains
`totalReplyCount` for discussion-engagement metrics without ingesting reply
content. Raw reply ingestion exists as an optional capability but is not
connected to the default pipeline, since per-comment reply requests increase
quota usage and reply conversations can distort broad sentiment or keyword
analysis. A future opt-in mode should use `--include-replies` with a strict
per-comment page and page-size limit.

The core analytics roadmap prioritizes group and member share of voice in
top-level comments:

```text
video metadata ingestion
  -> group and member alias dictionaries
  -> comment-group and comment-member mention enrichment
  -> daily and video-level group/member share of voice
  -> keyword and sentiment enrichment
```

The existing `comment_text` field remains the source text for group/member
mention, keyword, and sentiment processing. Reply Silver processing is
intentionally out of scope for the default roadmap.

## Run the Pipeline

Create a `.env` file with a YouTube Data API key:

```env
YOUTUBE_API_KEY=your_api_key
```

Run the pipeline with a video ID or supported YouTube URL:

```bash
python src/main.py aFrQIJ5cbRc
python src/main.py "https://www.youtube.com/watch?v=aFrQIJ5cbRc"
python src/main.py aFrQIJ5cbRc --max-pages 10
python src/main.py aFrQIJ5cbRc --max-pages 10 --page-size 100
```

Supported URL formats include `youtube.com/watch`, `youtu.be`,
`youtube.com/shorts`, `youtube.com/live`, and `youtube.com/embed`.
`--max-pages` defaults to 2 and accepts values from 1 to 100.
`--page-size` defaults to 10 and accepts values from 1 to 100.

## Project Status

🚧 In development
