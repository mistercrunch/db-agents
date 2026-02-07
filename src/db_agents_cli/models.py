"""Pydantic models for DB-AGENTS CLI."""

from pathlib import Path

from jinja2 import StrictUndefined, Template, TemplateSyntaxError, UndefinedError
from pydantic import BaseModel, Field, field_validator


class Resource(BaseModel):
    """Complete resource - metadata defines everything."""

    resource_type: str = Field(..., description="Type: global, domain, table, column, etc.")
    resource_name: str = Field(..., description="Identifier like 'ecommerce.orders' or 'global'")
    target_schema: str = Field(default="_agents", description="DB schema to sync to")
    description: str | None = Field(None, description="Short summary for indexing")
    full_markdown: str = Field(..., description="Everything after frontmatter")

    # Tracking
    source_file: Path | None = Field(None, description="Local file path", exclude=True)

    @field_validator("resource_name")
    @classmethod
    def validate_resource_name(cls, v: str) -> str:
        """Validate resource_name is not empty."""
        if not v or not v.strip():
            raise ValueError("resource_name cannot be empty")
        return v.strip()

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        """Validate resource_type is not empty."""
        if not v or not v.strip():
            raise ValueError("resource_type cannot be empty")
        return v.strip()


class ConnectionConfig(BaseModel):
    """Connection config from AGENTS.md frontmatter."""

    sqlalchemy_uri: str = Field(..., description="SQLAlchemy URI with Jinja2 templates")
    default_target_schema: str = Field(
        default="_agents", description="Default schema for resources"
    )
    display_name: str | None = Field(None, description="Human-readable connection name")

    def get_rendered_uri(self, env: dict[str, str]) -> str:
        """Render Jinja2 template with environment variables.

        Args:
            env: Dictionary of environment variables to use in template rendering

        Returns:
            Rendered connection URI string

        Raises:
            ValueError: If template syntax is invalid or required variables are missing
        """
        try:
            template = Template(self.sqlalchemy_uri, undefined=StrictUndefined)
            rendered = template.render(env=env)
            return rendered
        except TemplateSyntaxError as e:
            raise ValueError(f"Invalid template syntax in sqlalchemy_uri: {e}")
        except UndefinedError as e:
            raise ValueError(f"Missing environment variable in sqlalchemy_uri: {e}")


class WorkspaceConfig(BaseModel):
    """Root AGENTS.md frontmatter."""

    version: int = 1
    default_connection: str | None = None
    settings: dict = Field(default_factory=dict)
