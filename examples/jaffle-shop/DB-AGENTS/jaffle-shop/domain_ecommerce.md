---
resource_type: domain
resource_name: ecommerce
target_schema: _agents
description: E-commerce domain covering customers, orders, and payments
---

# E-commerce Domain

## Overview

The e-commerce domain contains all data related to customer transactions,
including customer profiles, order history, and payment processing.

## Domain Ownership

- **Team**: E-commerce Analytics
- **Lead**: Sarah Chen (sarah@jaffleshop.com)
- **Stakeholders**: Finance, Customer Success, Product

## Key Entities

### Customers
The customer entity represents individuals who have created accounts and
may place orders.

**Source of Truth**: `analytics_customers`

**Key Metrics**:
- Customer Lifetime Value (CLV)
- First Order Date
- Most Recent Order Date
- Total Number of Orders

### Orders
Orders represent purchase transactions made by customers.

**Source of Truth**: `analytics_orders`

**Key Metrics**:
- Order Volume (daily, weekly, monthly)
- Average Order Value (AOV)
- Order Status Distribution

### Payments
Payment records track how orders were paid for.

**Source of Truth**: `staging_payments`

**Key Metrics**:
- Payment Method Mix
- Payment Success Rate
- Average Payment Amount

## Business Rules

### Order Lifecycle
1. **Created**: Order is placed by customer
2. **Completed**: Order has been fulfilled and shipped
3. **Returned**: Order was returned by customer

### Payment Processing
- Multiple payments can be associated with a single order
- Payment amounts are stored in cents in raw data
- Converted to dollars in staging and analytics

### Customer Segmentation
Customers are categorized by order frequency:
- **New**: 1 order
- **Repeat**: 2-5 orders
- **Loyal**: 6+ orders

## Common Analytics Questions

### Customer Cohort Analysis
"How do customers from different acquisition months compare in retention?"

Use `analytics_customers` with date bucketing on `first_order`.

### Order Trends
"What is our week-over-week order growth?"

Use `analytics_orders` grouped by `order_date`.

### Payment Method Preference
"Which payment methods are most popular?"

Use `staging_payments` grouped by `payment_method`.

## Data Lineage

```
raw_customers -> staging_customers -> analytics_customers
raw_orders    -> staging_orders    -> analytics_orders
raw_payments  -> staging_payments  -> (joined into analytics_orders)
```

## Known Limitations

1. **Historical Data**: Only 2 years of raw data retained
2. **Customer Merges**: Duplicate customers not deduplicated
3. **Returns**: Return reasons not captured in database
4. **Payment Failures**: Failed payment attempts not tracked

## Useful Queries

### Customer Acquisition by Month
```sql
SELECT
    strftime('%Y-%m', first_order) AS cohort_month,
    COUNT(*) AS customers_acquired
FROM analytics_customers
GROUP BY cohort_month
ORDER BY cohort_month;
```

### Top Customers by Revenue
```sql
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.number_of_orders,
    SUM(o.amount) AS lifetime_value
FROM analytics_customers c
JOIN analytics_orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, customer_name, c.number_of_orders
ORDER BY lifetime_value DESC
LIMIT 10;
```

## Related Domains

- **Finance**: Revenue recognition and accounting
- **Marketing**: Campaign attribution and ROI
- **Customer Success**: Customer health scoring
