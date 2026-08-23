# Databricks End-to-End Workflow

The production notebook keeps deployment settings outside the shared Python
pipeline. It reads a YouTube API key from a Databricks Secret, maps one Unity
Catalog Volume to the platform-neutral storage layout, runs ingestion and
transformation, then publishes that exact run to Delta history tables and
current views.

## 1. Create development resources

Run this in Databricks SQL Editor. These names are recommended for the current
development workspace and remain notebook parameters rather than source-code
constants:

```sql
CREATE SCHEMA IF NOT EXISTS
    rselayva_dev.youtube_comment_pipeline_dev;

CREATE VOLUME IF NOT EXISTS
    rselayva_dev.youtube_comment_pipeline_dev.pipeline_data;
```

The job principal needs `USE CATALOG`, `USE SCHEMA`, Volume read/write access,
and permission to create tables and views in this schema.

## 2. Store the API key as a Secret

Never paste the key into the notebook or a job parameter.

Create a Databricks-backed scope named `youtube-comment-pipeline` by opening
the following case-sensitive path on your workspace URL:

```text
https://<your-databricks-workspace>#secrets/createScope
```

Choose **Creator** for Manage Principal when available. Add the secret with
Databricks CLI 0.205 or later; the interactive command avoids putting the key
in shell history:

```bash
databricks secrets put-secret youtube-comment-pipeline youtube-api-key
```

At the prompt, paste only the YouTube Data API key. Verify metadata without
printing its value:

```bash
databricks secrets list-secrets youtube-comment-pipeline
```

The notebook reads it with `dbutils.secrets.get()`. The scope and key names are
widgets, so another deployment can use different names without code changes.

## 3. Run one end-to-end development execution

1. Pull the latest `main` branch in the Databricks Git folder.
2. Open `databricks/run_pipeline_notebook.py`.
3. Attach Unity Catalog-enabled compute or serverless notebook compute.
4. Fill the widgets shown above the notebook:

| Widget | First-run value |
| --- | --- |
| `video_id` | An 11-character YouTube video ID |
| `max_pages` | `2` |
| `page_size` | `100` |
| `catalog` | `rselayva_dev` |
| `schema` | `youtube_comment_pipeline_dev` |
| `volume` | `pipeline_data` |
| `secret_scope` | `youtube-comment-pipeline` |
| `secret_key` | `youtube-api-key` |

5. Choose **Run all**.

The final cell prints `status`, `run_id`, `manifest_path`, and row counts. Raw,
Silver, rejected, Gold JSONL, and manifests are stored below:

```text
/Volumes/rselayva_dev/youtube_comment_pipeline_dev/pipeline_data/
    youtube_comment_pipeline/
```

Delta history tables, publication audit table, and current views are created
in `rselayva_dev.youtube_comment_pipeline_dev`.

## 4. Reconcile the published run

Open `databricks/validate_pipeline_notebook.py`, attach the same compute, and
set:

| Widget | Value |
| --- | --- |
| `catalog` | `rselayva_dev` |
| `schema` | `youtube_comment_pipeline_dev` |
| `video_id` | The same 11-character video ID |

Choose **Run all**. A passing result confirms that the latest publication
audit row counts match both its immutable history rows and all four current
views. Zero rows are valid when a video has no configured entity or topic
matches; mismatched counts are not.

## 5. Turn the notebooks into a Workflow

After the manual run succeeds:

1. In **Workflows**, create a Job with a notebook task named `run_pipeline`
   that uses `databricks/run_pipeline_notebook.py`.
2. Choose serverless or Unity Catalog-enabled compute and add the same widget
   keys and values under task parameters.
3. Add a second notebook task named `validate_publication` using
   `databricks/validate_pipeline_notebook.py`.
4. Make `validate_publication` depend on successful completion of
   `run_pipeline`; pass `catalog`, `schema`, and `video_id` to it.
5. Keep `video_id` as a runtime parameter; do not add the API key itself.
6. Add a schedule and failure notification email, then save the Job.

Notebook task parameters are passed to matching `dbutils.widgets` names. A
manual **Run now with different settings** can override them without editing
the notebook.

Official references:

- [Databricks secret management](https://docs.databricks.com/aws/en/security/secrets/)
- [Databricks notebook widgets](https://docs.databricks.com/aws/en/notebooks/widgets)
- [Schedule notebook jobs](https://docs.databricks.com/aws/en/notebooks/schedule-notebook-jobs)
- [Configure task parameters](https://docs.databricks.com/aws/en/jobs/task-parameters)
