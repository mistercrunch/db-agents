---
sqlalchemy_uri: "sqlite:///example.db"
default_target_schema: _agents
display_name: "Example Database"
---

# Example Database

This is an example database connection using SQLite for easy local testing.

## For PostgreSQL

To use PostgreSQL instead, change the URI to:

```yaml
sqlalchemy_uri: "postgresql://user:{{ env.DB_PASSWORD }}@localhost:5432/mydb"
```

And create a `.env` file with:

```
DB_PASSWORD=your_password
```

## For Other Databases

- MySQL: `mysql://user:{{ env.DB_PASSWORD }}@host:3306/database`
- Snowflake: `snowflake://user:{{ env.DB_PASSWORD }}@account/database/schema`
