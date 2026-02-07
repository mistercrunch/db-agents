"""File system operations for DB-AGENTS CLI."""

from collections import defaultdict
from pathlib import Path

import frontmatter
from pydantic import ValidationError

from .models import ConnectionConfig, Resource, WorkspaceConfig


class FileSystemError(Exception):
    """Base exception for filesystem operations."""

    pass


class FileSystemManager:
    """Manages file system operations for DB-AGENTS workspace."""

    def __init__(self, workspace_root: Path):
        """Initialize FileSystemManager.

        Args:
            workspace_root: Root directory of the DB-AGENTS workspace
        """
        self.root = workspace_root

    def load_workspace_config(self) -> WorkspaceConfig:
        """Load root AGENTS.md configuration.

        Returns:
            WorkspaceConfig parsed from root AGENTS.md

        Raises:
            FileSystemError: If AGENTS.md doesn't exist or is invalid
        """
        agents_file = self.root / "AGENTS.md"
        if not agents_file.exists():
            raise FileSystemError(f"No AGENTS.md found in {self.root}")

        try:
            post = frontmatter.load(agents_file)
            return WorkspaceConfig(**post.metadata)
        except ValidationError as e:
            raise FileSystemError(f"Invalid AGENTS.md frontmatter: {e}")
        except Exception as e:
            raise FileSystemError(f"Failed to load AGENTS.md: {e}")

    def load_connection_config(self, connection_name: str) -> ConnectionConfig:
        """Load connection AGENTS.md configuration.

        Args:
            connection_name: Name of the connection folder

        Returns:
            ConnectionConfig parsed from connection AGENTS.md

        Raises:
            FileSystemError: If connection AGENTS.md doesn't exist or is invalid
        """
        agents_file = self.root / connection_name / "AGENTS.md"
        if not agents_file.exists():
            raise FileSystemError(f"No AGENTS.md found in connection folder: {connection_name}/")

        try:
            post = frontmatter.load(agents_file)
            return ConnectionConfig(**post.metadata)
        except ValidationError as e:
            raise FileSystemError(f"Invalid AGENTS.md frontmatter in {connection_name}/: {e}")
        except Exception as e:
            raise FileSystemError(f"Failed to load AGENTS.md from {connection_name}/: {e}")

    def discover_resources(
        self,
        connection_name: str,
        target_schema_filter: str | None = None,
    ) -> list[Resource]:
        """Discover all .md resource files in connection folder.

        File location doesn't matter - metadata is source of truth.
        Scans all .md files recursively except AGENTS.md files.

        Args:
            connection_name: Name of the connection folder
            target_schema_filter: Optional filter to only include resources
                                 with specific target_schema

        Returns:
            List of Resource objects parsed from markdown files

        Raises:
            FileSystemError: If connection folder doesn't exist or files are invalid
        """
        connection_dir = self.root / connection_name
        if not connection_dir.exists():
            raise FileSystemError(f"Connection folder not found: {connection_name}/")

        resources = []
        errors = []

        for md_file in connection_dir.rglob("*.md"):
            # Skip AGENTS.md files
            if md_file.name == "AGENTS.md":
                continue

            # Skip dotfiles
            if md_file.name.startswith("."):
                continue

            try:
                # Parse frontmatter
                post = frontmatter.load(md_file)

                # Create resource (Pydantic validation)
                resource = Resource(
                    resource_type=post.metadata.get("resource_type"),
                    resource_name=post.metadata.get("resource_name"),
                    target_schema=post.metadata.get("target_schema", "_agents"),
                    description=post.metadata.get("description"),
                    full_markdown=post.content,
                    source_file=md_file.relative_to(self.root),
                )

                # Filter by target_schema if specified
                if target_schema_filter and resource.target_schema != target_schema_filter:
                    continue

                resources.append(resource)

            except ValidationError as e:
                errors.append(f"{md_file.relative_to(self.root)}: Invalid frontmatter - {e}")
            except Exception as e:
                errors.append(f"{md_file.relative_to(self.root)}: Failed to parse - {e}")

        # If there were errors, raise exception with all errors
        if errors:
            raise FileSystemError(f"Failed to parse {len(errors)} file(s):\n" + "\n".join(errors))

        return resources

    def group_by_target_schema(self, resources: list[Resource]) -> dict[str, list[Resource]]:
        """Group resources by their target_schema for batch operations.

        Args:
            resources: List of Resource objects to group

        Returns:
            Dictionary mapping target_schema to list of resources
        """
        grouped = defaultdict(list)
        for resource in resources:
            grouped[resource.target_schema].append(resource)
        return dict(grouped)

    def list_connections(self) -> list[str]:
        """List all connection folders in the workspace.

        Returns:
            List of connection folder names (directories with AGENTS.md)
        """
        if not self.root.exists():
            return []

        connections = []
        for item in self.root.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # Check if it has an AGENTS.md file
                if (item / "AGENTS.md").exists():
                    connections.append(item.name)

        return sorted(connections)

    def validate_resources(self, connection_name: str) -> tuple[list[Resource], list[str]]:
        """Validate all resources in a connection.

        Args:
            connection_name: Name of the connection folder

        Returns:
            Tuple of (valid_resources, error_messages)
        """
        try:
            resources = self.discover_resources(connection_name)

            # Check for duplicate resource names within same target_schema
            by_schema = self.group_by_target_schema(resources)
            errors = []

            for schema, schema_resources in by_schema.items():
                resource_names = [r.resource_name for r in schema_resources]
                duplicates = [name for name in resource_names if resource_names.count(name) > 1]
                if duplicates:
                    unique_duplicates = list(set(duplicates))
                    errors.append(
                        f"Duplicate resource_name in schema '{schema}': "
                        f"{', '.join(unique_duplicates)}"
                    )

            return resources, errors

        except FileSystemError as e:
            return [], [str(e)]

    def create_workspace(self, workspace_config: WorkspaceConfig) -> None:
        """Create a new workspace with root AGENTS.md.

        Args:
            workspace_config: WorkspaceConfig to write to AGENTS.md

        Raises:
            FileSystemError: If workspace already exists or creation fails
        """
        if self.root.exists() and (self.root / "AGENTS.md").exists():
            raise FileSystemError(f"Workspace already exists at {self.root}")

        self.root.mkdir(parents=True, exist_ok=True)

        # Create root AGENTS.md with frontmatter
        agents_file = self.root / "AGENTS.md"
        post = frontmatter.Post(
            "# DB-AGENTS Workspace\n\nThis workspace manages database documentation.\n",
            **workspace_config.model_dump(),
        )

        with open(agents_file, "w") as f:
            f.write(frontmatter.dumps(post))

    def create_connection(
        self,
        connection_name: str,
        connection_config: ConnectionConfig,
        create_example: bool = True,
    ) -> None:
        """Create a new connection folder with AGENTS.md.

        Args:
            connection_name: Name for the connection folder
            connection_config: ConnectionConfig to write to AGENTS.md
            create_example: Whether to create an example resource file

        Raises:
            FileSystemError: If connection already exists or creation fails
        """
        connection_dir = self.root / connection_name
        if connection_dir.exists():
            raise FileSystemError(f"Connection folder already exists: {connection_name}/")

        connection_dir.mkdir(parents=True, exist_ok=True)

        # Create connection AGENTS.md with frontmatter
        agents_file = connection_dir / "AGENTS.md"
        display_name = connection_config.display_name or connection_name
        post = frontmatter.Post(
            f"# {display_name}\n\nDatabase connection for {display_name}.\n",
            **connection_config.model_dump(),
        )

        with open(agents_file, "w") as f:
            f.write(frontmatter.dumps(post))

        # Optionally create example resource file
        if create_example:
            example_file = connection_dir / "global.md"
            example_post = frontmatter.Post(
                f"# {display_name} Documentation\n\n"
                f"## Overview\n\n"
                f"Global documentation for {display_name}.\n\n"
                f"## Conventions\n\n"
                f"- Add your conventions here\n",
                resource_type="global",
                resource_name="global",
                target_schema="_agents",
                description="Global documentation",
            )

            with open(example_file, "w") as f:
                f.write(frontmatter.dumps(example_post))
