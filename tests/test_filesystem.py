"""Tests for FileSystemManager."""

import tempfile
from pathlib import Path

import frontmatter
import pytest

from db_agents_cli.filesystem import FileSystemError, FileSystemManager
from db_agents_cli.models import ConnectionConfig, WorkspaceConfig


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_root = Path(tmpdir) / "DB-AGENTS"
        workspace_root.mkdir()
        yield workspace_root


@pytest.fixture
def workspace_with_config(temp_workspace):
    """Create a workspace with root AGENTS.md."""
    agents_file = temp_workspace / "AGENTS.md"
    post = frontmatter.Post(
        "# Test Workspace",
        version=1,
        default_connection="test-conn",
        settings={},
    )
    with open(agents_file, "w") as f:
        f.write(frontmatter.dumps(post))

    return temp_workspace


@pytest.fixture
def workspace_with_connection(workspace_with_config):
    """Create a workspace with a connection."""
    conn_dir = workspace_with_config / "test-conn"
    conn_dir.mkdir()

    agents_file = conn_dir / "AGENTS.md"
    post = frontmatter.Post(
        "# Test Connection",
        sqlalchemy_uri="sqlite:///test.db",
        default_target_schema="_agents",
        display_name="Test DB",
    )
    with open(agents_file, "w") as f:
        f.write(frontmatter.dumps(post))

    return workspace_with_config


class TestFileSystemManager:
    """Tests for FileSystemManager."""

    def test_load_workspace_config(self, workspace_with_config):
        """Test loading workspace configuration."""
        fs = FileSystemManager(workspace_with_config)
        config = fs.load_workspace_config()

        assert config.version == 1
        assert config.default_connection == "test-conn"
        assert config.settings == {}

    def test_load_workspace_config_missing(self, temp_workspace):
        """Test loading workspace config when AGENTS.md doesn't exist."""
        fs = FileSystemManager(temp_workspace)

        with pytest.raises(FileSystemError, match="No AGENTS.md found"):
            fs.load_workspace_config()

    def test_load_connection_config(self, workspace_with_connection):
        """Test loading connection configuration."""
        fs = FileSystemManager(workspace_with_connection)
        config = fs.load_connection_config("test-conn")

        assert config.sqlalchemy_uri == "sqlite:///test.db"
        assert config.default_target_schema == "_agents"
        assert config.display_name == "Test DB"

    def test_load_connection_config_missing(self, workspace_with_config):
        """Test loading connection config when folder doesn't exist."""
        fs = FileSystemManager(workspace_with_config)

        with pytest.raises(FileSystemError, match="No AGENTS.md found in connection folder"):
            fs.load_connection_config("nonexistent")

    def test_discover_resources(self, workspace_with_connection):
        """Test discovering resources in a connection."""
        fs = FileSystemManager(workspace_with_connection)
        conn_dir = workspace_with_connection / "test-conn"

        # Create resource files
        resource1 = conn_dir / "global.md"
        post1 = frontmatter.Post(
            "# Global docs",
            resource_type="global",
            resource_name="global",
            target_schema="_agents",
            description="Global documentation",
        )
        with open(resource1, "w") as f:
            f.write(frontmatter.dumps(post1))

        resource2 = conn_dir / "users.md"
        post2 = frontmatter.Post(
            "# Users table",
            resource_type="table",
            resource_name="users",
            description="User accounts",
        )
        with open(resource2, "w") as f:
            f.write(frontmatter.dumps(post2))

        resources = fs.discover_resources("test-conn")

        assert len(resources) == 2
        resource_names = [r.resource_name for r in resources]
        assert "global" in resource_names
        assert "users" in resource_names

    def test_discover_resources_nested(self, workspace_with_connection):
        """Test discovering resources in nested directories."""
        fs = FileSystemManager(workspace_with_connection)
        conn_dir = workspace_with_connection / "test-conn"

        # Create nested structure
        nested_dir = conn_dir / "tables"
        nested_dir.mkdir()

        resource = nested_dir / "orders.md"
        post = frontmatter.Post(
            "# Orders",
            resource_type="table",
            resource_name="orders",
        )
        with open(resource, "w") as f:
            f.write(frontmatter.dumps(post))

        resources = fs.discover_resources("test-conn")

        assert len(resources) == 1
        assert resources[0].resource_name == "orders"

    def test_discover_resources_skip_agents_md(self, workspace_with_connection):
        """Test that AGENTS.md files are skipped."""
        fs = FileSystemManager(workspace_with_connection)
        resources = fs.discover_resources("test-conn")

        # Should not include the AGENTS.md in connection folder
        assert len(resources) == 0

    def test_discover_resources_with_filter(self, workspace_with_connection):
        """Test discovering resources with schema filter."""
        fs = FileSystemManager(workspace_with_connection)
        conn_dir = workspace_with_connection / "test-conn"

        # Create resources with different schemas
        resource1 = conn_dir / "global.md"
        post1 = frontmatter.Post(
            "# Global",
            resource_type="global",
            resource_name="global",
            target_schema="_agents",
        )
        with open(resource1, "w") as f:
            f.write(frontmatter.dumps(post1))

        resource2 = conn_dir / "special.md"
        post2 = frontmatter.Post(
            "# Special",
            resource_type="table",
            resource_name="special",
            target_schema="custom_schema",
        )
        with open(resource2, "w") as f:
            f.write(frontmatter.dumps(post2))

        # Filter for _agents only
        resources = fs.discover_resources("test-conn", target_schema_filter="_agents")

        assert len(resources) == 1
        assert resources[0].resource_name == "global"

    def test_group_by_target_schema(self, workspace_with_connection):
        """Test grouping resources by schema."""
        fs = FileSystemManager(workspace_with_connection)
        conn_dir = workspace_with_connection / "test-conn"

        # Create resources with different schemas
        for i, schema in enumerate(["_agents", "_agents", "custom"]):
            resource = conn_dir / f"resource{i}.md"
            post = frontmatter.Post(
                f"# Resource {i}",
                resource_type="table",
                resource_name=f"resource{i}",
                target_schema=schema,
            )
            with open(resource, "w") as f:
                f.write(frontmatter.dumps(post))

        resources = fs.discover_resources("test-conn")
        grouped = fs.group_by_target_schema(resources)

        assert len(grouped) == 2
        assert len(grouped["_agents"]) == 2
        assert len(grouped["custom"]) == 1

    def test_list_connections(self, workspace_with_connection):
        """Test listing all connections."""
        fs = FileSystemManager(workspace_with_connection)

        # Add another connection
        conn2_dir = workspace_with_connection / "conn2"
        conn2_dir.mkdir()
        agents_file = conn2_dir / "AGENTS.md"
        post = frontmatter.Post("# Conn2", sqlalchemy_uri="sqlite:///conn2.db")
        with open(agents_file, "w") as f:
            f.write(frontmatter.dumps(post))

        connections = fs.list_connections()

        assert len(connections) == 2
        assert "test-conn" in connections
        assert "conn2" in connections

    def test_validate_resources(self, workspace_with_connection):
        """Test resource validation."""
        fs = FileSystemManager(workspace_with_connection)
        conn_dir = workspace_with_connection / "test-conn"

        # Create valid resource
        resource = conn_dir / "valid.md"
        post = frontmatter.Post(
            "# Valid",
            resource_type="table",
            resource_name="valid",
        )
        with open(resource, "w") as f:
            f.write(frontmatter.dumps(post))

        resources, errors = fs.validate_resources("test-conn")

        assert len(resources) == 1
        assert len(errors) == 0

    def test_validate_resources_with_duplicates(self, workspace_with_connection):
        """Test validation catches duplicate resource names."""
        fs = FileSystemManager(workspace_with_connection)
        conn_dir = workspace_with_connection / "test-conn"

        # Create two resources with same name
        for i in range(2):
            resource = conn_dir / f"duplicate{i}.md"
            post = frontmatter.Post(
                "# Duplicate",
                resource_type="table",
                resource_name="duplicate_name",
                target_schema="_agents",
            )
            with open(resource, "w") as f:
                f.write(frontmatter.dumps(post))

        resources, errors = fs.validate_resources("test-conn")

        assert len(errors) > 0
        assert "Duplicate resource_name" in errors[0]

    def test_create_workspace(self, temp_workspace):
        """Test creating a new workspace."""
        # Remove the directory first
        import shutil

        shutil.rmtree(temp_workspace)

        fs = FileSystemManager(temp_workspace)
        config = WorkspaceConfig(version=1, default_connection="test")
        fs.create_workspace(config)

        assert temp_workspace.exists()
        assert (temp_workspace / "AGENTS.md").exists()

        # Verify content
        loaded_config = fs.load_workspace_config()
        assert loaded_config.version == 1
        assert loaded_config.default_connection == "test"

    def test_create_connection(self, workspace_with_config):
        """Test creating a new connection."""
        fs = FileSystemManager(workspace_with_config)
        config = ConnectionConfig(sqlalchemy_uri="sqlite:///new.db", display_name="New Connection")

        fs.create_connection("new-conn", config, create_example=True)

        conn_dir = workspace_with_config / "new-conn"
        assert conn_dir.exists()
        assert (conn_dir / "AGENTS.md").exists()
        assert (conn_dir / "global.md").exists()  # Example file

        # Verify content
        loaded_config = fs.load_connection_config("new-conn")
        assert loaded_config.sqlalchemy_uri == "sqlite:///new.db"
        assert loaded_config.display_name == "New Connection"

    def test_create_connection_without_example(self, workspace_with_config):
        """Test creating connection without example file."""
        fs = FileSystemManager(workspace_with_config)
        config = ConnectionConfig(sqlalchemy_uri="sqlite:///test.db")

        fs.create_connection("no-example", config, create_example=False)

        conn_dir = workspace_with_config / "no-example"
        assert conn_dir.exists()
        assert (conn_dir / "AGENTS.md").exists()
        assert not (conn_dir / "global.md").exists()  # No example
