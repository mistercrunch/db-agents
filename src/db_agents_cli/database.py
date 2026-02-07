"""Database operations for DB-AGENTS CLI."""

from sqlalchemy import Column, MetaData, String, Table, Text, delete, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .models import Resource


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class DatabaseClient:
    """Manages database operations for DB-AGENTS."""

    def __init__(self, engine: Engine, agents_schema: str = "_agents"):
        """Initialize DatabaseClient.

        Args:
            engine: SQLAlchemy Engine instance
            agents_schema: Schema name for _agents table (default: _agents)
        """
        self.engine = engine
        self.schema = agents_schema
        self.metadata = MetaData()
        self._table: Table | None = None
        # Check if database supports schemas (SQLite doesn't)
        self.supports_schemas = engine.dialect.name not in ("sqlite",)

    def _get_table(self) -> Table:
        """Get or create Table object for _agents._agents.

        Returns:
            SQLAlchemy Table object
        """
        if self._table is None:
            # Use schema only if database supports it
            table_schema = self.schema if self.supports_schemas else None
            self._table = Table(
                "_agents",
                self.metadata,
                Column("resource_type", String(255), nullable=False, primary_key=True),
                Column("resource_name", String(255), nullable=False, primary_key=True),
                Column("description", Text),
                Column("full_markdown", Text),
                schema=table_schema,
            )
        return self._table

    def ensure_schema_exists(self) -> None:
        """Create schema if it doesn't exist.

        Raises:
            DatabaseError: If schema creation fails
        """
        # Skip schema creation for databases that don't support it
        if not self.supports_schemas:
            return

        try:
            inspector = inspect(self.engine)
            schemas = inspector.get_schema_names()

            if self.schema not in schemas:
                with self.engine.connect() as conn:
                    # Try to create schema (dialect-specific)
                    dialect_name = self.engine.dialect.name

                    if dialect_name in ("postgresql", "mysql"):
                        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema}"))
                    else:
                        # For other dialects, try generic approach
                        conn.execute(text(f"CREATE SCHEMA {self.schema}"))

                    conn.commit()

        except SQLAlchemyError as e:
            # Some databases don't support schemas
            if "schema" not in str(e).lower():
                raise DatabaseError(f"Failed to create schema: {e}")

    def ensure_table_exists(self) -> None:
        """Create _agents._agents table if it doesn't exist.

        Raises:
            DatabaseError: If table creation fails
        """
        try:
            # First ensure schema exists
            self.ensure_schema_exists()

            # Create table if not exists
            table = self._get_table()
            table.create(self.engine, checkfirst=True)

        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to create table: {e}")

    def table_exists(self) -> bool:
        """Check if _agents._agents table exists.

        Returns:
            True if table exists, False otherwise
        """
        try:
            inspector = inspect(self.engine)
            schema = self.schema if self.supports_schemas else None
            return inspector.has_table("_agents", schema=schema)
        except Exception:
            return False

    def pull_all_resources(self, schema_filter: str | None = None) -> list[Resource]:
        """Query all rows from _agents._agents.

        Args:
            schema_filter: Optional filter (currently unused as resources
                          are filtered by connection/schema already)

        Returns:
            List of Resource objects from database

        Raises:
            DatabaseError: If query fails
        """
        try:
            table = self._get_table()

            with self.engine.connect() as conn:
                stmt = select(table)
                result = conn.execute(stmt)
                rows = result.fetchall()

                resources = []
                for row in rows:
                    resource = Resource(
                        resource_type=row.resource_type,
                        resource_name=row.resource_name,
                        target_schema=self.schema,
                        description=row.description,
                        full_markdown=row.full_markdown or "",
                    )
                    resources.append(resource)

                return resources

        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to pull resources: {e}")

    def sync_resources(self, resources: list[Resource]) -> tuple[int, int, int]:
        """Deterministically sync resources to database.

        This is a deterministic operation: the database state will match
        the provided resources exactly. Resources in DB but not in the
        provided list will be DELETED.

        Args:
            resources: List of Resource objects to sync

        Returns:
            Tuple of (inserted, updated, deleted) counts

        Raises:
            DatabaseError: If sync fails
        """
        try:
            table = self._get_table()

            with self.engine.begin() as conn:
                # Get current resources from database
                stmt = select(table)
                result = conn.execute(stmt)
                db_resources = {
                    (row.resource_type, row.resource_name): row for row in result.fetchall()
                }

                # Track resources from local files
                local_resources = {(r.resource_type, r.resource_name): r for r in resources}

                inserted = 0
                updated = 0
                deleted = 0

                # Insert or update resources from local files
                for key, resource in local_resources.items():
                    resource_dict = {
                        "resource_type": resource.resource_type,
                        "resource_name": resource.resource_name,
                        "description": resource.description,
                        "full_markdown": resource.full_markdown,
                    }

                    if key in db_resources:
                        # Update existing resource
                        db_row = db_resources[key]
                        # Check if content changed
                        if (
                            db_row.description != resource.description
                            or db_row.full_markdown != resource.full_markdown
                        ):
                            stmt = (
                                table.update()
                                .where(table.c.resource_type == resource.resource_type)
                                .where(table.c.resource_name == resource.resource_name)
                                .values(resource_dict)
                            )
                            conn.execute(stmt)
                            updated += 1
                    else:
                        # Insert new resource
                        stmt = table.insert().values(resource_dict)
                        conn.execute(stmt)
                        inserted += 1

                # Delete resources in DB but not in local files
                for key in db_resources.keys():
                    if key not in local_resources:
                        resource_type, resource_name = key
                        stmt = delete(table).where(
                            table.c.resource_type == resource_type,
                            table.c.resource_name == resource_name,
                        )
                        conn.execute(stmt)
                        deleted += 1

                return inserted, updated, deleted

        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to sync resources: {e}")

    def get_resource(self, resource_type: str, resource_name: str) -> Resource | None:
        """Get a single resource from database.

        Args:
            resource_type: Type of resource
            resource_name: Name of resource

        Returns:
            Resource object if found, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        try:
            table = self._get_table()

            with self.engine.connect() as conn:
                stmt = select(table).where(
                    table.c.resource_type == resource_type,
                    table.c.resource_name == resource_name,
                )
                result = conn.execute(stmt)
                row = result.fetchone()

                if row:
                    return Resource(
                        resource_type=row.resource_type,
                        resource_name=row.resource_name,
                        target_schema=self.schema,
                        description=row.description,
                        full_markdown=row.full_markdown or "",
                    )

                return None

        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to get resource: {e}")
