"""Integration tests for complete DB-AGENTS workflow."""

import sqlite3
import tempfile
from pathlib import Path

import frontmatter
import pytest

from db_agents_cli.config import ConnectionManager
from db_agents_cli.database import DatabaseClient
from db_agents_cli.filesystem import FileSystemManager
from db_agents_cli.sync import SyncEngine


@pytest.fixture
def integration_workspace():
    """Create a complete test workspace with database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_root = Path(tmpdir) / "DB-AGENTS"
        workspace_root.mkdir()

        # Create workspace config
        agents_file = workspace_root / "AGENTS.md"
        post = frontmatter.Post(
            "# Test Workspace",
            version=1,
            default_connection="test-db",
            settings={},
        )
        with open(agents_file, "w") as f:
            f.write(frontmatter.dumps(post))

        # Create connection
        conn_dir = workspace_root / "test-db"
        conn_dir.mkdir()

        db_path = Path(tmpdir) / "test.db"
        conn_agents = conn_dir / "AGENTS.md"
        conn_post = frontmatter.Post(
            "# Test Database",
            sqlalchemy_uri=f"sqlite:///{db_path}",
            default_target_schema="_agents",
            display_name="Test DB",
        )
        with open(conn_agents, "w") as f:
            f.write(frontmatter.dumps(conn_post))

        yield {
            "workspace_root": workspace_root,
            "conn_dir": conn_dir,
            "db_path": db_path,
        }


class TestCompleteWorkflow:
    """Test complete end-to-end workflow."""

    def test_full_sync_workflow(self, integration_workspace):
        """Test complete workflow: create, validate, diff, push, modify, push."""
        workspace_root = integration_workspace["workspace_root"]
        conn_dir = integration_workspace["conn_dir"]
        db_path = integration_workspace["db_path"]

        fs = FileSystemManager(workspace_root)

        # Step 1: Create resource files
        global_file = conn_dir / "global.md"
        global_post = frontmatter.Post(
            "# Global Documentation\n\nDatabase conventions and best practices.",
            resource_type="global",
            resource_name="global",
            target_schema="_agents",
            description="Global documentation",
        )
        with open(global_file, "w") as f:
            f.write(frontmatter.dumps(global_post))

        users_file = conn_dir / "users.md"
        users_post = frontmatter.Post(
            "# users\n\nUser accounts table.",
            resource_type="table",
            resource_name="users",
            target_schema="_agents",
            description="User accounts",
        )
        with open(users_file, "w") as f:
            f.write(frontmatter.dumps(users_post))

        # Step 2: Validate
        resources, errors = fs.validate_resources("test-db")
        assert len(resources) == 2
        assert len(errors) == 0

        # Step 3: Set up database connection
        conn_config = fs.load_connection_config("test-db")
        conn_manager = ConnectionManager(conn_config)
        engine = conn_manager.get_engine()
        db_client = DatabaseClient(engine)

        # Step 4: Ensure table exists
        db_client.ensure_table_exists()
        assert db_client.table_exists()

        # Step 5: Create sync engine and get diff
        sync_engine = SyncEngine(fs, db_client)
        diffs = sync_engine.diff_connection("test-db")

        assert "_agents" in diffs
        diff = diffs["_agents"]
        assert len(diff.added) == 2
        assert len(diff.modified) == 0
        assert len(diff.deleted) == 0

        # Step 6: Push to database
        diffs, results = sync_engine.push_connection("test-db", dry_run=False)
        assert results["_agents"] == (2, 0, 0)  # 2 inserted, 0 updated, 0 deleted

        # Step 7: Verify database content
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT resource_type, resource_name FROM _agents ORDER BY resource_name")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0] == ("global", "global")
        assert rows[1] == ("table", "users")

        # Step 8: Modify a resource
        modified_users_post = frontmatter.Post(
            "# users\n\nUser accounts table with authentication information.",
            resource_type="table",
            resource_name="users",
            target_schema="_agents",
            description="User accounts with auth",
        )
        with open(users_file, "w") as f:
            f.write(frontmatter.dumps(modified_users_post))

        # Step 9: Check diff shows modification
        diffs = sync_engine.diff_connection("test-db")
        diff = diffs["_agents"]
        assert len(diff.added) == 0
        assert len(diff.modified) == 1
        assert len(diff.deleted) == 0

        # Step 10: Push modification
        diffs, results = sync_engine.push_connection("test-db", dry_run=False)
        assert results["_agents"] == (0, 1, 0)  # 0 inserted, 1 updated, 0 deleted

        # Step 11: Delete a resource file
        users_file.unlink()

        # Step 12: Check diff shows deletion
        diffs = sync_engine.diff_connection("test-db")
        diff = diffs["_agents"]
        assert len(diff.added) == 0
        assert len(diff.modified) == 0
        assert len(diff.deleted) == 1

        # Step 13: Push deletion
        diffs, results = sync_engine.push_connection("test-db", dry_run=False)
        assert results["_agents"] == (0, 0, 1)  # 0 inserted, 0 updated, 1 deleted

        # Step 14: Verify only 1 resource remains
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM _agents")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_multi_schema_workflow(self, integration_workspace):
        """Test workflow with multiple target schemas."""
        workspace_root = integration_workspace["workspace_root"]
        conn_dir = integration_workspace["conn_dir"]

        fs = FileSystemManager(workspace_root)

        # Create resources for different schemas
        agents_file = conn_dir / "agents_resource.md"
        agents_post = frontmatter.Post(
            "# Agents Schema Resource",
            resource_type="table",
            resource_name="agents_table",
            target_schema="_agents",
            description="In _agents schema",
        )
        with open(agents_file, "w") as f:
            f.write(frontmatter.dumps(agents_post))

        custom_file = conn_dir / "custom_resource.md"
        custom_post = frontmatter.Post(
            "# Custom Schema Resource",
            resource_type="table",
            resource_name="custom_table",
            target_schema="custom_schema",
            description="In custom schema",
        )
        with open(custom_file, "w") as f:
            f.write(frontmatter.dumps(custom_post))

        # Set up database
        conn_config = fs.load_connection_config("test-db")
        conn_manager = ConnectionManager(conn_config)
        engine = conn_manager.get_engine()
        db_client = DatabaseClient(engine)
        db_client.ensure_table_exists()

        # Create sync engine
        sync_engine = SyncEngine(fs, db_client)

        # Get diff - should show resources grouped by schema
        diffs = sync_engine.diff_connection("test-db")
        assert len(diffs) == 2
        assert "_agents" in diffs
        assert "custom_schema" in diffs

        # Push all
        diffs, results = sync_engine.push_connection("test-db")
        assert len(results) == 2

        # Filter by schema
        resources_agents = fs.discover_resources("test-db", target_schema_filter="_agents")
        assert len(resources_agents) == 1
        assert resources_agents[0].resource_name == "agents_table"

        resources_custom = fs.discover_resources("test-db", target_schema_filter="custom_schema")
        assert len(resources_custom) == 1
        assert resources_custom[0].resource_name == "custom_table"

    def test_validation_workflow(self, integration_workspace):
        """Test validation catches errors."""
        workspace_root = integration_workspace["workspace_root"]
        conn_dir = integration_workspace["conn_dir"]

        fs = FileSystemManager(workspace_root)

        # Create resource with missing required field
        invalid_file = conn_dir / "invalid.md"
        invalid_post = frontmatter.Post(
            "# Invalid Resource",
            resource_type="table",
            # Missing resource_name
            target_schema="_agents",
        )
        with open(invalid_file, "w") as f:
            f.write(frontmatter.dumps(invalid_post))

        # Validation should catch this
        resources, errors = fs.validate_resources("test-db")
        assert len(errors) > 0

    def test_deterministic_sync(self, integration_workspace):
        """Test that sync is deterministic (DB = local files exactly)."""
        workspace_root = integration_workspace["workspace_root"]
        conn_dir = integration_workspace["conn_dir"]
        db_path = integration_workspace["db_path"]

        fs = FileSystemManager(workspace_root)

        # Create 2 resources
        for i in range(2):
            resource_file = conn_dir / f"resource{i}.md"
            post = frontmatter.Post(
                f"# Resource {i}",
                resource_type="table",
                resource_name=f"resource{i}",
                target_schema="_agents",
            )
            with open(resource_file, "w") as f:
                f.write(frontmatter.dumps(post))

        # Set up and push
        conn_config = fs.load_connection_config("test-db")
        conn_manager = ConnectionManager(conn_config)
        engine = conn_manager.get_engine()
        db_client = DatabaseClient(engine)
        db_client.ensure_table_exists()

        sync_engine = SyncEngine(fs, db_client)
        sync_engine.push_connection("test-db")

        # Verify 2 in database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM _agents")
        assert cursor.fetchone()[0] == 2
        conn.close()

        # Delete 1 local file
        (conn_dir / "resource1.md").unlink()

        # Push again - should delete from DB
        sync_engine.push_connection("test-db")

        # Verify only 1 remains
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM _agents")
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_connection_manager_uri_rendering(self, integration_workspace):
        """Test connection URI rendering with environment variables."""
        workspace_root = integration_workspace["workspace_root"]
        conn_dir = integration_workspace["conn_dir"]

        # Update connection config to use environment variable
        conn_agents = conn_dir / "AGENTS.md"
        conn_post = frontmatter.Post(
            "# Test Database",
            sqlalchemy_uri="sqlite:///{{ env.TEST_DB_PATH }}",
            default_target_schema="_agents",
        )
        with open(conn_agents, "w") as f:
            f.write(frontmatter.dumps(conn_post))

        fs = FileSystemManager(workspace_root)
        conn_config = fs.load_connection_config("test-db")

        # Should fail without env var
        conn_manager = ConnectionManager(conn_config)
        with pytest.raises(ValueError, match="Missing environment variable"):
            conn_manager.get_connection_uri()

        # Should work with env var
        import os

        os.environ["TEST_DB_PATH"] = "/tmp/test.db"
        uri = conn_manager.get_connection_uri()
        assert uri == "sqlite:////tmp/test.db"
