---
version: 1
default_connection: example-db
settings:
  validate_on_push: true
  require_description: true
---

# Example DB-AGENTS Workspace

This is an example workspace for learning db-agents-cli.

## Getting Started

1. Run `dba validate` to check all files
2. Run `dba db list` to see available connections
3. Run `dba diff` to compare with database (requires real database)
4. Run `dba push` to sync to database (requires real database)
