# YouTube Comment Pipeline

An end-to-end data engineering project that collects YouTube comments,
processes and enriches the data, and produces analytics-ready datasets.

## Project Goals

- Collect YouTube video and comment data
- Build an ETL data pipeline
- Perform data cleaning and transformation
- Classify comments into configured audience topics
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
  -> rule-based comment topic enrichment
```

The default workflow processes top-level comments only. It retains
`totalReplyCount` for discussion-engagement metrics without ingesting reply
content. Raw reply ingestion exists as an optional capability but is not
connected to the default pipeline, since per-comment reply requests increase
quota usage and reply conversations can distort broad audience analysis. A
future opt-in mode should use `--include-replies` with a strict
per-comment page and page-size limit.

The core analytics roadmap prioritizes group and member share of voice in
top-level comments:

```text
video metadata ingestion
  -> group and member alias dictionaries
  -> comment-group and comment-member mention enrichment
  -> daily and video-level group/member share of voice
  -> rule-based comment topic enrichment and Gold topic metrics
```

The existing `comment_text` field remains the source text for group/member
mention and topic processing. Reply Silver and sentiment processing are
intentionally out of scope for the current roadmap.

## Entity Mention Metrics

The NMIXX development dictionary is versioned as `nmixx_v2`. Each top-level
comment contributes at most one mention to each matched group or member,
regardless of repeated names or multiple aliases in the same comment.

The pipeline writes versioned current snapshots to:

```text
data/silver/youtube/comment_entity_mentions/<dictionary_version>/<video_id>/current_mentions.jsonl
data/silver/youtube/comment_topics/<dictionary_version>/<video_id>/current_topics.jsonl
data/gold/youtube/video_entity_sov/<dictionary_version>/<video_id>/current_metrics.jsonl
data/gold/youtube/daily_entity_sov/<dictionary_version>/<video_id>/current_metrics.jsonl
data/gold/youtube/video_topic_metrics/<dictionary_version>/<video_id>/current_metrics.jsonl
data/gold/youtube/daily_topic_metrics/<dictionary_version>/<video_id>/current_metrics.jsonl
```

Gold entity metrics include all configured groups and members, including zero
mention rows. `comment_share_of_voice` uses all top-level comments in the
video or UTC day as its denominator. `entity_share_of_voice` uses mention
comments from the same entity type (`group` or `member`) as its denominator.
Group metrics represent explicit group-name mentions; member mentions do not
implicitly add a group mention.

## Comment Topics

The initial `comment_topics_v1` taxonomy contains only the stable Topic IDs
`vocal`, `dance`, and `visual`. Each topic starts with a small English,
Traditional Chinese, and Korean keyword set for development and can be
expanded in later dictionary versions. A top-level comment contributes at
most one count to each matched Topic ID, even when a keyword is repeated or
multiple keywords for the same topic are present.

Gold Topic metrics include all configured Topic IDs, including zero-count
rows. `comment_share_of_voice` divides a Topic's comment count by all
top-level comments in the video or UTC day. `topic_share_of_voice` divides it
by the total number of Topic assignments, so configured topics can be
compared with one another. Sentiment analysis is not part of the current
project scope.

## SQL Analytics

The platform-neutral Gold table contracts are defined in
`sql/gold_schema.sql`. They cover video and daily entity share-of-voice plus
video and daily Topic metrics. Column names and SQL types are tested against
the Python output schemas to prevent contract drift.

Load each versioned `current_metrics.jsonl` snapshot into its matching table
using the JSON ingestion command provided by the chosen SQL platform. Replace
rows for the same video and dictionary version when a newer current snapshot
is loaded. Example ranking and trend queries are available in
`sql/example_queries.sql`; replace `YOUR_VIDEO_ID` before running them.

## Gold Data Quality

Gold writers validate each non-empty snapshot before creating or replacing a
file. The checks cover exact schema fields, non-negative counts, ratio ranges
and formulas, unique logical keys, grouped denominator totals, consistent
snapshot metadata, and agreement between each record's video/dictionary
version and its output partition. If validation fails, the current Gold
snapshot is not replaced.

## Run Manifests

After a successful pipeline run, an atomic control manifest is written to:

```text
data/manifests/youtube/runs/<video_id>/<UTC date>/<run timestamp>_run.json
```

The versioned manifest records the video ID, CLI parameters, entity and Topic
dictionary versions, dataset counts, artifact paths, timestamps, and execution
duration. It does not contain the YouTube API key or comment text. A successful
manifest is created only after all Bronze, Silver, and Gold outputs for the run
have completed successfully.

Failed runs also attempt to write a manifest with the failure stage, exception
type, and any counts or artifact paths known at that point. Exception messages
and tracebacks are excluded from the manifest; tracebacks remain in the
application log. If the failed manifest cannot be written, that secondary
error is logged without replacing the original pipeline exception.

Show run summaries for a video without calling the YouTube API:

```bash
python src/run_summary.py aFrQIJ5cbRc
python src/run_summary.py "https://www.youtube.com/watch?v=aFrQIJ5cbRc"
python src/run_summary.py aFrQIJ5cbRc --latest-successful
python src/run_summary.py aFrQIJ5cbRc --history 10
```

The read-only command validates the manifest schema and prints JSON containing
status, timestamps, parameters, dictionary versions, counts, artifact paths,
and failure stage/type when applicable. By default it returns the latest run;
`--latest-successful` scans backward to the most recent succeeded run, and
`--history N` returns 1–100 runs in newest-first order. Selection uses the UTC
timestamped manifest path rather than filesystem modification time.

### Load Gold Snapshots into DuckDB

Load all four Gold snapshots from the latest successful run manifest into a
persistent local DuckDB database:

```bash
python src/load_gold.py aFrQIJ5cbRc
python src/load_gold.py aFrQIJ5cbRc --database data/warehouse/custom.duckdb
```

The default database is `data/warehouse/youtube_analytics.duckdb`. The loader
validates the success manifest, artifact paths, manifest-to-row video and
dictionary lineage, and the typed tables declared in `sql/gold_schema.sql`.
All four tables are replaced in one transaction for the same `video_id` and
`dictionary_version`, so rerunning the same snapshot is idempotent. If any
table fails, the transaction is rolled back and the previous database state is
preserved. Empty JSONL snapshots intentionally replace prior rows with zero
rows.

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
