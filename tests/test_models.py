"""Tests for Pydantic models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from db_agents_cli.models import ConnectionConfig, Resource, WorkspaceConfig


class TestResource:
    """Tests for Resource model."""

    def test_valid_resource(self):
        """Test creating a valid resource."""
        resource = Resource(
            resource_type="table",
            resource_name="users",
            target_schema="_agents",
            description="User accounts",
            full_markdown="# Users\n\nUser accounts table",
        )

        assert resource.resource_type == "table"
        assert resource.resource_name == "users"
        assert resource.target_schema == "_agents"
        assert resource.description == "User accounts"
        assert resource.full_markdown == "# Users\n\nUser accounts table"

    def test_resource_defaults(self):
        """Test resource with default values."""
        resource = Resource(
            resource_type="global",
            resource_name="global",
            full_markdown="# Global docs",
        )

        assert resource.target_schema == "_agents"  # Default value
        assert resource.description is None  # Optional field

    def test_resource_with_source_file(self):
        """Test resource with source file path."""
        resource = Resource(
            resource_type="table",
            resource_name="orders",
            full_markdown="# Orders",
            source_file=Path("DB-AGENTS/prod/orders.md"),
        )

        assert resource.source_file == Path("DB-AGENTS/prod/orders.md")

    def test_resource_name_validation(self):
        """Test that resource_name cannot be empty."""
        with pytest.raises(ValidationError, match="resource_name cannot be empty"):
            Resource(
                resource_type="table",
                resource_name="",
                full_markdown="# Test",
            )

        with pytest.raises(ValidationError, match="resource_name cannot be empty"):
            Resource(
                resource_type="table",
                resource_name="   ",  # Whitespace only
                full_markdown="# Test",
            )

    def test_resource_type_validation(self):
        """Test that resource_type cannot be empty."""
        with pytest.raises(ValidationError, match="resource_type cannot be empty"):
            Resource(
                resource_type="",
                resource_name="users",
                full_markdown="# Test",
            )

    def test_resource_name_whitespace_trimmed(self):
        """Test that resource_name whitespace is trimmed."""
        resource = Resource(
            resource_type="table",
            resource_name="  users  ",
            full_markdown="# Test",
        )

        assert resource.resource_name == "users"

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            Resource(
                resource_type="table",
                # Missing resource_name
                full_markdown="# Test",
            )

        with pytest.raises(ValidationError):
            Resource(
                resource_name="users",
                # Missing resource_type
                full_markdown="# Test",
            )

        with pytest.raises(ValidationError):
            Resource(
                resource_type="table",
                resource_name="users",
                # Missing full_markdown
            )


class TestConnectionConfig:
    """Tests for ConnectionConfig model."""

    def test_valid_connection_config(self):
        """Test creating a valid connection config."""
        config = ConnectionConfig(
            sqlalchemy_uri="postgresql://user:pass@host/db",
            default_target_schema="_agents",
            display_name="Production DB",
        )

        assert config.sqlalchemy_uri == "postgresql://user:pass@host/db"
        assert config.default_target_schema == "_agents"
        assert config.display_name == "Production DB"

    def test_connection_config_defaults(self):
        """Test connection config with default values."""
        config = ConnectionConfig(sqlalchemy_uri="sqlite:///test.db")

        assert config.default_target_schema == "_agents"  # Default
        assert config.display_name is None  # Optional

    def test_get_rendered_uri_no_template(self):
        """Test rendering URI without templates."""
        config = ConnectionConfig(sqlalchemy_uri="sqlite:///test.db")

        rendered = config.get_rendered_uri({})
        assert rendered == "sqlite:///test.db"

    def test_get_rendered_uri_with_env_var(self):
        """Test rendering URI with environment variable."""
        config = ConnectionConfig(sqlalchemy_uri="postgresql://user:{{ env.DB_PASSWORD }}@host/db")

        rendered = config.get_rendered_uri({"DB_PASSWORD": "secret123"})
        assert rendered == "postgresql://user:secret123@host/db"

    def test_get_rendered_uri_entire_uri(self):
        """Test rendering when entire URI is an env var."""
        config = ConnectionConfig(sqlalchemy_uri="{{ env.DATABASE_URL }}")

        rendered = config.get_rendered_uri({"DATABASE_URL": "sqlite:///test.db"})
        assert rendered == "sqlite:///test.db"

    def test_get_rendered_uri_missing_var(self):
        """Test rendering with missing environment variable."""
        config = ConnectionConfig(sqlalchemy_uri="postgresql://user:{{ env.DB_PASSWORD }}@host/db")

        with pytest.raises(ValueError, match="Missing environment variable"):
            config.get_rendered_uri({})

    def test_get_rendered_uri_invalid_syntax(self):
        """Test rendering with invalid template syntax."""
        config = ConnectionConfig(sqlalchemy_uri="postgresql://user:{{ env.PASS @host/db")

        with pytest.raises(ValueError, match="Invalid template syntax"):
            config.get_rendered_uri({"PASS": "secret"})


class TestWorkspaceConfig:
    """Tests for WorkspaceConfig model."""

    def test_valid_workspace_config(self):
        """Test creating a valid workspace config."""
        config = WorkspaceConfig(
            version=1,
            default_connection="prod",
            settings={"validate_on_push": True},
        )

        assert config.version == 1
        assert config.default_connection == "prod"
        assert config.settings == {"validate_on_push": True}

    def test_workspace_config_defaults(self):
        """Test workspace config with defaults."""
        config = WorkspaceConfig()

        assert config.version == 1  # Default
        assert config.default_connection is None  # Default
        assert config.settings == {}  # Default

    def test_workspace_config_minimal(self):
        """Test workspace config with minimal data."""
        config = WorkspaceConfig(version=1)

        assert config.version == 1
        assert config.default_connection is None
        assert config.settings == {}
