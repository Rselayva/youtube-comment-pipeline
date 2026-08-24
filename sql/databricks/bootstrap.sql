-- Databricks Unity Catalog deployment template: development environment.
--
-- Replace every placeholder before execution:
--   <CATALOG>          Existing Unity Catalog catalog.
--   <PIPELINE_SCHEMA>  Schema for Delta tables and current views.
--   <PIPELINE_VOLUME>  Managed Volume for Raw/Silver/Gold/manifests.
--
-- Required privileges include USE CATALOG and CREATE SCHEMA on the catalog,
-- followed by USE SCHEMA and CREATE VOLUME on the created schema.

CREATE SCHEMA IF NOT EXISTS <CATALOG>.<PIPELINE_SCHEMA>
COMMENT 'YouTube comment pipeline development schema';

CREATE VOLUME IF NOT EXISTS
    <CATALOG>.<PIPELINE_SCHEMA>.<PIPELINE_VOLUME>
COMMENT 'YouTube comment pipeline Raw, Silver, Gold, and manifest files';
