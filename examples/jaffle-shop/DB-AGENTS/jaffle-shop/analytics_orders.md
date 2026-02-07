---
resource_type: table
resource_name: analytics_orders
target_schema: _agents
description: Order fact table with payment totals for analytics
---

# analytics_orders

Fact table containing all orders with payment amounts rolled up from payment records.

## Purpose

This table provides order-level data enriched with payment information.
Use this for order volume analysis, revenue reporting, and trend analysis.

## Grain

One row per order (unique on `order_id`).

## Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `order_id` | INTEGER | NOT NULL | Unique order identifier (PK) |
| `customer_id` | INTEGER | NULL | Customer who placed the order (FK) |
| `order_date` | TEXT | NULL | Date order was placed (YYYY-MM-DD) |
| `status` | TEXT | NULL | Order status (completed, returned) |
| `amount` | REAL | NULL | Total order amount in dollars |

## Primary Key

- `order_id`

## Foreign Keys

- `customer_id` → `analytics_customers.customer_id`

## Indexes

Consider adding:
- `order_date` for time-series queries
- `customer_id` for customer analysis

## Data Lineage

```
raw_orders              raw_payments
    ↓                        ↓
staging_orders          staging_payments
    ↓                        ↓
    └───────────────┬────────┘
                    ↓
            analytics_orders
```

## Refresh Schedule

- **Built by**: dbt model `analytics_orders.sql`
- **Refresh**: Daily at 4:00 AM UTC
- **Dependencies**: `staging_orders`, `staging_payments`

## Business Logic

### Amount Calculation
- Sum of all payment amounts for the order
- NULL if order has no payments
- Already converted from cents to dollars (via staging layer)

### Status Values
- `completed`: Order successfully fulfilled
- `returned`: Order was returned by customer
- NULL: Unknown status (data quality issue)

## Usage Examples

### Daily Revenue
```sql
SELECT
    order_date,
    COUNT(*) AS order_count,
    SUM(amount) AS total_revenue,
    AVG(amount) AS avg_order_value
FROM analytics_orders
WHERE status = 'completed'
GROUP BY order_date
ORDER BY order_date;
```

### Order Status Distribution
```sql
SELECT
    status,
    COUNT(*) AS order_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS pct_of_total
FROM analytics_orders
GROUP BY status;
```

### Top Revenue Days
```sql
SELECT
    order_date,
    COUNT(*) AS order_count,
    SUM(amount) AS daily_revenue
FROM analytics_orders
WHERE status = 'completed'
GROUP BY order_date
ORDER BY daily_revenue DESC
LIMIT 10;
```

### Customer Order History
```sql
SELECT
    c.first_name || ' ' || c.last_name AS customer_name,
    o.order_id,
    o.order_date,
    o.status,
    o.amount
FROM analytics_customers c
JOIN analytics_orders o ON c.customer_id = o.customer_id
WHERE c.customer_id = 1
ORDER BY o.order_date DESC;
```

## Data Quality

### Expected Checks
- No duplicate `order_id` values
- All `customer_id` values should exist in `analytics_customers`
- `amount` should be >= 0 (or NULL)
- `order_date` should not be in the future
- `status` should be one of: completed, returned

### Known Issues
- Some orders may have NULL amounts (payments not yet processed)
- Returned orders still count toward revenue (no adjustment made)

## Related Tables

- **Upstream**: `staging_orders`, `staging_payments`
- **Downstream**: Used in dashboards and reports
- **Joins**:
  - → `analytics_customers` via `customer_id` for customer info
  - → `staging_payments` via `order_id` for payment breakdowns

## Performance Considerations

- Table size: ~1K orders/day expected
- Annual volume: ~365K rows
- Queries on `order_date` are common - consider index
- Joins on `customer_id` are frequent - consider index

## Maintenance

### Data Retention
- Keep all historical orders
- No deletion policy

### Rebuild Strategy
- Full rebuild nightly (table is small)
- Consider incremental loads if volume exceeds 10M rows

## Common Pitfalls

1. **Don't use for real-time**: This table is batch-loaded daily
2. **Returns are not netted**: Include `status = 'completed'` to exclude returns
3. **NULL amounts**: Some orders may not have payments yet
4. **Duplicate prevention**: Don't join to `staging_payments` directly (use this table's pre-aggregated `amount`)

## Ownership

- **Team**: Analytics Engineering
- **Maintainer**: dbt model `analytics_orders.sql`
- **Stakeholders**: Finance, Operations, Executive Team

## Change Log

- **2024-01**: Initial creation
- **2024-02**: Added payment amount aggregation
- **2024-03**: Changed amount from cents to dollars
