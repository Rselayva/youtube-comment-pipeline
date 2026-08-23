# Databricks Gold Smoke Test

This smoke test uses anonymous synthetic metrics. It does not call YouTube,
read an API key, or load local production data.

## 1. Create dedicated test resources

Use an existing development catalog if you do not have permission to create a
catalog. In Databricks SQL Editor, replace `YOUR_DEV_CATALOG` and run:

```sql
CREATE SCHEMA IF NOT EXISTS
    YOUR_DEV_CATALOG.youtube_comment_pipeline_smoke;

CREATE VOLUME IF NOT EXISTS
    YOUR_DEV_CATALOG.youtube_comment_pipeline_smoke.smoke_data;
```

Do not point the notebook at a production schema. The notebook refuses schema
names that do not contain `smoke` or `test`.

The executing user or service principal needs access to the catalog and
schema, read/write access to the Volume, and permission to create and modify
tables and views in the dedicated schema.

## 2. Add the Git repository to Databricks

In the Databricks workspace:

1. Open **Workspace**.
2. Choose **Create > Git folder**.
3. Use the repository URL:
   `https://github.com/Rselayva/youtube-comment-pipeline`.
4. Select branch `main`.
5. If the repository is private, connect your GitHub credential when prompted.

## 3. Run the notebook

1. Open `databricks/smoke_test_notebook.py` from the Git folder.
2. Attach Unity Catalog-enabled compute or use serverless notebook compute.
3. Set the notebook widgets:
   - `catalog`: your development catalog.
   - `schema`: `youtube_comment_pipeline_smoke`.
   - `volume`: `smoke_data`.
4. Choose **Run all**.

Expected final output:

```json
{
  "status": "passed",
  "loaded_rows": {
    "gold_video_entity_sov": 1,
    "gold_daily_entity_sov": 1,
    "gold_video_topic_metrics": 1,
    "gold_daily_topic_metrics": 1
  },
  "retry_was_idempotent": true
}
```

The output also includes the generated run ID and Volume manifest path.

## 4. Inspect the results

In Catalog Explorer, the dedicated schema should contain:

```text
gold_load_publications
gold_video_entity_sov_history
gold_daily_entity_sov_history
gold_video_topic_metrics_history
gold_daily_topic_metrics_history
gold_video_entity_sov          (view)
gold_daily_entity_sov          (view)
gold_video_topic_metrics       (view)
gold_daily_topic_metrics       (view)
```

If the notebook fails, copy the complete failing cell output and the
Databricks Runtime version back into the Codex task. Do not paste access
tokens, credentials, or unrelated production data.
