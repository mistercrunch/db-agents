---
resource_type: table
resource_name: staging_payments
target_schema: _agents
description: Cleaned payment records with standardized amounts
---

# staging_payments

Staging table for payment records with cleaned data and standardized formatting.

## Purpose

This table provides cleaned payment data suitable for analytics. It's the
intermediate layer between raw data and final analytics tables.

## Grain

One row per payment transaction (unique on `payment_id`).

## Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `payment_id` | INTEGER | NOT NULL | Unique payment identifier (PK) |
| `order_id` | INTEGER | NULL | Associated order (FK) |
| `payment_method` | TEXT | NULL | How payment was made |
| `amount` | REAL | NULL | Payment amount in dollars |

## Primary Key

- `payment_id`

## Foreign Keys

- `order_id` → `staging_orders.order_id`

## Data Lineage

```
raw_payments
    ↓ (clean, convert cents to dollars)
staging_payments
```

## Refresh Schedule

- **Built by**: dbt model `staging_payments.sql`
- **Refresh**: Daily at 3:00 AM UTC
- **Dependencies**: `raw_payments`

## Transformations Applied

### Amount Conversion
- **Source**: Stored in cents (e.g., 1000 = $10.00)
- **Target**: Converted to dollars (e.g., 10.00)
- **Formula**: `amount / 100.0`

### Payment Method Standardization
- Values are lowercase in source, preserved as-is
- Known values: `credit_card`, `coupon`, `bank_transfer`, `gift_card`

## Business Logic

### Multiple Payments Per Order
Orders can have multiple payment records:
- Split payments across methods
- Partial refunds
- Gift card + credit card combinations

Use SUM when aggregating to order level.

## Usage Examples

### Payment Method Analysis
```sql
SELECT
    payment_method,
    COUNT(*) AS payment_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount
FROM staging_payments
GROUP BY payment_method
ORDER BY total_amount DESC;
```

### Order Payment Breakdown
```sql
SELECT
    order_id,
    payment_method,
    amount
FROM staging_payments
WHERE order_id = 1
ORDER BY amount DESC;
```

### Payment Method Combinations
```sql
SELECT
    order_id,
    COUNT(DISTINCT payment_method) AS methods_used,
    GROUP_CONCAT(payment_method) AS payment_methods,
    SUM(amount) AS total_amount
FROM staging_payments
GROUP BY order_id
HAVING COUNT(DISTINCT payment_method) > 1;
```

## Data Quality

### Expected Checks
- No duplicate `payment_id` values
- All `order_id` values should exist in `staging_orders`
- `amount` should be >= 0
- `payment_method` should be one of expected values

### Known Issues
- Some payments may have `amount = 0` (promotional codes)
- Payment method values are inconsistent in source data

## Related Tables

- **Upstream**: `raw_payments`
- **Downstream**: `analytics_orders` (aggregated)
- **Joins**: → `staging_orders` via `order_id`

## Maintenance

### Data Retention
- Keep 2 years of history (aligned with raw data retention)

### Performance
- Table is small (~5-10 payments per order)
- Full rebuild is acceptable

## Ownership

- **Team**: Analytics Engineering
- **Maintainer**: dbt model `staging_payments.sql`
- **Source System**: Payment processor API

## Change Log

- **2024-01**: Initial creation
- **2024-02**: Added amount conversion from cents to dollars
- **2024-03**: Standardized payment_method values
