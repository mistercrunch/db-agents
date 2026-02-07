---
resource_type: table
resource_name: users
target_schema: _agents
description: User accounts and authentication information
---

# users

The users table stores user account information and authentication details.

## Schema

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique user identifier |
| username | VARCHAR(50) | UNIQUE, NOT NULL | User's login name |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User's email address |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| is_active | BOOLEAN | DEFAULT true | Whether account is active |
| is_admin | BOOLEAN | DEFAULT false | Admin privileges flag |
| created_at | TIMESTAMP | DEFAULT NOW() | Account creation timestamp |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update timestamp |

## Indexes

- **PRIMARY KEY**: `id`
- **UNIQUE**: `username`
- **UNIQUE**: `email`
- **INDEX**: `created_at` (for analytics queries)

## Relationships

### Outgoing Foreign Keys

None (this is a root table)

### Incoming Foreign Keys

- `orders.user_id` → `users.id`
- `sessions.user_id` → `users.id`

## Usage Notes

### Authentication

Always check `is_active = true` before authenticating a user:

```sql
SELECT * FROM users
WHERE username = ?
  AND is_active = true;
```

### Email Normalization

Email addresses should be stored in lowercase for case-insensitive matching:

```sql
INSERT INTO users (username, email, password_hash)
VALUES (?, LOWER(?), ?);
```

### Security

- Never expose `password_hash` in API responses
- Use parameterized queries to prevent SQL injection
- Implement rate limiting on authentication attempts

## Common Queries

### Get user by username
```sql
SELECT id, username, email, is_active, is_admin, created_at
FROM users
WHERE username = ? AND is_active = true;
```

### Get recently registered users
```sql
SELECT id, username, email, created_at
FROM users
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

### Count active users
```sql
SELECT COUNT(*) as active_users
FROM users
WHERE is_active = true;
```

## Migration History

- **2024-01-15**: Initial table creation
- **2024-02-01**: Added `is_admin` column
- **2024-03-10**: Added index on `created_at`

## Data Quality Checks

Run these queries regularly to ensure data quality:

```sql
-- Check for duplicate emails
SELECT email, COUNT(*) as count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Check for invalid email formats
SELECT id, email
FROM users
WHERE email NOT LIKE '%@%.%';

-- Check for old inactive accounts
SELECT COUNT(*) as inactive_count
FROM users
WHERE is_active = false
  AND updated_at < NOW() - INTERVAL '1 year';
```
