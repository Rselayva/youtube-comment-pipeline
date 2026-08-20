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

Coming soon.

## Run the Pipeline

Create a `.env` file with a YouTube Data API key:

```env
YOUTUBE_API_KEY=your_api_key
```

Run the pipeline with a video ID or supported YouTube URL:

```bash
python src/main.py aFrQIJ5cbRc
python src/main.py "https://www.youtube.com/watch?v=aFrQIJ5cbRc"
```

Supported URL formats include `youtube.com/watch`, `youtu.be`,
`youtube.com/shorts`, `youtube.com/live`, and `youtube.com/embed`.

## Project Status

🚧 In development
