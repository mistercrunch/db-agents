# DB-AGENTS CLI

A Python CLI tool for syncing DB-AGENTS metadata between local markdown files and database `_agents._agents` tables.

## Installation

### Using uv (recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Install with PostgreSQL support
source .venv/bin/activate
uv pip install -e ".[postgres]"

# Or install with other database drivers
uv pip install -e ".[mysql]"
uv pip install -e ".[snowflake]"
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[postgres]"
```

## Quick Start

### 1. Initialize a workspace

```bash
# Create a new workspace (both commands are equivalent)
dba init
```

This creates a `DB-AGENTS/` directory with a root `AGENTS.md` configuration file.

### 2. Add a database connection

```bash
# Interactive setup
dba init --connection prod-warehouse

# Or provide all details upfront
dba init \
  --connection prod-warehouse \
  --uri "postgresql://user:{{ env.DB_PASSWORD }}@host:5432/database" \
  --display-name "Production Warehouse"
```

This creates:
- `DB-AGENTS/prod-warehouse/AGENTS.md` - Connection configuration
- `DB-AGENTS/prod-warehouse/global.md` - Example resource file

### 3. Create resource files

Resource files are markdown files with YAML frontmatter. You can organize them however you want - the metadata determines where they sync to.

```bash
cat > DB-AGENTS/prod-warehouse/users_table.md << 'EOF'
---
resource_type: table
resource_name: users
target_schema: _agents
description: User accounts and authentication
---

# users

User accounts table with authentication information.

## Columns
- id (PK) - Unique user identifier
- username - Unique username
- email - User email address
- created_at - Account creation timestamp

## Usage Notes
- Always check `is_active` flag before authentication
- Email addresses are case-insensitive
EOF
```

### 4. Validate your files

```bash
dba validate

# Output:
# Validating connection: prod-warehouse
# ✓ All files valid in prod-warehouse
# 2 resource(s) found
```

### 5. Check what would change

```bash
dba diff

# Output:
# Connection: prod-warehouse
# URI: postgresql://user:***@host:5432/database
#
# Target Schema: _agents
#
# Added (2):
#   A prod-warehouse/global.md
#     → global: global
#   A prod-warehouse/users_table.md
#     → table: users
#
# Summary: 2 added, 0 modified, 0 deleted
```

### 6. Push to database

```bash
dba push

# Prompts for confirmation, then:
# ✓ Push completed for prod-warehouse
#
# Schema: _agents (2 change(s))
#   + 2 inserted
```

## Commands

### Core Commands

#### `dba init` (or `dba init`)

Initialize workspace or add a connection.

```bash
# Initialize workspace
dba init

# Add a connection interactively
dba init --connection prod

# Add connection with all details
dba init \
  --connection prod \
  --uri "postgresql://user:{{ env.DB_PASSWORD }}@host/db" \
  --display-name "Production"
```

#### `dba validate` (or `dba validate`)

Validate local files without touching the database.

```bash
# Validate all connections
dba validate

# Validate specific connection
dba validate --connection prod
```

Checks:
- Valid YAML frontmatter
- Required fields present (`resource_type`, `resource_name`)
- No duplicate resource names within same schema
- Parseable markdown content

#### `dba diff` (or `dba diff`)

Compare local files to database state.

```bash
# Diff default connection
dba diff

# Diff specific connection
dba diff --connection prod

# Filter by target schema
dba diff --target-schema _agents
```

#### `dba push` (or `dba push`)

Push local files to database (deterministic sync).

```bash
# Push with confirmation prompt
dba push

# Skip confirmation
dba push --force

# Dry run (show what would change)
dba push --dry-run

# Push specific schema only
dba push --target-schema _agents
```

**Important:** Push is deterministic - the database will match your local files exactly. Resources in the database but not in local files will be **deleted**!

### Database Management

#### `dba db list` (or `dba db list`)

List all connections with status.

```bash
dba db list

# Output:
# ┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┓
# ┃ Connection     ┃ URI                ┃ Status      ┃ Resources ┃
# ┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━┩
# │ prod-warehouse │ postgresql://...   │ ✓ Connected │ 5         │
# └────────────────┴────────────────────┴─────────────┴───────────┘
```

#### `dba db test <connection>` (or `dba db test <connection>`)

Test database connection.

```bash
dba db test prod

# Output:
# Testing connection: prod
# URI: postgresql://user:***@host/db
# ✓ Successfully connected to prod
# ℹ Table _agents._agents exists
# 5 resource(s) in database
```

## Configuration

### Workspace Configuration (`DB-AGENTS/AGENTS.md`)

```yaml
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

### Connection Configuration (`DB-AGENTS/<connection>/AGENTS.md`)

```yaml
---
sqlalchemy_uri: "postgresql://user:{{ env.DB_PASSWORD }}@host:5432/database"
default_target_schema: _agents
display_name: "Production Warehouse"
---

# Production Warehouse

PostgreSQL production warehouse containing all analytics data.
```

### Resource Files

```yaml
---
resource_type: table
resource_name: ecommerce.orders
target_schema: _agents
description: Order headers with customer info
---

# ecommerce.orders

Order-level information including customer, dates, and fulfillment status.

## Key Columns
- `order_id` (PK)
- `customer_id` (FK to customers)
- `order_date` (partition key)
```

**Metadata Fields:**
- `resource_type` - **Required** (global, domain, table, column, etc.)
- `resource_name` - **Required** (identifier like `ecommerce.orders` or `global`)
- `target_schema` - **Optional** (DB schema to sync to, defaults to `_agents`)
- `description` - **Optional** but recommended (short summary)

## Secret Management

Connection URIs support Jinja2 templates for environment variables:

```yaml
# Reference environment variables
sqlalchemy_uri: "postgresql://user:{{ env.DB_PASSWORD }}@host/db"

# Or reference entire connection string
sqlalchemy_uri: "{{ env.DATABASE_URL }}"
```

Create a `.env` file (gitignored):

```bash
DB_PASSWORD=supersecret123
DATABASE_URL=postgresql://user:pass@host/db
```

The tool automatically loads `.env` files using python-dotenv.

## Supported Databases

Currently tested with:
- PostgreSQL (via psycopg2-binary)
- SQLite (built-in)

Coming soon:
- MySQL
- Snowflake
- BigQuery
- DuckDB

Install database-specific drivers:

```bash
# PostgreSQL
uv pip install -e ".[postgres]"

# MySQL (when available)
uv pip install -e ".[mysql]"

# Snowflake (when available)
uv pip install -e ".[snowflake]"
```

## File Organization

**Files can be organized however you want!** The metadata in frontmatter determines where resources sync to, not the folder structure.

Valid layouts:

```
# Flat structure
prod-warehouse/
├── AGENTS.md
├── global.md
├── ecommerce_orders.md
└── analytics_metrics.md

# Grouped by schema
prod-warehouse/
├── AGENTS.md
├── core/
│   ├── global.md
│   └── finance_domain.md
└── product-analytics/
    └── events.md

# Grouped by type
prod-warehouse/
├── AGENTS.md
├── tables/
│   ├── orders.md
│   └── products.md
└── domains/
    └── revenue_analysis.md
```

All layouts work the same - the tool scans all `.md` files and reads their metadata.

## Development

### Running tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=src/db_agents_cli
```

### Code formatting

```bash
# Install ruff
uv pip install -e ".[dev]"

# Format code
ruff format src/ tests/

# Lint
ruff check src/ tests/
```

## Troubleshooting

### Connection failed

```
Error: Failed to connect: could not translate host name
```

**Solution:** Check your connection URI and ensure environment variables are set.

```bash
# Check if .env file exists
ls -la .env

# Test connection
dba db test <connection>
```

### Table does not exist

```
⚠ Table _agents._agents does not exist
ℹ Run 'dba push' to create and populate it
```

**Solution:** The table will be created automatically on first push:

```bash
dba push
```

### Invalid frontmatter

```
Error: Invalid AGENTS.md frontmatter in prod/: 1 validation error
```

**Solution:** Check your YAML syntax and ensure required fields are present:

```bash
# Validate files
dba validate

# Check the specific file
cat DB-AGENTS/prod/AGENTS.md
```

## Architecture

See [DESIGN.md](DESIGN.md) for detailed architecture and implementation plan.

**Key design decisions:**
- **Metadata is source of truth** - Folder structure is for humans only
- **Deterministic sync** - Database state = local files (push deletes orphaned resources)
- **Git-friendly** - All config and resources are markdown with YAML frontmatter
- **Secret-safe** - Jinja2 templates for sensitive values, never stored rendered

## Contributing

Phase 1 (MVP) is complete! Phase 2 will add:
- Enhanced UX (status, check commands)
- Better diff output with color-coded changes
- Resource inspection commands
- Interactive prompts for dangerous operations

See [DESIGN.md](DESIGN.md) for the full roadmap.

## License

[To be determined]
