# DB-AGENTS Sync Tool - Implementation Plan

## Overview

A Python CLI tool for syncing DB-AGENTS metadata between local markdown files and database `_agents._agents` tables. The tool provides a git-like workflow for managing database documentation as code.

## Goals

1. **Bidirectional sync**: Push local markdown files to databases, pull database content to local files
2. **Multi-database support**: Manage multiple database connections from a single workspace
3. **Version control friendly**: Store all metadata as markdown files with YAML frontmatter
4. **Developer experience**: Rich CLI output, clear error messages, validation
5. **Flexibility**: Support any SQL database with appropriate drivers

## Project Structure

```
db-agents-cli/
├── pyproject.toml              # uv-managed dependencies
├── README.md
├── src/
│   └── db_agents_cli/
│       ├── __init__.py
│       ├── main.py             # Typer CLI entrypoint
│       ├── models.py           # Pydantic models for validation
│       ├── config.py           # Configuration management
│       ├── database.py         # Database abstraction layer
│       ├── sync.py             # Push/pull logic
│       ├── filesystem.py       # File discovery and parsing
│       └── utils.py            # Rich formatting helpers
└── tests/
    ├── __init__.py
    ├── test_sync.py
    └── fixtures/
```

## Core Philosophy

**"Markdown all the way down" + "Metadata is the source of truth"**

- All config files are markdown with YAML frontmatter (no `.yaml` files)
- Folder structure is for human organization only - it has NO semantic meaning
- Metadata in each file determines where it syncs to the database
- Files can be organized however you want: flat, nested, by domain, by schema, whatever

## Workspace Structure

```
my-project/
├── DB-AGENTS/                  # Root workspace (configurable)
│   ├── AGENTS.md               # Root config (workspace settings)
│   ├── prod-warehouse/         # Connection folder (name = connection identifier)
│   │   ├── AGENTS.md           # Connection config (sqlalchemy_uri here)
│   │   ├── global.md           # Resource files (organize however you want!)
│   │   ├── revenue_analysis.md
│   │   ├── ecommerce/          # Optional: organize by schema
│   │   │   ├── orders.md
│   │   │   ├── products.md
│   │   │   └── line_items/     # Optional: deeper nesting
│   │   │       └── order_items.md
│   │   └── analytics_daily_metrics.md  # Or keep files flat!
│   └── dev-warehouse/
│       ├── AGENTS.md
│       └── global.md
```

**Alternative layouts (all valid!):**

```
# Flat structure - everything in connection root
prod-warehouse/
├── AGENTS.md
├── global.md
├── ecommerce_orders.md
├── ecommerce_products.md
└── analytics_metrics.md

# Grouped by domain
prod-warehouse/
├── AGENTS.md
├── core/
│   ├── global.md
│   └── finance_domain.md
└── product-analytics/
    └── events.md

# Grouped by resource_type
prod-warehouse/
├── AGENTS.md
├── global/
│   └── global.md
├── domains/
│   └── revenue_analysis.md
└── tables/
    ├── orders.md
    └── products.md
```

**The tool doesn't care - it just scans all `.md` files and reads their metadata!**

## File Format

### Root AGENTS.md

```markdown
---
version: 1
default_connection: prod-warehouse
settings:
  validate_on_push: true
  require_description: true
---

# DB-AGENTS Workspace

This workspace manages database documentation for our data platform.
```

### Connection AGENTS.md

```markdown
---
sqlalchemy_uri: "postgresql://user:{{ env.PROD_DB_PASSWORD }}@prod.example.com/warehouse"
default_target_schema: _agents
display_name: "Production Warehouse"
---

# Production Warehouse

PostgreSQL production warehouse containing all analytics data.

## Schemas
- `_agents` - Agent metadata (managed by db-agents)
- `ecommerce` - E-commerce transactional data
- `analytics` - Derived analytics tables
```

### Resource Markdown File

```markdown
---
resource_type: table
resource_name: ecommerce.orders
target_schema: _agents
description: Order headers with customer and fulfillment info
---

# ecommerce.orders

## Purpose
Order-level information including customer, dates, and fulfillment status.

## Key Columns
- `order_id` (PK)
- `customer_id` (FK to customers)
- `order_date` (partition key, always filter on this for performance)
- `status` (pending, shipped, delivered, canceled)
- `total_amount` (includes product revenue + shipping + tax)

## Critical Notes
- `total_amount` should NOT be used for product revenue analysis
- Always join to `order_items` for line-level detail
```

**Metadata Fields:**
- `resource_type` - **Required** (global, domain, table, column, etc.)
- `resource_name` - **Required** (identifier like `ecommerce.orders` or `global`)
- `target_schema` - **Optional** (DB schema to sync to, defaults to `_agents`)
- `description` - **Optional** but recommended (short summary for indexing)

**Rules:**
- Filename can be anything (e.g., `orders.md`, `ecom_orders.md`, `foo.md`)
- File location can be anywhere in the connection folder
- YAML frontmatter defines where it syncs to the database
- Everything after frontmatter becomes `full_markdown` in the database
- The tool scans all `.md` files except `AGENTS.md`

**Supported URI formats** (standard SQLAlchemy):
```
postgresql://user:pass@host:port/database
mysql://user:pass@host:port/database
snowflake://user:pass@account/database/schema
bigquery://project/dataset
sqlite:///path/to/file.db
duckdb:///path/to/file.duckdb
```

**URI Template Rules:**
- Templates use Jinja2 syntax: `{{ env.VAR_NAME }}`
- Only `env` context is available (access to environment variables)
- Templates are rendered at runtime, never stored rendered
- Missing env vars cause clear error messages
- Can reference entire URI: `{{ env.DATABASE_URL }}`

## Quick Start Example

Here's a complete workflow showing how to use the tool:

```bash
# 1. Set up environment variables
cat > .env <<EOF
PROD_DB_PASSWORD=my_secure_password
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
EOF

# 2. Initialize workspace
db-agents init
# Creates DB-AGENTS/ directory with root AGENTS.md

# 3. Add a connection (creates folder with AGENTS.md)
db-agents init --connection prod-warehouse
# Interactive prompts:
#   SQLAlchemy URI: postgresql://user:{{ env.PROD_DB_PASSWORD }}@prod.example.com/warehouse
#   Display name: Production Warehouse
# Created: DB-AGENTS/prod-warehouse/AGENTS.md

# 4. Create resource files (organize however you want!)
cat > DB-AGENTS/prod-warehouse/global.md <<EOF
---
resource_type: global
resource_name: global
target_schema: _agents
description: Warehouse-wide conventions
---

# E-commerce Data Warehouse

## Canonical Sources
- Orders: Always use ecommerce.orders + ecommerce.order_items
EOF

cat > DB-AGENTS/prod-warehouse/ecommerce_orders.md <<EOF
---
resource_type: table
resource_name: ecommerce.orders
target_schema: _agents
description: Order headers with customer info
---

# ecommerce.orders

Order-level information...
EOF

# 5. Validate files (can use 'dba' shortcut!)
dba validate
# ✓ All files valid
# 2 resources found in prod-warehouse

# 6. Check what would be pushed
dba diff
# Target Schema: _agents
#   A global.md (new)
#   A ecommerce_orders.md (new)

# 7. Push to database
db-agents push
# Connection: prod-warehouse
# Target Schema: _agents
#   A global (new)
#   A ecommerce.orders (new)
# Push 2 resources? [y/N]: y
# ✓ Synced 2 resources to _agents._agents
# Push complete

# 8. Edit a file
vim DB-AGENTS/prod-warehouse/global.md
# Update documentation...

# 9. Check status
db-agents status
# Target Schema: _agents
#   M global.md (modified)
#   ✓ ecommerce_orders.md (synced)

# 10. See the diff
db-agents diff global.md
# Shows color-coded diff

# 11. Push changes
db-agents push
# ✓ Updated 1 resource

# 12. Remove a file (delete from DB on next push)
rm DB-AGENTS/prod-warehouse/ecommerce_orders.md

db-agents status
# Target Schema: _agents
#   ✓ global.md (synced)
#   ! ecommerce.orders (in DB, will be deleted on push)

db-agents push
# WARNING: 1 resource will be DELETED from database
#   D ecommerce.orders
# Continue? [y/N]: y
# ✓ Deleted 1 resource
```

## Command Reference

The CLI is available as both `db-agents` and `dba` (3-letter shortcut for faster typing).

All examples below use `db-agents`, but you can substitute `dba` anywhere:
```bash
db-agents push      # or: dba push
db-agents db list   # or: dba db list
db-agents resource list --type domain  # or: dba resource list --type domain
```

### Command Overview

**Core Commands:**
- `init` - Initialize workspace
- `diff` - Compare local to database
- `push` - Push local files to database
- `status` - Show sync status
- `validate` - Validate local files
- `check` - Check workspace health
- `migrate` - Create/update database tables

**Database Management:**
- `db list` - List all connections
- `db test` - Test connection
- `db info` - Show connection details

**Resource Inspection:**
- `resource list` - List resources (with filters)
- `resource show` - Show resource details
- `resource search` - Full-text search

## Core Commands

### `db-agents init`

Initialize a new DB-AGENTS workspace.

```bash
db-agents init                           # Interactive setup
db-agents init --connection prod         # Create connection folder with AGENTS.md
```

**Behavior:**
- Creates `DB-AGENTS/` directory with root `AGENTS.md`
- Optionally creates first connection folder with `AGENTS.md`
- Interactive prompts for sqlalchemy_uri (with template examples)
- Creates example resource file to demonstrate format

### `db-agents diff`

Compare local files to database state.

```bash
db-agents diff                           # Diff default connection
db-agents diff --connection prod         # Diff specific connection
db-agents diff orders.md                 # Diff specific file
```

**Behavior:**
1. Scan all `.md` files (except `AGENTS.md`) in connection folder
2. Parse frontmatter and content
3. Query database for current state
4. Show side-by-side diff with rich formatting
5. Report: new files, modified files, deleted resources (in DB but not local)

**Output:**
- Color-coded diffs
- Separate frontmatter changes from content changes
- Summary statistics

### `db-agents push`

Push local files to database (deterministic, source-controlled).

```bash
db-agents push                           # Push default connection
db-agents push --connection prod         # Push specific connection
db-agents push --all                     # Push all connections
db-agents push --target-schema ecommerce # Push only files with target_schema=ecommerce
db-agents push --dry-run                 # Show what would change (same as diff)
db-agents push --force                   # Skip confirmation
```

**Behavior:**
1. Discover all `.md` files (except `AGENTS.md`) in connection folder
2. Parse frontmatter and markdown content
3. Validate with Pydantic models
4. Group by `target_schema`
5. Show summary of changes
6. Prompt for confirmation (unless `--force`)
7. Execute transaction per schema:
   - **Deterministic sync**: Database state = local file state
   - Upsert resources from local files
   - **Delete resources in DB not present locally** (with warnings)
8. Report results

**Important:** v1.0 is push-only and deterministic. What's in git is the source of truth!

### `db-agents status`

Show sync status (like `git status`).

```bash
db-agents status                         # All connections
db-agents status --connection prod       # Specific connection
```

**Output:**
```
Connection: prod-warehouse (postgresql://...)

Target Schema: _agents
  ✓ global.md (synced)
  M revenue_analysis.md (modified)
  A domain_finance.md (new)

Target Schema: ecommerce
  ✓ orders.md (synced)
  M products.md (modified)
  ! customers.md (in DB, not in local files - will be deleted on push!)

3 resources synced, 2 modified, 1 new, 1 will be deleted
```

### `db-agents validate`

Validate local files without touching the database.

```bash
db-agents validate                       # Validate all files
db-agents validate --connection prod     # Validate specific connection
```

**Checks:**
- All `.md` files (except `AGENTS.md`) have valid YAML frontmatter
- Required fields present (`resource_type`, `resource_name`)
- `target_schema` is valid if specified
- Markdown content is parseable
- No duplicate `resource_name` within same `target_schema`
- Optional: Referenced resources exist (cross-reference checking)

### `db-agents pull` (Future: v2.0+)

Pull resources from database to local files.

**Status:** Not in v1.0 - v1.0 is push-only (deterministic from source control).

**Future behavior:**
```bash
db-agents pull                           # Pull new/changed resources
db-agents pull --force                   # Overwrite local files
```

**Planned approach:**
- Query database for all resources
- For new resources (not in local files), create files in connection root
- For modified resources, show diff and prompt (or use `--force`)
- User can then `git mv` files to organize as desired
- Merge strategy TBD (last-write-wins, 3-way merge, etc.)

**Why not in v1.0:**
- Deterministic push-only is simpler and safer
- Git is the source of truth - if you need to bootstrap, manually create files
- Pull introduces merge conflicts and organization questions
- Can iterate on pull strategy based on user feedback

### `db-agents db` (or `dba db`)

Manage database connections.

```bash
db-agents db list                        # List all connections (from AGENTS.md files)
db-agents db test prod                   # Test connection (verify URI, credentials)
db-agents db info prod                   # Show connection details
```

**Output for `db list`:**
```
Available Connections:

  prod-warehouse
    URI: postgresql://user:***@prod.example.com/warehouse
    Status: ✓ Connected
    Target Schemas: _agents, ecommerce (2 schemas)
    Resources: 12 local files

  dev-warehouse
    URI: postgresql://user:***@localhost/dev_warehouse
    Status: ✗ Connection failed
    Error: could not translate host name "localhost" to address
```

### `db-agents resource` (or `dba resource`)

Inspect and manage resources.

```bash
# List resources
db-agents resource list                  # List all resources (from local files)
db-agents resource list --connection prod
db-agents resource list --type domain    # Filter by resource_type
db-agents resource list --schema _agents # Filter by target_schema
db-agents resource list --remote         # Query database instead of local files

# Show resource details
db-agents resource show global           # Show resource by name (with rendered markdown)
db-agents resource show ecommerce.orders --connection prod

# Search resources
db-agents resource search "revenue"      # Full-text search in descriptions and content
```

**Output for `resource list`:**
```
Resources in prod-warehouse:

Target Schema: _agents
  Resource Type  | Resource Name           | Description                          | File
  ---------------+-------------------------+--------------------------------------+------------------
  global         | global                  | Warehouse conventions               | global.md
  domain         | revenue_analysis        | Revenue analytics guidelines        | revenue_analysis.md
  table          | ecommerce.orders        | Order headers                       | ecom/orders.md
  table          | ecommerce.order_items   | Line items                          | ecom/order_items.md
  table          | ecommerce.products      | Product catalog                     | ecom/products.md

5 resources found
```

**Output for `resource list --remote`:**
```
Resources in prod-warehouse (from database):

Target Schema: _agents
  Resource Type  | Resource Name           | Description                          | Status
  ---------------+-------------------------+--------------------------------------+--------
  global         | global                  | Warehouse conventions               | ✓ synced
  domain         | revenue_analysis        | Revenue analytics guidelines        | M modified
  table          | ecommerce.orders        | Order headers                       | ✓ synced
  table          | ecommerce.customers     | Customer profiles                   | ! not local

3 synced, 1 modified, 1 not in local files
```

### `db-agents check` (or `dba check`)

Check workspace health and completeness.

```bash
db-agents check                          # Check everything
db-agents check --connection prod        # Check specific connection
db-agents check --strict                 # Fail on warnings
```

**Checks performed:**
1. **Workspace structure**
   - Root `AGENTS.md` exists
   - All connection folders have `AGENTS.md`
   - Connection URIs are valid templates

2. **Resource validation**
   - All `.md` files have valid frontmatter
   - Required fields present (`resource_type`, `resource_name`)
   - No duplicate `resource_name` within same `target_schema`
   - Descriptions are present (warning if missing)

3. **Database connectivity**
   - All connections can be reached
   - `_agents` schema exists (warning if not)
   - `_agents._agents` table exists (warning if not)

4. **Sync status**
   - Resources in local files but not in DB (new)
   - Resources in DB but not in local files (orphaned)
   - Resources with mismatched content (modified)

**Output:**
```
Checking workspace health...

✓ Workspace structure valid
  ✓ Root AGENTS.md found
  ✓ 2 connections configured

✓ Connection: prod-warehouse
  ✓ Connection URI valid
  ✓ Database reachable
  ✓ Schema _agents exists
  ✓ Table _agents._agents exists

⚠ Connection: dev-warehouse
  ✗ Database unreachable
  → Error: Connection refused

✓ Resources: 5 files scanned
  ✓ All files have valid frontmatter
  ✓ No duplicate resource names
  ⚠ 2 resources missing descriptions
    - ecommerce/products.md
    - analytics/metrics.md

⚠ Sync status:
  2 resources modified locally
  1 resource not in database (new)
  1 resource in database but not local (orphaned)

Summary: 3 errors, 4 warnings
Run 'db-agents diff' to see details
```

### `db-agents migrate`

Create/update `_agents._agents` table in database.

```bash
db-agents migrate --connection prod      # Ensure table exists
db-agents migrate --all                  # Run for all connections
```

**Behavior:**
- Check if `_agents` schema exists, create if needed
- Check if `_agents._agents` table exists
- Create table with canonical schema
- Idempotent (safe to run multiple times)

## Technical Design

### Secret Management

**Connection URI Template Rendering:**

```python
import os
from jinja2 import Template, StrictUndefined

class ConnectionManager:
    def __init__(self, config: ConnectionConfig):
        self.config = config

    def get_connection_uri(self) -> str:
        """Render connection URI template with environment variables"""
        # Load .env if present
        from dotenv import load_dotenv
        load_dotenv()

        # Render Jinja2 template with strict undefined checking
        template = Template(
            self.config.sqlalchemy_uri,
            undefined=StrictUndefined  # Fail fast on missing vars
        )

        try:
            rendered_uri = template.render(env=os.environ)
            return rendered_uri
        except Exception as e:
            # Provide clear error with variable name
            raise ValueError(
                f"Failed to render connection URI template. "
                f"Missing or invalid environment variable: {e}"
            )

    def test_connection(self) -> bool:
        """Test database connection without executing queries"""
        from sqlalchemy import create_engine
        try:
            uri = self.get_connection_uri()
            engine = create_engine(uri)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")
```

**Security Best Practices:**
- Never store rendered URIs to disk
- Use `.env` files for local development (gitignored)
- Use environment variables in CI/CD
- Support external secret managers (future: AWS Secrets Manager, 1Password, etc.)
- Fail fast with clear errors if secrets are missing

**Example `.env` file** (gitignored):
```bash
# Production warehouse
PROD_DB_PASSWORD=supersecret123
PROD_SNOWFLAKE_ACCOUNT=xy12345.us-east-1

# Development
DEV_DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/dev_warehouse
```

### Database Abstraction

Use **SQLAlchemy Core** (not ORM) for maximum compatibility:

```python
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, select, inspect

class DatabaseClient:
    def __init__(self, connection_uri: str, agents_schema: str = "_agents"):
        self.engine = create_engine(connection_uri)
        self.schema = agents_schema
        self.metadata = MetaData()

    def ensure_schema_exists(self):
        """Create _agents schema if it doesn't exist"""
        inspector = inspect(self.engine)
        schemas = inspector.get_schema_names()

        if self.schema not in schemas:
            with self.engine.connect() as conn:
                # Dialect-specific schema creation
                conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
                conn.commit()

    def ensure_table_exists(self):
        """Create _agents._agents table if it doesn't exist"""
        table = Table(
            "_agents",
            self.metadata,
            Column("resource_type", String(255), nullable=False),
            Column("resource_name", String(255), nullable=False),
            Column("description", Text),
            Column("full_markdown", Text),
            schema=self.schema,
        )

        # Create if not exists (idempotent)
        table.create(self.engine, checkfirst=True)

    def pull_all_resources(self, schema_filter: str = None) -> list[Resource]:
        """Query all rows from _agents._agents"""
        # Implementation with optional schema filtering
        pass

    def push_resources(self, resources: list[Resource], backup: bool = True):
        """Upsert resources to _agents._agents"""
        # Transaction-wrapped upsert
        pass

    def get_diff(self, resources: list[Resource]) -> Diff:
        """Compare local resources to database state"""
        pass
```

**Supported databases** (initially):
- PostgreSQL
- MySQL
- SQLite
- DuckDB
- Snowflake (via snowflake-sqlalchemy)
- BigQuery (via sqlalchemy-bigquery)

### Models

```python
from pydantic import BaseModel, Field, validator
from typing import Literal, Optional

class Resource(BaseModel):
    """Complete resource - metadata defines everything"""
    resource_type: str = Field(..., description="Type: global, domain, table, column, etc.")
    resource_name: str = Field(..., description="Identifier like 'ecommerce.orders' or 'global'")
    target_schema: str = Field(default="_agents", description="DB schema to sync to")
    description: Optional[str] = Field(None, description="Short summary for indexing")
    full_markdown: str = Field(..., description="Everything after frontmatter")

    # Tracking
    source_file: Optional[Path] = Field(None, description="Local file path")

    @validator('resource_name')
    def validate_resource_name(cls, v):
        # Basic validation - ensure not empty
        if not v or not v.strip():
            raise ValueError("resource_name cannot be empty")
        return v.strip()

class ConnectionConfig(BaseModel):
    """Connection config from AGENTS.md frontmatter"""
    sqlalchemy_uri: str = Field(..., description="SQLAlchemy URI with Jinja2 templates")
    default_target_schema: str = Field(default="_agents", description="Default schema for resources")
    display_name: Optional[str] = Field(None, description="Human-readable connection name")

    def get_rendered_uri(self, env: dict[str, str]) -> str:
        """Render Jinja2 template with environment variables"""
        from jinja2 import Template, StrictUndefined, TemplateSyntaxError, UndefinedError

        try:
            template = Template(self.sqlalchemy_uri, undefined=StrictUndefined)
            rendered = template.render(env=env)
            return rendered
        except TemplateSyntaxError as e:
            raise ValueError(f"Invalid template syntax in sqlalchemy_uri: {e}")
        except UndefinedError as e:
            raise ValueError(f"Missing environment variable in sqlalchemy_uri: {e}")

class WorkspaceConfig(BaseModel):
    """Root AGENTS.md frontmatter"""
    version: int = 1
    default_connection: Optional[str] = None
    settings: dict = Field(default_factory=dict)
```

### File System Operations

```python
from pathlib import Path
import frontmatter
from collections import defaultdict

class FileSystemManager:
    def __init__(self, workspace_root: Path):
        self.root = workspace_root

    def load_workspace_config(self) -> WorkspaceConfig:
        """Load root AGENTS.md"""
        agents_file = self.root / "AGENTS.md"
        if not agents_file.exists():
            raise ValueError(f"No AGENTS.md found in {self.root}")

        post = frontmatter.load(agents_file)
        return WorkspaceConfig(**post.metadata)

    def load_connection_config(self, connection_name: str) -> ConnectionConfig:
        """Load connection AGENTS.md"""
        agents_file = self.root / connection_name / "AGENTS.md"
        if not agents_file.exists():
            raise ValueError(f"No AGENTS.md found in {connection_name}/")

        post = frontmatter.load(agents_file)
        return ConnectionConfig(**post.metadata)

    def discover_resources(
        self,
        connection_name: str,
        target_schema_filter: Optional[str] = None
    ) -> list[Resource]:
        """
        Discover ALL .md files in connection folder (except AGENTS.md).
        File location doesn't matter - metadata is source of truth.
        """
        connection_dir = self.root / connection_name
        resources = []

        for md_file in connection_dir.rglob("*.md"):
            # Skip AGENTS.md files
            if md_file.name == "AGENTS.md":
                continue

            # Skip dotfiles
            if md_file.name.startswith('.'):
                continue

            # Parse frontmatter
            post = frontmatter.load(md_file)

            # Create resource (Pydantic validation)
            resource = Resource(
                resource_type=post.metadata['resource_type'],
                resource_name=post.metadata['resource_name'],
                target_schema=post.metadata.get('target_schema', '_agents'),
                description=post.metadata.get('description'),
                full_markdown=post.content,
                source_file=md_file
            )

            # Filter by target_schema if specified
            if target_schema_filter and resource.target_schema != target_schema_filter:
                continue

            resources.append(resource)

        return resources

    def group_by_target_schema(self, resources: list[Resource]) -> dict[str, list[Resource]]:
        """Group resources by their target_schema for batch operations"""
        grouped = defaultdict(list)
        for resource in resources:
            grouped[resource.target_schema].append(resource)
        return dict(grouped)
```

### Sync Engine

```python
class SyncEngine:
    def __init__(self, workspace: FileSystemManager, db: DatabaseClient):
        self.workspace = workspace
        self.db = db

    def diff(
        self,
        connection_name: str,
        target_schema_filter: Optional[str] = None
    ) -> Diff:
        """Compare local files to database state"""
        # 1. Discover local resources
        local_resources = self.workspace.discover_resources(
            connection_name,
            target_schema_filter=target_schema_filter
        )

        # 2. Group by target_schema
        by_schema = self.workspace.group_by_target_schema(local_resources)

        # 3. For each schema, query database and compare
        diffs = {}
        for schema, resources in by_schema.items():
            remote_resources = self.db.pull_all_resources(schema=schema)
            diffs[schema] = self._compute_diff(resources, remote_resources)

        return diffs

    def push(
        self,
        connection_name: str,
        dry_run: bool = False,
        force: bool = False,
        target_schema_filter: Optional[str] = None
    ):
        """
        Push local files to database (deterministic).
        Database state will match local files exactly.
        """
        # 1. Discover local files (metadata tells us where to sync)
        local_resources = self.workspace.discover_resources(
            connection_name,
            target_schema_filter=target_schema_filter
        )

        # 2. Group by target_schema for batch operations
        by_schema = self.workspace.group_by_target_schema(local_resources)

        # 3. Get diff to show what will change
        diff = self.diff(connection_name, target_schema_filter)

        # 4. Show summary
        self._print_diff_summary(diff)

        # 5. Confirm (unless force or dry_run)
        if not dry_run and not force:
            if not self._confirm_push(diff):
                return

        # 6. Execute push (one transaction per schema)
        if not dry_run:
            for schema, resources in by_schema.items():
                # Deterministic sync: DB = local files
                # This will DELETE resources in DB not in local files!
                self.db.sync_resources(schema, resources)

    def status(self, connection_name: str) -> StatusReport:
        """Show sync status (like git status)"""
        diff = self.diff(connection_name)
        return self._format_status(diff)
```

### CLI with Typer + Rich

```python
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from typing import Optional

# Main app
app = typer.Typer(
    name="db-agents",
    help="Sync DB-AGENTS metadata between databases and local files",
    add_completion=False
)

console = Console()

# Subcommand groups
db_app = typer.Typer(help="Manage database connections")
resource_app = typer.Typer(help="Inspect and manage resources")

app.add_typer(db_app, name="db")
app.add_typer(resource_app, name="resource")

# Core commands
@app.command()
def init(
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
):
    """Initialize DB-AGENTS workspace"""
    pass

@app.command()
def diff(
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
    file: Optional[str] = typer.Argument(None, help="Specific file to diff"),
):
    """Compare local files to database state"""
    pass

@app.command()
def push(
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
    all: bool = typer.Option(False, "--all", "-a"),
    target_schema: Optional[str] = typer.Option(None, "--target-schema", "-s"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Push local files to database"""
    pass

@app.command()
def status(
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
):
    """Show sync status (like git status)"""
    table = Table(title="Sync Status")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_row("global.md", "✓ synced")
    table.add_row("orders.md", "M modified")
    console.print(table)

@app.command()
def validate(
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
):
    """Validate local files without touching database"""
    pass

@app.command()
def check(
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
    strict: bool = typer.Option(False, "--strict", help="Fail on warnings"),
):
    """Check workspace health and completeness"""
    console.print("[bold blue]Checking workspace health...[/bold blue]")
    # Run comprehensive checks
    pass

@app.command()
def migrate(
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
    all: bool = typer.Option(False, "--all", "-a"),
):
    """Create/update _agents._agents table"""
    pass

# db subcommands
@db_app.command("list")
def db_list():
    """List all database connections"""
    table = Table(title="Available Connections")
    table.add_column("Connection", style="cyan")
    table.add_column("URI", style="dim")
    table.add_column("Status", style="green")
    table.add_column("Resources", style="magenta")
    table.add_row("prod-warehouse", "postgresql://user:***@prod.example.com/warehouse", "✓ Connected", "12")
    console.print(table)

@db_app.command("test")
def db_test(connection: str):
    """Test database connection"""
    with console.status(f"[bold blue]Testing connection to {connection}..."):
        # Test connection
        pass
    console.print(f"[bold green]✓[/bold green] Successfully connected to {connection}")

@db_app.command("info")
def db_info(connection: str):
    """Show connection details"""
    pass

# resource subcommands
@resource_app.command("list")
def resource_list(
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by resource_type"),
    schema: Optional[str] = typer.Option(None, "--schema", "-s", help="Filter by target_schema"),
    remote: bool = typer.Option(False, "--remote", "-r", help="Query database instead of local"),
):
    """List resources"""
    table = Table(title="Resources in prod-warehouse")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Description", style="dim")
    table.add_column("File", style="magenta")
    table.add_row("global", "global", "Warehouse conventions", "global.md")
    table.add_row("domain", "revenue_analysis", "Revenue guidelines", "revenue_analysis.md")
    console.print(table)

@resource_app.command("show")
def resource_show(
    resource_name: str,
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
):
    """Show resource details with rendered markdown"""
    from rich.markdown import Markdown
    # Load resource
    md = Markdown("# Resource content here...")
    console.print(md)

@resource_app.command("search")
def resource_search(
    query: str,
    connection: Optional[str] = typer.Option(None, "--connection", "-c"),
):
    """Full-text search in resources"""
    pass
```

## Dependencies

```toml
[project]
name = "db-agents-cli"
version = "0.1.0"
description = "Sync tool for DB-AGENTS metadata"
dependencies = [
    "typer[all]>=0.12.0",        # CLI framework with rich support
    "rich>=13.7.0",               # Beautiful terminal output
    "sqlalchemy>=2.0.0",          # Database abstraction
    "pydantic>=2.6.0",            # Data validation
    "python-frontmatter>=1.1.0",  # YAML frontmatter parsing
    "pyyaml>=6.0.1",              # YAML config files
    "python-dotenv>=1.0.0",       # .env file support
    "jinja2>=3.1.0",              # Template rendering for connection URIs
    "click>=8.1.7",               # CLI utilities (typer dependency)
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.3.0",
]

# Database drivers (user installs as needed)
postgres = ["psycopg2-binary>=2.9.9"]
mysql = ["pymysql>=1.1.0"]
snowflake = ["snowflake-sqlalchemy>=1.5.0"]
bigquery = ["sqlalchemy-bigquery>=1.9.0"]

[project.scripts]
db-agents = "db_agents_cli.main:app"
dba = "db_agents_cli.main:app"  # Short alias for faster typing

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Implementation Phases

### Phase 1: Core Foundation (MVP)
- [ ] Project setup with uv
- [ ] Basic file structure
- [ ] Pydantic models for validation (Resource, ConnectionConfig, WorkspaceConfig)
- [ ] Jinja2 template rendering for connection URIs with env var support
- [ ] Frontmatter parsing (read/write) with python-frontmatter
- [ ] SQLAlchemy database client (PostgreSQL only initially)
- [ ] ConnectionManager with secret handling
- [ ] `init` command (create workspace + connection AGENTS.md)
- [ ] `diff` command (basic comparison)
- [ ] `push` command (deterministic sync with deletions)
- [ ] `validate` command (frontmatter + schema validation)
- [ ] `db list` / `db test` commands
- [ ] Basic Rich output with tables and progress bars

**Deliverable:** Can push markdown files to PostgreSQL deterministically with validation

### Phase 2: Enhanced UX
- [ ] `status` command (git-style status view)
- [ ] `check` command (comprehensive workspace health check)
- [ ] `resource list` / `resource show` / `resource search` commands
- [ ] `db info` command with detailed connection stats
- [ ] Enhanced `diff` command with color-coded output
- [ ] Interactive prompts for dangerous operations
- [ ] Progress bars for large syncs
- [ ] Better error messages with suggestions
- [ ] `--dry-run` mode for push
- [ ] Deletion warnings with summary

**Deliverable:** Production-ready tool with great UX for single database type

### Phase 3: Multi-Database Support
- [ ] Support MySQL
- [ ] Support SQLite
- [ ] Support DuckDB
- [ ] Support Snowflake
- [ ] Support BigQuery
- [ ] Database driver auto-detection
- [ ] Connection testing utilities

**Deliverable:** Works with major SQL databases

### Phase 4: Advanced Features
- [ ] `migrate` command for table creation
- [ ] `connections` command for management
- [ ] Schema mapping configuration
- [ ] Backup/restore functionality
- [ ] Git-like staged changes (optional)
- [ ] Watch mode (`db-agents watch`)
- [ ] Pre-commit hooks integration
- [ ] Resource reference validation
- [ ] Link checking in markdown

**Deliverable:** Feature-complete tool

### Phase 5: Ecosystem
- [ ] Comprehensive documentation
- [ ] Example repositories
- [ ] CI/CD templates (GitHub Actions, etc.)
- [ ] VS Code extension (syntax highlighting for frontmatter)
- [ ] Web UI for browsing (optional)
- [ ] Terraform/Pulumi providers (optional)

## Open Questions

1. **Deletion semantics**: Should `push` delete database entries not present in local files?
   - **✓ RESOLVED**: Yes, v1.0 is deterministic (DB = local files)
   - Push is source-of-truth from git
   - Warn loudly when resources will be deleted
   - Extra warnings if `resource_type=global` would be deleted

2. **Conflict resolution**: How to handle concurrent modifications?
   - **Proposal**: Timestamp-based (last-write-wins) with warnings
   - Future: Track hashes for 3-way merge

3. **Large deployments**: How to handle 1000+ resources?
   - **Proposal**: Schema-scoped pulls, parallel processing
   - Consider pagination for pull operations

4. **Authentication**: How to handle database credentials securely?
   - **✓ RESOLVED**: Use Jinja2 templates in `sqlalchemy_uri` with `{{ env.VAR_NAME }}` syntax
   - Support `.env` files via python-dotenv
   - Never store rendered URIs or plaintext passwords in config files
   - Future: Add keyring integration, AWS Secrets Manager, etc.

5. **Schema creation**: Should tool auto-create `_agents` schema?
   - **Proposal**: Yes, with confirmation prompt
   - `migrate` command should be explicit and safe

6. **Multi-schema support**: Should one connection support multiple DB schemas?
   - **✓ RESOLVED**: Yes, via `target_schema` metadata field
   - Each resource specifies where it syncs to
   - Can have resources syncing to different schemas in same connection

7. **Pull implementation**: When should we add pull functionality?
   - **Proposal**: Not in v1.0 - defer to v2.0+
   - v1.0 is deterministic push-only (git as source of truth)
   - Pull adds complexity: merge conflicts, file organization, conflict resolution
   - Use `diff` command to see what's in DB vs local

8. **File organization**: Should we enforce any structure?
   - **✓ RESOLVED**: No! Metadata is source of truth
   - Folder structure is for humans only
   - Files can be flat, nested, grouped by domain - whatever works

9. **Versioning**: Should we track metadata versions?
   - **Proposal**: Not in v1, but add `version` column to table schema for future
   - Git is the version control mechanism

8. **Testing**: How to test against real databases?
   - **Proposal**: Use pytest with docker-compose for integration tests
   - Fixtures for SQLite (fast unit tests)

## Success Metrics

- Users can sync metadata in < 5 commands after installing
- Support for 5+ major SQL databases
- < 100ms command startup time
- Zero data loss during sync operations
- Clear, actionable error messages
- Works with databases containing 100+ resources without performance issues

## Non-Goals (v1)

- Web UI for editing (CLI-first)
- Real-time sync / watch mode (can be Phase 4)
- Multi-user collaboration features (Git handles this)
- Built-in CI/CD pipelines (provide examples instead)
- Metrics/analytics collection
- Support for NoSQL databases

## Questions for Review

1. ~~Is the folder structure intuitive?~~ **RESOLVED**: No enforced structure, organize however you want!
2. ~~Should we support alternative layouts?~~ **RESOLVED**: All layouts work - metadata is source of truth
3. Is YAML frontmatter the right choice vs TOML or JSON? **Decision: YAML (markdown convention)**
4. ~~Should connection configs be YAML or TOML?~~ **RESOLVED**: Markdown with YAML frontmatter (AGENTS.md)
5. Should we include a `db-agents new` command to scaffold resource files?
6. Do we need a `db-agents search` command to find resources locally?
7. ~~Should markdown files be named `{resource_name}.md`?~~ **RESOLVED**: Arbitrary names allowed
8. Should v1.0 include pull, or defer to v2.0? **Decision: Defer - v1.0 is push-only**
9. How aggressive should deletion warnings be? (Require `--force`? Require typing resource name?)

---

**Next Steps:**
1. Review this plan and gather feedback
2. Create GitHub repository
3. Set up uv project structure
4. Begin Phase 1 implementation
5. Create example DB-AGENTS workspace for testing
