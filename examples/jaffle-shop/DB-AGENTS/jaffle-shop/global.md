---
resource_type: global
resource_name: global
target_schema: _agents
description: Jaffle Shop database-wide conventions and guidelines
---

# Jaffle Shop Data Warehouse

## Purpose

The Jaffle Shop data warehouse provides analytics-ready data for business intelligence,
reporting, and data science use cases.

## Naming Conventions

### Tables
- **Raw tables**: `raw_<entity>` - Source data, loaded as-is
- **Staging tables**: `staging_<entity>` - Cleaned and standardized
- **Analytics tables**: `analytics_<entity>` - Business logic applied

### Columns
- **Primary Keys**: Always named `<entity>_id` (e.g., `customer_id`, `order_id`)
- **Foreign Keys**: Follow same pattern as primary keys
- **Timestamps**: Use `_date` suffix for dates, `_at` for datetimes
- **Monetary Values**: Store in smallest unit (cents) in raw, convert to dollars in staging

## Data Refresh Schedule

- **Raw tables**: Loaded daily at 2:00 AM UTC
- **Staging tables**: Rebuilt daily at 3:00 AM UTC (after raw loads)
- **Analytics tables**: Rebuilt daily at 4:00 AM UTC (after staging)

## Data Retention

- **Raw tables**: 2 years of history
- **Staging tables**: 2 years of history
- **Analytics tables**: All history (no deletion)

## Query Best Practices

### Performance
1. **Always filter on indexed columns** when possible
2. **Use analytics tables** for reporting - they're pre-aggregated
3. **Avoid SELECT *** - specify columns explicitly
4. **Use staging tables** for joins - they have proper data types

### Correctness
1. **Check date ranges** - data may have gaps
2. **Handle NULLs** - especially in outer joins
3. **Use analytics_customers** for customer metrics, not raw data
4. **Understand grain** - know the granularity of each table

## Common Queries

### Customer Lifetime Value
```sql
SELECT
    customer_id,
    first_name || ' ' || last_name AS customer_name,
    number_of_orders,
    first_order,
    most_recent_order
FROM analytics_customers
ORDER BY number_of_orders DESC;
```

### Daily Order Volume
```sql
SELECT
    order_date,
    COUNT(*) AS order_count,
    SUM(amount) AS total_revenue
FROM analytics_orders
GROUP BY order_date
ORDER BY order_date;
```

### Payment Method Mix
```sql
SELECT
    payment_method,
    COUNT(*) AS payment_count,
    SUM(amount) AS total_amount
FROM staging_payments
GROUP BY payment_method
ORDER BY total_amount DESC;
```

## Data Quality Checks

Run these queries regularly to ensure data quality:

```sql
-- Check for orphaned orders (orders without customers)
SELECT COUNT(*) FROM raw_orders
WHERE user_id NOT IN (SELECT id FROM raw_customers);

-- Check for negative payments
SELECT COUNT(*) FROM raw_payments WHERE amount < 0;

-- Check for future-dated orders
SELECT COUNT(*) FROM raw_orders WHERE order_date > DATE('now');
```

## Support

For questions or issues with the data warehouse:
- Data Engineering: data-eng@jaffleshop.com
- Analytics Team: analytics@jaffleshop.com
- On-call: PagerDuty "Data Platform" rotation
