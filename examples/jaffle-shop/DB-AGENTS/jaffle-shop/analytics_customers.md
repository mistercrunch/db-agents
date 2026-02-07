---
resource_type: table
resource_name: analytics_customers
target_schema: _agents
description: Customer dimension with lifetime metrics and order history
---

# analytics_customers

Customer master table with aggregated metrics for analytics and reporting.

## Purpose

This table provides a complete view of each customer including their order history
and key behavioral metrics. Use this as the starting point for all customer analysis.

## Grain

One row per customer (unique on `customer_id`).

## Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `customer_id` | INTEGER | NOT NULL | Unique customer identifier (PK) |
| `first_name` | TEXT | NULL | Customer's first name |
| `last_name` | TEXT | NULL | Customer's last name |
| `first_order` | TEXT | NULL | Date of customer's first order (YYYY-MM-DD) |
| `most_recent_order` | TEXT | NULL | Date of customer's most recent order (YYYY-MM-DD) |
| `number_of_orders` | INTEGER | NULL | Total count of orders placed by customer |

## Primary Key

- `customer_id`

## Indexes

None currently. Consider adding index on `first_order` for cohort analysis.

## Data Lineage

```
raw_customers
  ↓ (clean & rename)
staging_customers
  ↓ (join & aggregate)
analytics_customers
```

Built from:
- `staging_customers`: Customer names
- `staging_orders`: Order dates for aggregation

## Refresh Schedule

- **Built by**: dbt model `analytics_customers.sql`
- **Refresh**: Daily at 4:00 AM UTC
- **Dependencies**: `staging_customers`, `staging_orders`

## Business Logic

### Number of Orders
- Counts all orders regardless of status
- Includes returned orders in the count
- NULL if customer has no orders

### First Order / Most Recent Order
- Based on `order_date` from orders table
- NULL if customer has no orders
- Dates are in YYYY-MM-DD format

## Usage Examples

### Customer Segmentation
```sql
SELECT
    CASE
        WHEN number_of_orders = 1 THEN 'New'
        WHEN number_of_orders BETWEEN 2 AND 5 THEN 'Repeat'
        WHEN number_of_orders >= 6 THEN 'Loyal'
        ELSE 'No Orders'
    END AS segment,
    COUNT(*) AS customer_count
FROM analytics_customers
GROUP BY segment;
```

### Cohort Analysis
```sql
SELECT
    strftime('%Y-%m', first_order) AS cohort,
    COUNT(*) AS customers,
    AVG(number_of_orders) AS avg_orders_per_customer,
    SUM(CASE WHEN number_of_orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS repeat_rate_pct
FROM analytics_customers
WHERE first_order IS NOT NULL
GROUP BY cohort
ORDER BY cohort;
```

### Customer Activity
```sql
SELECT
    customer_id,
    first_name || ' ' || last_name AS customer_name,
    number_of_orders,
    first_order,
    most_recent_order,
    JULIANDAY('now') - JULIANDAY(most_recent_order) AS days_since_last_order
FROM analytics_customers
WHERE number_of_orders > 0
ORDER BY days_since_last_order;
```

## Data Quality

### Expected Checks
- No duplicate `customer_id` values
- `number_of_orders` should be >= 0
- If `first_order` IS NOT NULL, then `number_of_orders` should be > 0
- `first_order` should be <= `most_recent_order`

### Known Issues
- Some customers may have NULL names (data entry issue in source system)
- Customers without orders will have NULL for all order-related fields

## Related Tables

- **Upstream**: `staging_customers`, `staging_orders`
- **Downstream**: None (this is a final analytics table)
- **Joins**:
  - → `analytics_orders` via `customer_id` to get order details
  - → `staging_payments` via orders to get payment information

## Maintenance

### Performance
- Table is small (<100K rows expected)
- Full rebuild is acceptable
- Consider incremental strategy if customer count exceeds 1M

### Data Retention
- All historical customers retained (no deletion policy)

## Ownership

- **Team**: Analytics Engineering
- **Maintainer**: dbt model `analytics_customers.sql`
- **Stakeholders**: Marketing, Customer Success

## Change Log

- **2024-01**: Initial creation
- **2024-02**: Added `number_of_orders` column
- **2024-03**: Standardized date format to YYYY-MM-DD
