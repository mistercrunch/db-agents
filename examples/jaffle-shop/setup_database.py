#!/usr/bin/env python3
"""Set up dbt Jaffle Shop sample database in SQLite.

This creates a SQLite database with the official dbt jaffle shop data
from https://github.com/dbt-labs/jaffle_shop

Tables created:
- Raw: raw_customers, raw_orders, raw_payments
- Staging: staging_customers, staging_orders, staging_payments
- Analytics: analytics_customers, analytics_orders
"""

import csv
import sqlite3
from pathlib import Path


def create_jaffle_shop_db():
    """Create jaffle shop database with real dbt sample data."""
    db_path = Path(__file__).parent / "jaffle_shop.db"

    # Remove existing database
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Note: SQLite doesn't support schemas like PostgreSQL
    # We'll use table name prefixes instead: raw_, staging_, analytics_

    # Create raw customers table
    cursor.execute("""
        CREATE TABLE raw_customers (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT
        )
    """)

    # Load from CSV
    csv_path = Path(__file__).parent / "raw_customers.csv"
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute(
                "INSERT INTO raw_customers VALUES (?, ?, ?)",
                (row["id"], row["first_name"], row["last_name"]),
            )

    # Create raw orders table
    cursor.execute("""
        CREATE TABLE raw_orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            order_date TEXT,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES raw_customers(id)
        )
    """)

    # Load from CSV
    csv_path = Path(__file__).parent / "raw_orders.csv"
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute(
                "INSERT INTO raw_orders VALUES (?, ?, ?, ?)",
                (row["id"], row["user_id"], row["order_date"], row["status"]),
            )

    # Create raw payments table
    cursor.execute("""
        CREATE TABLE raw_payments (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            payment_method TEXT,
            amount INTEGER,
            FOREIGN KEY (order_id) REFERENCES raw_orders(id)
        )
    """)

    # Load from CSV
    csv_path = Path(__file__).parent / "raw_payments.csv"
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute(
                "INSERT INTO raw_payments VALUES (?, ?, ?, ?)",
                (row["id"], row["order_id"], row["payment_method"], row["amount"]),
            )

    # Create staging tables (these would be dbt models)
    cursor.execute("""
        CREATE TABLE staging_customers AS
        SELECT
            id AS customer_id,
            first_name,
            last_name
        FROM raw_customers
    """)

    cursor.execute("""
        CREATE TABLE staging_orders AS
        SELECT
            id AS order_id,
            user_id AS customer_id,
            order_date,
            status
        FROM raw_orders
    """)

    cursor.execute("""
        CREATE TABLE staging_payments AS
        SELECT
            id AS payment_id,
            order_id,
            payment_method,
            amount / 100.0 AS amount
        FROM raw_payments
    """)

    # Create final analytics tables
    cursor.execute("""
        CREATE TABLE analytics_customers AS
        SELECT
            c.customer_id,
            c.first_name,
            c.last_name,
            MIN(o.order_date) AS first_order,
            MAX(o.order_date) AS most_recent_order,
            COUNT(o.order_id) AS number_of_orders
        FROM staging_customers c
        LEFT JOIN staging_orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.first_name, c.last_name
    """)

    cursor.execute("""
        CREATE TABLE analytics_orders AS
        SELECT
            o.order_id,
            o.customer_id,
            o.order_date,
            o.status,
            SUM(p.amount) AS amount
        FROM staging_orders o
        LEFT JOIN staging_payments p ON o.order_id = p.order_id
        GROUP BY o.order_id, o.customer_id, o.order_date, o.status
    """)

    conn.commit()

    # Print summary
    cursor.execute("SELECT COUNT(*) FROM raw_customers")
    customer_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM raw_orders")
    order_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM raw_payments")
    payment_count = cursor.fetchone()[0]

    conn.close()

    print(f"✓ Created jaffle shop database: {db_path}")
    print("  Data loaded from official dbt jaffle_shop CSVs:")
    print(f"    {customer_count} customers")
    print(f"    {order_count} orders")
    print(f"    {payment_count} payments")
    print("  Tables created:")
    print("    Raw: raw_customers, raw_orders, raw_payments")
    print("    Staging: staging_customers, staging_orders, staging_payments")
    print("    Analytics: analytics_customers, analytics_orders")


if __name__ == "__main__":
    create_jaffle_shop_db()
