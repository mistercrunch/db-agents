"""Utility functions for Rich formatting and output."""

from rich.console import Console
from rich.table import Table

from .models import Resource
from .sync import SchemaDiff

console = Console()


def print_error(message: str) -> None:
    """Print error message in red."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print success message in green."""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print info message in blue."""
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def format_resource_table(resources: list[Resource], title: str = "Resources") -> Table:
    """Format resources as a Rich table.

    Args:
        resources: List of Resource objects
        title: Title for the table

    Returns:
        Rich Table object
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Description", style="dim")
    table.add_column("File", style="yellow", no_wrap=True)

    for resource in resources:
        file_path = str(resource.source_file) if resource.source_file else "N/A"
        description = resource.description or ""
        table.add_row(
            resource.resource_type,
            resource.resource_name,
            description,
            file_path,
        )

    return table


def print_diff_summary(diffs: dict[str, SchemaDiff]) -> None:
    """Print summary of diffs across schemas.

    Args:
        diffs: Dictionary mapping schema to SchemaDiff
    """
    has_any_changes = any(diff.has_changes for diff in diffs.values())

    if not has_any_changes:
        print_success("No changes detected. Local files match database.")
        return

    for schema, diff in diffs.items():
        if not diff.has_changes:
            continue

        console.print(f"\n[bold]Target Schema:[/bold] [cyan]{schema}[/cyan]")

        if diff.added:
            console.print(f"\n[bold green]Added ({len(diff.added)}):[/bold green]")
            for resource in diff.added:
                file_path = str(resource.source_file) if resource.source_file else "?"
                console.print(f"  [green]A[/green] {file_path}")
                console.print(f"    → {resource.resource_type}: {resource.resource_name}")

        if diff.modified:
            console.print(f"\n[bold yellow]Modified ({len(diff.modified)}):[/bold yellow]")
            for local, db in diff.modified:
                file_path = str(local.source_file) if local.source_file else "?"
                console.print(f"  [yellow]M[/yellow] {file_path}")
                console.print(f"    → {local.resource_type}: {local.resource_name}")

        if diff.deleted:
            console.print(f"\n[bold red]Deleted ({len(diff.deleted)}):[/bold red]")
            for resource in diff.deleted:
                console.print(f"  [red]D[/red] {resource.resource_type}: {resource.resource_name}")
            console.print(
                "\n  [bold red]WARNING:[/bold red] These resources exist in the database "
                "but not in local files."
            )
            console.print("  They will be [bold red]DELETED[/bold red] from the database on push!")

    # Print summary
    total_added = sum(len(d.added) for d in diffs.values())
    total_modified = sum(len(d.modified) for d in diffs.values())
    total_deleted = sum(len(d.deleted) for d in diffs.values())

    console.print(
        f"\n[bold]Summary:[/bold] {total_added} added, "
        f"{total_modified} modified, {total_deleted} deleted"
    )


def print_validation_results(
    is_valid: bool, errors: list[str], warnings: list[str], connection_name: str
) -> None:
    """Print validation results.

    Args:
        is_valid: Whether validation passed
        errors: List of error messages
        warnings: List of warning messages
        connection_name: Name of connection being validated
    """
    console.print(f"\n[bold]Validating connection:[/bold] [cyan]{connection_name}[/cyan]")

    if errors:
        console.print(f"\n[bold red]Errors ({len(errors)}):[/bold red]")
        for error in errors:
            console.print(f"  [red]✗[/red] {error}")

    if warnings:
        console.print(f"\n[bold yellow]Warnings ({len(warnings)}):[/bold yellow]")
        for warning in warnings:
            console.print(f"  [yellow]⚠[/yellow] {warning}")

    if is_valid and not warnings:
        print_success(f"All files valid in {connection_name}")
    elif is_valid:
        print_warning(f"Validation passed with {len(warnings)} warning(s)")
    else:
        print_error(f"Validation failed with {len(errors)} error(s)")


def confirm_push(diffs: dict[str, SchemaDiff]) -> bool:
    """Prompt user to confirm push operation.

    Args:
        diffs: Dictionary mapping schema to SchemaDiff

    Returns:
        True if user confirms, False otherwise
    """
    total_changes = sum(d.total_changes for d in diffs.values())
    total_deleted = sum(len(d.deleted) for d in diffs.values())

    if total_deleted > 0:
        console.print(
            f"\n[bold red]WARNING:[/bold red] {total_deleted} resource(s) "
            f"will be DELETED from the database!"
        )

    response = console.input(
        f"\n[bold]Push {total_changes} change(s) to database?[/bold] [dim](y/N)[/dim]: "
    )

    return response.lower() in ("y", "yes")


def print_push_results(results: dict[str, tuple[int, int, int]], connection_name: str) -> None:
    """Print results of push operation.

    Args:
        results: Dictionary mapping schema to (inserted, updated, deleted) counts
        connection_name: Name of connection that was pushed
    """
    console.print(f"\n[bold green]✓[/bold green] Push completed for [cyan]{connection_name}[/cyan]")

    for schema, (inserted, updated, deleted) in results.items():
        total = inserted + updated + deleted
        console.print(f"\n[bold]Schema:[/bold] [cyan]{schema}[/cyan] ({total} change(s))")
        if inserted > 0:
            console.print(f"  [green]+ {inserted} inserted[/green]")
        if updated > 0:
            console.print(f"  [yellow]~ {updated} updated[/yellow]")
        if deleted > 0:
            console.print(f"  [red]- {deleted} deleted[/red]")


def print_connection_list(connections: dict[str, dict]) -> None:
    """Print list of connections with status.

    Args:
        connections: Dictionary mapping connection name to connection info
    """
    if not connections:
        print_warning(
            "No connections found. Run 'db-agents init --connection <name>' to create one."
        )
        return

    table = Table(title="Available Connections", show_header=True)
    table.add_column("Connection", style="cyan", no_wrap=True)
    table.add_column("URI", style="dim")
    table.add_column("Status", style="green")
    table.add_column("Resources", style="magenta")

    for name, info in connections.items():
        status = info.get("status", "unknown")
        uri = info.get("uri", "N/A")
        resource_count = info.get("resource_count", 0)

        status_display = "✓ Connected" if status == "connected" else "✗ Failed"
        status_style = "green" if status == "connected" else "red"

        table.add_row(
            name,
            uri,
            f"[{status_style}]{status_display}[/{status_style}]",
            str(resource_count),
        )

    console.print(table)
