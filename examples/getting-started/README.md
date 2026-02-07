# Getting Started Example

This directory contains a complete example DB-AGENTS workspace demonstrating basic usage.

## Setup

1. Install db-agents-cli:
```bash
uv pip install -e ".[postgres]"
```

2. Set up environment variables (if using PostgreSQL):
```bash
# Create .env file
cat > .env << EOF
DB_PASSWORD=your_password_here
EOF
```

3. Initialize and explore:
```bash
# Validate the example workspace
cd DB-AGENTS
dba validate

# Check connections
dba db list

# See what would be pushed (requires real database)
dba diff

# Push to database (requires real database)
dba push
```

## Workspace Structure

```
DB-AGENTS/
├── AGENTS.md              # Workspace configuration
└── example-db/            # Connection folder
    ├── AGENTS.md          # Connection configuration
    ├── global.md          # Global documentation
    └── users_table.md     # Table resource
```

## Files

### Root Configuration (AGENTS.md)

Workspace-level settings. Sets `example-db` as the default connection.

### Connection Configuration (example-db/AGENTS.md)

Connection details including SQLAlchemy URI with environment variable templates.

### Resource Files

- **global.md** - Global documentation for the database
- **users_table.md** - Documentation for a users table

## Try It Out

### 1. Validate files

```bash
dba validate
```

### 2. Add a new resource

```bash
cat > DB-AGENTS/example-db/orders_table.md << 'EOF'
---
resource_type: table
resource_name: orders
target_schema: _agents
description: Customer orders
---

# orders

Order information table.

## Columns
- id - Order ID (PK)
- user_id - Foreign key to users
- created_at - Order timestamp
- status - Order status
EOF

dba validate
```

### 3. See the diff

```bash
dba diff
```

### 4. Push to database (requires real database)

```bash
dba push
```

### 5. Modify a file

Edit any resource file and run `dba diff` to see the changes.

### 6. Test deletion

Remove a resource file and run `dba diff` to see the deletion warning.

## Next Steps

- Organize files in subdirectories (flat structure vs. nested)
- Add more resource types (domains, columns, etc.)
- Connect to a real database and test the full workflow
- Set up multiple connections for different environments
