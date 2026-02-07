"""Sync engine for DB-AGENTS CLI."""

from dataclasses import dataclass

from .database import DatabaseClient
from .filesystem import FileSystemManager
from .models import Resource


@dataclass
class ResourceDiff:
    """Represents a difference for a single resource."""

    resource: Resource
    status: str  # 'added', 'modified', 'deleted', 'unchanged'
    db_resource: Resource | None = None


@dataclass
class SchemaDiff:
    """Represents differences for all resources in a schema."""

    schema: str
    added: list[Resource]
    modified: list[tuple[Resource, Resource]]  # (local, db)
    deleted: list[Resource]
    unchanged: list[Resource]

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added or self.modified or self.deleted)

    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.added) + len(self.modified) + len(self.deleted)


class SyncEngine:
    """Manages sync operations between filesystem and database."""

    def __init__(self, workspace: FileSystemManager, db_client: DatabaseClient):
        """Initialize SyncEngine.

        Args:
            workspace: FileSystemManager instance
            db_client: DatabaseClient instance
        """
        self.workspace = workspace
        self.db = db_client

    def compute_diff(
        self,
        local_resources: list[Resource],
        db_resources: list[Resource],
    ) -> SchemaDiff:
        """Compute differences between local and database resources.

        Args:
            local_resources: Resources from local files
            db_resources: Resources from database

        Returns:
            SchemaDiff object with categorized changes
        """
        # Assume all resources are in same schema
        schema = local_resources[0].target_schema if local_resources else "_agents"

        # Create lookup dictionaries
        local_dict = {(r.resource_type, r.resource_name): r for r in local_resources}
        db_dict = {(r.resource_type, r.resource_name): r for r in db_resources}

        added = []
        modified = []
        deleted = []
        unchanged = []

        # Find added and modified resources
        for key, local_resource in local_dict.items():
            if key not in db_dict:
                added.append(local_resource)
            else:
                db_resource = db_dict[key]
                # Check if content changed
                if (
                    local_resource.description != db_resource.description
                    or local_resource.full_markdown != db_resource.full_markdown
                ):
                    modified.append((local_resource, db_resource))
                else:
                    unchanged.append(local_resource)

        # Find deleted resources (in DB but not local)
        for key, db_resource in db_dict.items():
            if key not in local_dict:
                deleted.append(db_resource)

        return SchemaDiff(
            schema=schema,
            added=added,
            modified=modified,
            deleted=deleted,
            unchanged=unchanged,
        )

    def diff_connection(
        self,
        connection_name: str,
        target_schema_filter: str | None = None,
    ) -> dict[str, SchemaDiff]:
        """Compare local files to database state for a connection.

        Args:
            connection_name: Name of the connection
            target_schema_filter: Optional filter for specific schema

        Returns:
            Dictionary mapping schema name to SchemaDiff

        Raises:
            Exception: If filesystem or database operations fail
        """
        # Discover local resources
        local_resources = self.workspace.discover_resources(
            connection_name,
            target_schema_filter=target_schema_filter,
        )

        # Group by target_schema
        by_schema = self.workspace.group_by_target_schema(local_resources)

        # For each schema, compute diff
        diffs = {}
        for schema, resources in by_schema.items():
            # Note: For now we're using the same db_client for all schemas
            # The db_client schema should be updated or we need multiple clients
            db_resources = self.db.pull_all_resources()
            diffs[schema] = self.compute_diff(resources, db_resources)

        return diffs

    def push_connection(
        self,
        connection_name: str,
        dry_run: bool = False,
        target_schema_filter: str | None = None,
    ) -> tuple[dict[str, SchemaDiff], dict[str, tuple[int, int, int]]]:
        """Push local files to database (deterministic sync).

        Args:
            connection_name: Name of the connection
            dry_run: If True, only compute diff without applying changes
            target_schema_filter: Optional filter for specific schema

        Returns:
            Tuple of (diffs, results) where:
            - diffs: Dictionary mapping schema to SchemaDiff
            - results: Dictionary mapping schema to (inserted, updated, deleted) counts

        Raises:
            Exception: If filesystem or database operations fail
        """
        # Get diff first
        diffs = self.diff_connection(connection_name, target_schema_filter)

        # If dry_run, return diffs only
        if dry_run:
            return diffs, {}

        # Apply changes per schema
        results = {}
        local_resources = self.workspace.discover_resources(
            connection_name,
            target_schema_filter=target_schema_filter,
        )
        by_schema = self.workspace.group_by_target_schema(local_resources)

        for schema, resources in by_schema.items():
            # Sync resources (deterministic)
            inserted, updated, deleted = self.db.sync_resources(resources)
            results[schema] = (inserted, updated, deleted)

        return diffs, results

    def validate_connection(self, connection_name: str) -> tuple[bool, list[str], list[str]]:
        """Validate resources in a connection.

        Args:
            connection_name: Name of the connection

        Returns:
            Tuple of (is_valid, error_messages, warning_messages)
        """
        errors = []
        warnings = []

        try:
            resources, validation_errors = self.workspace.validate_resources(connection_name)
            errors.extend(validation_errors)

            # Check for missing descriptions
            for resource in resources:
                if not resource.description:
                    warnings.append(
                        f"{resource.source_file}: Missing description for "
                        f"{resource.resource_type} '{resource.resource_name}'"
                    )

            is_valid = len(errors) == 0

            return is_valid, errors, warnings

        except Exception as e:
            errors.append(str(e))
            return False, errors, warnings
