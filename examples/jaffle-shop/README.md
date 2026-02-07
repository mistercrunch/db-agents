## Jaffle Shop Example

Complete example of using DB-AGENTS with the dbt Jaffle Shop database.

## Overview

This example demonstrates DB-AGENTS documentation for a realistic e-commerce database
based on dbt's classic "Jaffle Shop" tutorial.

### Database Structure

- **Raw Layer**: `raw_customers`, `raw_orders`, `raw_payments`
- **Staging Layer**: `staging_customers`, `staging_orders`, `staging_payments`
- **Analytics Layer**: `analytics_customers`, `analytics_orders`

### Documentation Included

- **Global**: Database-wide conventions and best practices
- **Domain**: E-commerce domain documentation
- **Tables**: Detailed documentation for key tables
  - `analytics_customers` - Customer dimension with metrics
  - `analytics_orders` - Order fact table with revenue
  - `staging_payments` - Cleaned payment data

## Quick Start

### 1. Set up the database

The database is already included! It contains the **official dbt jaffle shop dataset**:
- 100 customers
- 99 orders
- 113 payments

To regenerate (optional):
```bash
cd examples/jaffle-shop
python3 setup_database.py
```

### 2. Validate the documentation

```bash
cd DB-AGENTS
dba validate
```

You should see:
```
✓ All files valid in jaffle-shop
5 resource(s) found
```

### 3. View what would be synced

```bash
dba diff
```

### 4. Push to database

```bash
dba push
```

This creates the `_agents` table and populates it with your documentation.

### 5. Query the documentation

```bash
sqlite3 ../jaffle_shop.db "SELECT resource_type, resource_name, description FROM _agents"
```

## Resource Types Demonstrated

### Global Resource
File: `global.md`
- Database-wide naming conventions
- Data refresh schedules
- Common queries
- Data quality checks

### Domain Resource
File: `domain_ecommerce.md`
- Domain ownership and stakeholders
- Key entities and metrics
- Business rules
- Data lineage diagrams

### Table Resources
Files: `analytics_customers.md`, `analytics_orders.md`, `staging_payments.md`
- Full schema documentation
- Data lineage
- Business logic explanation
- Usage examples with SQL
- Data quality checks
- Known limitations

## Folder Structure

```
jaffle-shop/
├── setup_database.py         # Script to create sample database
├── jaffle_shop.db             # SQLite database (created by script)
├── README.md                  # This file
└── DB-AGENTS/
    ├── AGENTS.md              # Workspace config
    └── jaffle-shop/
        ├── AGENTS.md          # Connection config
        ├── global.md          # Global conventions
        ├── domain_ecommerce.md    # Domain documentation
        ├── analytics_customers.md  # Customer table
        ├── analytics_orders.md     # Orders table
        └── staging_payments.md     # Payments table
```

## Key Features Demonstrated

### 1. Resource Organization
Files are organized by table name for easy navigation, but the tool
would work equally well with nested folders or any other structure.

### 2. Comprehensive Documentation
Each resource includes:
- Purpose and business context
- Complete schema with descriptions
- Data lineage diagrams
- SQL usage examples
- Data quality checks
- Known limitations

### 3. Different Resource Types
- `global` - Database-wide conventions
- `domain` - Business domain documentation
- `table` - Individual table documentation

### 4. Rich Metadata
All frontmatter includes:
- `resource_type` - Type classification
- `resource_name` - Unique identifier
- `target_schema` - Where to sync (_agents)
- `description` - Short summary

## Testing the Workflow

### Modify a File

Edit any `.md` file, then:

```bash
dba diff
# See: M <filename> (modified)

dba push
# Syncs changes to database
```

### Add a New Table

Create `raw_customers.md`:

```markdown
---
resource_type: table
resource_name: raw_customers
target_schema: _agents
description: Raw customer data from operational database
---

# raw_customers

Source table containing customer master data...
```

Then:
```bash
dba validate  # Check syntax
dba diff      # See new file
dba push      # Add to database
```

### Remove Documentation

```bash
rm staging_payments.md
dba diff
# See: D staging_payments (will be deleted)

dba push
# Removes from database (deterministic sync)
```

## Real-World Usage

This example mirrors how you'd document a real data warehouse:

1. **Start with global conventions** - Naming, standards, schedules
2. **Add domain documentation** - Business context, ownership, key metrics
3. **Document critical tables** - Most-used tables get detailed docs
4. **Iterate and improve** - Add examples, queries, gotchas as you learn

## Next Steps

- Explore the markdown files to see documentation examples
- Modify documentation and push changes
- Query the `_agents` table to see how documentation is stored
- Try organizing files differently (flat vs. nested)
- Add your own resource types (column, metric, etc.)

## Tips

- Use the global resource for database-wide patterns
- Use domains to group related tables and explain business context
- Include SQL examples in table documentation
- Document known limitations and gotchas
- Keep descriptions short - full detail goes in markdown body
