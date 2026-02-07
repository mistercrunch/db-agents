"""Main CLI entrypoint for DB-AGENTS."""

from pathlib import Path

import typer

from . import __version__
from .config import ConnectionManager
from .database import DatabaseClient, DatabaseError
from .filesystem import FileSystemError, FileSystemManager
from .models import ConnectionConfig, WorkspaceConfig
from .sync import SyncEngine
from .utils import (
    confirm_push,
    console,
    print_connection_list,
    print_diff_summary,
    print_error,
    print_info,
    print_push_results,
    print_success,
    print_validation_results,
    print_warning,
)

# Main app
app = typer.Typer(
    name="db-agents",
    help="Sync DB-AGENTS metadata between databases and local files",
    add_completion=False,
    no_args_is_help=True,  # Show help when no command is provided
)

# Subcommand groups
db_app = typer.Typer(help="Manage database connections")
app.add_typer(db_app, name="db")


def find_workspace_root(start_path: Path | None = None) -> Path | None:
    """Find workspace root by looking for AGENTS.md in current or parent directories.

    Args:
        start_path: Path to start searching from (default: current directory)

    Returns:
        Path to workspace root or None if not found
    """
    current = start_path or Path.cwd()

    # Check current directory and parents
    for path in [current] + list(current.parents):
        agents_file = path / "DB-AGENTS" / "AGENTS.md"
        if agents_file.exists():
            return path / "DB-AGENTS"

        # Also check if current directory itself is the workspace
        if (path / "AGENTS.md").exists():
            return path

    return None


def get_workspace() -> FileSystemManager:
    """Get FileSystemManager for current workspace.

    Returns:
        FileSystemManager instance

    Raises:
        typer.Exit: If workspace not found
    """
    workspace_root = find_workspace_root()
    if workspace_root is None:
        print_error("Not in a DB-AGENTS workspace. Run 'db-agents init' to create one.")
        raise typer.Exit(1)

    return FileSystemManager(workspace_root)


def get_connection_name(workspace: FileSystemManager, connection: str | None = None) -> str:
    """Get connection name, using default if not specified.

    Args:
        workspace: FileSystemManager instance
        connection: Optional connection name

    Returns:
        Connection name to use

    Raises:
        typer.Exit: If connection cannot be determined
    """
    if connection:
        return connection

    # Try to get default connection from workspace config
    try:
        config = workspace.load_workspace_config()
        if config.default_connection:
            return config.default_connection
    except Exception:
        pass

    # If no default, try to find the only connection
    connections = workspace.list_connections()
    if len(connections) == 1:
        return connections[0]
    elif len(connections) == 0:
        print_error("No connections found. Run 'db-agents init --connection <name>' to create one.")
        raise typer.Exit(1)
    else:
        print_error(
            f"Multiple connections found. Please specify one with --connection: "
            f"{', '.join(connections)}"
        )
        raise typer.Exit(1)


@app.command()
def init(
    connection: str | None = typer.Option(
        None, "--connection", "-c", help="Create connection with this name"
    ),
    uri: str | None = typer.Option(None, "--uri", help="SQLAlchemy URI for connection"),
    display_name: str | None = typer.Option(
        None, "--display-name", help="Display name for connection"
    ),
):
    """Initialize DB-AGENTS workspace or add a connection."""
    # Determine workspace root
    workspace_root = find_workspace_root()

    if workspace_root is None:
        # Create new workspace
        workspace_root = Path.cwd() / "DB-AGENTS"
        workspace = FileSystemManager(workspace_root)

        try:
            workspace.create_workspace(WorkspaceConfig())
            print_success(f"Initialized DB-AGENTS workspace at {workspace_root}")
        except FileSystemError as e:
            print_error(str(e))
            raise typer.Exit(1)

    else:
        workspace = FileSystemManager(workspace_root)
        print_info(f"Using existing workspace at {workspace_root}")

    # Create connection if requested
    if connection:
        # Prompt for URI if not provided
        if not uri:
            console.print(
                "\n[bold]Enter SQLAlchemy URI[/bold] "
                "(use Jinja2 templates for secrets, e.g., {{ env.PASSWORD }}):"
            )
            console.print(
                "[dim]Examples:[/dim]\n"
                "  postgresql://user:{{ env.DB_PASSWORD }}@host:5432/database\n"
                "  mysql://user:{{ env.DB_PASSWORD }}@host:3306/database\n"
                "  {{ env.DATABASE_URL }}"
            )
            uri = console.input("[bold]URI:[/bold] ")

            if not uri:
                print_error("URI is required")
                raise typer.Exit(1)

        # Prompt for display name if not provided
        if not display_name:
            display_name = console.input(
                f"[bold]Display name[/bold] [dim](default: {connection})[/dim]: "
            )
            if not display_name:
                display_name = connection

        try:
            connection_config = ConnectionConfig(sqlalchemy_uri=uri, display_name=display_name)
            workspace.create_connection(connection, connection_config, create_example=True)
            print_success(f"Created connection '{connection}' at {workspace_root / connection}")
            print_info(f"Example resource file created: {connection}/global.md")
        except FileSystemError as e:
            print_error(str(e))
            raise typer.Exit(1)


@app.command()
def validate(
    connection: str | None = typer.Option(
        None, "--connection", "-c", help="Connection to validate"
    ),
):
    """Validate local files without touching database."""
    workspace = get_workspace()
    connection_name = get_connection_name(workspace, connection)

    try:
        # Load connection config
        conn_config = workspace.load_connection_config(connection_name)
        conn_manager = ConnectionManager(conn_config)
        engine = conn_manager.get_engine()
        db_client = DatabaseClient(engine)

        # Create sync engine
        sync_engine = SyncEngine(workspace, db_client)

        # Validate
        is_valid, errors, warnings = sync_engine.validate_connection(connection_name)

        # Print results
        print_validation_results(is_valid, errors, warnings, connection_name)

        # Count resources
        if is_valid:
            resources = workspace.discover_resources(connection_name)
            console.print(f"\n[bold]{len(resources)}[/bold] resource(s) found")

        if not is_valid:
            raise typer.Exit(1)

    except (FileSystemError, DatabaseError) as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def diff(
    connection: str | None = typer.Option(None, "--connection", "-c", help="Connection to diff"),
    target_schema: str | None = typer.Option(
        None, "--target-schema", "-s", help="Filter by target schema"
    ),
):
    """Compare local files to database state."""
    workspace = get_workspace()
    connection_name = get_connection_name(workspace, connection)

    try:
        # Load connection config
        conn_config = workspace.load_connection_config(connection_name)
        conn_manager = ConnectionManager(conn_config)

        console.print(f"\n[bold]Connection:[/bold] [cyan]{connection_name}[/cyan]")
        console.print(f"[bold]URI:[/bold] [dim]{conn_manager.get_masked_uri()}[/dim]")

        # Get engine and create clients
        engine = conn_manager.get_engine()
        db_client = DatabaseClient(engine)

        # Ensure table exists
        if not db_client.table_exists():
            print_warning(
                "Database table does not exist. Run 'db-agents push' to create and populate it."
            )
            # Show what would be added
            resources = workspace.discover_resources(connection_name, target_schema)
            console.print(f"\n[bold green]{len(resources)} resource(s) would be added[/bold green]")
            for resource in resources:
                console.print(
                    f"  [green]A[/green] {resource.resource_type}: {resource.resource_name}"
                )
            return

        # Create sync engine and get diff
        sync_engine = SyncEngine(workspace, db_client)
        diffs = sync_engine.diff_connection(connection_name, target_schema)

        # Print diff summary
        print_diff_summary(diffs)

    except (FileSystemError, DatabaseError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def push(
    connection: str | None = typer.Option(None, "--connection", "-c", help="Connection to push"),
    target_schema: str | None = typer.Option(
        None, "--target-schema", "-s", help="Filter by target schema"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would change without applying"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Push local files to database (deterministic sync)."""
    workspace = get_workspace()
    connection_name = get_connection_name(workspace, connection)

    try:
        # Load connection config
        conn_config = workspace.load_connection_config(connection_name)
        conn_manager = ConnectionManager(conn_config)

        console.print(f"\n[bold]Connection:[/bold] [cyan]{connection_name}[/cyan]")
        console.print(f"[bold]URI:[/bold] [dim]{conn_manager.get_masked_uri()}[/dim]")

        # Get engine and create clients
        engine = conn_manager.get_engine()
        db_client = DatabaseClient(engine)

        # Ensure schema and table exist
        console.print("\n[dim]Ensuring database schema and table exist...[/dim]")
        db_client.ensure_table_exists()

        # Create sync engine
        sync_engine = SyncEngine(workspace, db_client)

        # Get diff and push
        diffs, results = sync_engine.push_connection(
            connection_name, dry_run=dry_run, target_schema_filter=target_schema
        )

        # Print diff
        print_diff_summary(diffs)

        # If dry run, stop here
        if dry_run:
            print_info("Dry run - no changes applied")
            return

        # Check if there are any changes
        has_changes = any(d.has_changes for d in diffs.values())
        if not has_changes:
            return

        # Confirm unless --force
        if not force:
            if not confirm_push(diffs):
                print_info("Push cancelled")
                return

        # Already pushed (sync_engine.push_connection does the work)
        # Print results
        print_push_results(results, connection_name)

    except (FileSystemError, DatabaseError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)


@db_app.command("list")
def db_list():
    """List all database connections."""
    workspace = get_workspace()

    try:
        connections = workspace.list_connections()
        connection_info = {}

        for conn_name in connections:
            try:
                # Load config
                conn_config = workspace.load_connection_config(conn_name)
                conn_manager = ConnectionManager(conn_config)

                # Test connection
                success, error = conn_manager.test_connection()

                # Count resources
                resources = workspace.discover_resources(conn_name)

                connection_info[conn_name] = {
                    "uri": conn_manager.get_masked_uri(),
                    "status": "connected" if success else "failed",
                    "error": error,
                    "resource_count": len(resources),
                }

            except Exception as e:
                connection_info[conn_name] = {
                    "uri": "N/A",
                    "status": "error",
                    "error": str(e),
                    "resource_count": 0,
                }

        print_connection_list(connection_info)

    except FileSystemError as e:
        print_error(str(e))
        raise typer.Exit(1)


@db_app.command("test")
def db_test(
    connection: str = typer.Argument(..., help="Connection name to test"),
):
    """Test database connection."""
    workspace = get_workspace()

    try:
        # Load connection config
        conn_config = workspace.load_connection_config(connection)
        conn_manager = ConnectionManager(conn_config)

        console.print(f"\n[bold]Testing connection:[/bold] [cyan]{connection}[/cyan]")
        console.print(f"[bold]URI:[/bold] [dim]{conn_manager.get_masked_uri()}[/dim]")

        with console.status("[bold blue]Connecting..."):
            success, error = conn_manager.test_connection()

        if success:
            print_success(f"Successfully connected to {connection}")

            # Check if table exists
            engine = conn_manager.get_engine()
            db_client = DatabaseClient(engine)

            if db_client.table_exists():
                print_info("Table _agents._agents exists")
                resources = db_client.pull_all_resources()
                console.print(f"[bold]{len(resources)}[/bold] resource(s) in database")
            else:
                print_warning("Table _agents._agents does not exist")
                print_info("Run 'db-agents push' to create and populate it")

        else:
            print_error(f"Failed to connect: {error}")
            raise typer.Exit(1)

    except (FileSystemError, ValueError) as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print(f"db-agents version [bold cyan]{__version__}[/bold cyan]")


def main():
    """Main entrypoint."""
    app()


if __name__ == "__main__":
    main()
