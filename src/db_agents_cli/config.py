"""Configuration and connection management for DB-AGENTS CLI."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .models import ConnectionConfig


class ConnectionManager:
    """Manages database connections with secret handling."""

    def __init__(self, config: ConnectionConfig):
        """Initialize ConnectionManager.

        Args:
            config: ConnectionConfig with connection details
        """
        self.config = config
        self._engine: Engine | None = None
        # Load .env file if present
        load_dotenv()

    def get_connection_uri(self) -> str:
        """Render connection URI template with environment variables.

        Returns:
            Rendered connection URI string

        Raises:
            ValueError: If template rendering fails due to missing or invalid variables
        """
        # Pass all environment variables to the template renderer
        rendered_uri = self.config.get_rendered_uri(dict(os.environ))
        return rendered_uri

    def get_masked_uri(self) -> str:
        """Get connection URI with password masked for display purposes.

        Returns:
            Connection URI with password replaced by '***'
        """
        try:
            uri = self.get_connection_uri()
            # Simple password masking: replace password in URL
            # Format: scheme://user:password@host/path
            if "://" in uri and "@" in uri:
                scheme_and_rest = uri.split("://", 1)
                if len(scheme_and_rest) == 2:
                    scheme, rest = scheme_and_rest
                    if "@" in rest:
                        userpass_and_hostpath = rest.split("@", 1)
                        if len(userpass_and_hostpath) == 2:
                            userpass, hostpath = userpass_and_hostpath
                            if ":" in userpass:
                                user, _ = userpass.split(":", 1)
                                return f"{scheme}://{user}:***@{hostpath}"
            return uri
        except Exception:
            return "***"

    def get_engine(self) -> Engine:
        """Get or create SQLAlchemy engine.

        Returns:
            SQLAlchemy Engine instance

        Raises:
            ValueError: If connection URI template rendering fails
            Exception: If engine creation fails
        """
        if self._engine is None:
            uri = self.get_connection_uri()
            self._engine = create_engine(uri)
        return self._engine

    def test_connection(self) -> tuple[bool, str | None]:
        """Test database connection without executing queries.

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            engine = self.get_engine()
            with engine.connect() as conn:
                # Simple query to test connection
                conn.execute(text("SELECT 1"))
                conn.commit()
            return True, None
        except Exception as e:
            return False, str(e)

    def close(self):
        """Close the database connection."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
