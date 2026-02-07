---
sqlalchemy_uri: "sqlite:///../jaffle_shop.db"
default_target_schema: _agents
display_name: "Jaffle Shop"
---

# Jaffle Shop Database

E-commerce database for the fictional Jaffle Shop coffee company.

## Data Architecture

This database follows a medallion-style architecture:

### Bronze Layer (Raw)
- `raw_customers` - Customer master data
- `raw_orders` - Order transactions
- `raw_payments` - Payment records

### Silver Layer (Staging)
- `staging_customers` - Cleaned customer data
- `staging_orders` - Standardized orders
- `staging_payments` - Normalized payments

### Gold Layer (Analytics)
- `analytics_customers` - Customer lifetime value metrics
- `analytics_orders` - Enriched order data with payment totals

## Data Quality

All raw tables are loaded daily via ETL from the operational database.
Staging and analytics tables are rebuilt on each dbt run.

## Access Patterns

- For customer analysis: Use `analytics_customers`
- For order analysis: Use `analytics_orders`
- For operational queries: Use `raw_*` tables directly
