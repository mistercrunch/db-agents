# DB-AGENTS CLI - Quick Start

A 5-minute guide to get started with db-agents-cli.

## Installation

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone <repo-url>
cd db-agents-cli
uv venv
source .venv/bin/activate
uv pip install -e ".[postgres]"

# Verify (both show help with no args)
dba
db-agents --help
```

## Basic Workflow

### 1. Initialize Workspace

```bash
# Create workspace
dba init

# Add a connection
dba init --connection my-db \
  --uri "postgresql://user:{{ env.DB_PASSWORD }}@host/db" \
  --display-name "My Database"
```

Creates:
```
DB-AGENTS/
├── AGENTS.md              # Workspace config
└── my-db/
    ├── AGENTS.md          # Connection config
    └── global.md          # Example resource
```

### 2. Create Resource Files

```bash
cat > DB-AGENTS/my-db/users.md << 'EOF'
---
resource_type: table
resource_name: users
target_schema: _agents
description: User accounts
---

# users

User accounts table with authentication info.

## Columns
- id - Primary key
- username - Login name
- email - Email address
EOF
```

### 3. Validate

```bash
dba validate

# Output:
# ✓ All files valid in my-db
# 2 resource(s) found
```

### 4. Preview Changes

```bash
dba diff

# Output:
# Target Schema: _agents
#   A my-db/global.md → global: global
#   A my-db/users.md → table: users
# Summary: 2 added, 0 modified, 0 deleted
```

### 5. Push to Database

```bash
# Set environment variables
export DB_PASSWORD="your-password"

# Push changes
dba push

# Confirms and syncs to database
```

## Common Commands

```bash
# List all connections
dba db list

# Test a connection
dba db test my-db

# Validate files
dba validate

# See what would change
dba diff

# Push changes (with confirmation)
dba push

# Push without confirmation
dba push --force

# Show version
dba version
```

## Directory Structure

```
your-project/
├── .env                   # Environment variables (gitignored)
└── DB-AGENTS/             # Workspace root
    ├── AGENTS.md          # Workspace config
    └── my-db/             # Connection folder (any name)
        ├── AGENTS.md      # Connection config
        └── *.md           # Resource files (any structure)
```

## Resource File Format

```yaml
---
resource_type: table           # Required: type of resource
resource_name: users           # Required: unique identifier
target_schema: _agents         # Optional: DB schema (default: _agents)
description: User accounts     # Optional: short description
---

# Your Markdown Content Here

Any markdown content after the frontmatter becomes the
documentation stored in the database.
```

## Environment Variables

Create `.env` file (gitignored):

```bash
# Database passwords
DB_PASSWORD=supersecret123
PROD_DB_PASSWORD=prod_secret

# Or entire connection strings
DATABASE_URL=postgresql://user:pass@host/db
```

Reference in AGENTS.md:

```yaml
---
sqlalchemy_uri: "postgresql://user:{{ env.DB_PASSWORD }}@host/db"
---
```

## File Organization

Organize files **however you want** - metadata determines sync behavior:

### Flat Structure
```
my-db/
├── AGENTS.md
├── global.md
├── users.md
└── orders.md
```

### Nested Structure
```
my-db/
├── AGENTS.md
├── core/
│   └── global.md
└── tables/
    ├── users.md
    └── orders.md
```

Both work identically!

## Supported Databases

- PostgreSQL (install with `.[postgres]`)
- SQLite (built-in)
- MySQL, Snowflake, BigQuery (coming soon)

## Next Steps

- Read [docs/CLI.md](docs/CLI.md) for full documentation
- See [examples/jaffle-shop/](examples/jaffle-shop/) for a complete working example
- Check [docs/DESIGN.md](docs/DESIGN.md) for architecture details

## Troubleshooting

### "Not in a DB-AGENTS workspace"
```bash
# Run init in your project directory
dba init
```

### "Failed to connect"
```bash
# Check environment variables
cat .env

# Test connection
dba db test my-db
```

### "Missing environment variable"
```bash
# Add to .env file
echo "DB_PASSWORD=your-password" >> .env

# Or export directly
export DB_PASSWORD="your-password"
```

## Pro Tips

1. **Use the short alias**: `dba` instead of `db-agents`
2. **Validate before push**: `dba validate && dba push`
3. **Review diffs carefully**: `dba diff` shows what will change
4. **Use dry-run**: `dba push --dry-run` to preview
5. **Check connections**: `dba db list` shows status
6. **Keep descriptions**: They make resources searchable

## Example Workflow

```bash
# Day 1: Setup
dba init
dba init --connection prod --uri "postgresql://..."
dba db test prod
✓ Connected

# Day 2: Add documentation
vim DB-AGENTS/prod/users.md
dba validate
✓ Valid
dba diff
# Shows: A users.md
dba push
✓ Synced

# Day 3: Update
vim DB-AGENTS/prod/users.md
dba diff
# Shows: M users.md
dba push
✓ Updated

# Day 4: Clean up
rm DB-AGENTS/prod/old_table.md
dba diff
# Shows: D old_table (WARNING)
dba push
✓ Deleted
```

That's it! You're ready to manage database documentation with db-agents-cli.
