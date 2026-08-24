-- Databricks Unity Catalog deployment template: isolated smoke test.
--
-- Replace every placeholder before execution:
--   <CATALOG>       Existing development catalog.
--   <SMOKE_SCHEMA>  Dedicated schema containing "smoke" or "test".
--   <SMOKE_VOLUME>  Managed Volume for anonymous smoke-test fixtures.
--
-- Never point the smoke notebook at a production schema. The notebook also
-- enforces the schema-name guard before writing any fixtures.

CREATE SCHEMA IF NOT EXISTS <CATALOG>.<SMOKE_SCHEMA>
COMMENT 'Isolated YouTube comment pipeline smoke-test schema';

CREATE VOLUME IF NOT EXISTS
    <CATALOG>.<SMOKE_SCHEMA>.<SMOKE_VOLUME>
COMMENT 'Anonymous YouTube comment pipeline smoke-test fixtures';
