---
version: 1
default_connection: jaffle-shop
settings:
  validate_on_push: true
  require_description: true
---

# Jaffle Shop DB-AGENTS Workspace

This workspace contains documentation for the dbt Jaffle Shop example database.

## Overview

The Jaffle Shop is a fictional e-commerce company used in dbt's getting started tutorial.
This database contains:

- **Raw Data**: Source tables with customer, order, and payment information
- **Staging Models**: Cleaned and renamed source data
- **Analytics Models**: Business logic and aggregations

## Using This Example

```bash
# Validate all resources
dba validate

# Check what would be synced
dba diff

# Push to database
dba push

# View in database
sqlite3 jaffle_shop.db "SELECT * FROM _agents"
```

## Database Structure

- `raw_*` tables: Source data from operational systems
- `staging_*` tables: Cleaned and typed data ready for modeling
- `analytics_*` tables: Business metrics and aggregations
