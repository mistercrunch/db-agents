---
resource_type: global
resource_name: global
target_schema: _agents
description: Global conventions and documentation
---

# Example Database Documentation

## Overview

This is the global documentation for the example database. Use this file to document database-wide conventions, best practices, and general information.

## Naming Conventions

- **Tables**: Use snake_case for all table names (e.g., `user_orders`, `product_categories`)
- **Primary Keys**: Always name primary keys as `id`
- **Foreign Keys**: Use format `{table_singular}_id` (e.g., `user_id`, `product_id`)
- **Timestamps**: Use `created_at` and `updated_at` for audit fields

## Best Practices

### Query Performance

- Always filter on indexed columns
- Use appropriate JOIN types
- Avoid SELECT * in production queries

### Data Integrity

- Use foreign key constraints
- Set appropriate NOT NULL constraints
- Use CHECK constraints for data validation

## Common Queries

### Find active users
```sql
SELECT * FROM users WHERE is_active = true;
```

### Get recent orders
```sql
SELECT * FROM orders
WHERE created_at >= NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;
```

## Contact

For questions about this database, contact the data team.
