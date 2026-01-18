"""Main entry point for PostgreSQL MCP Server.

This module provides the CLI entry point for running the MCP server
using FastMCP with stdio transport.
"""

import os
import sys
import traceback
from pathlib import Path

# Force UTF-8 encoding to handle Chinese characters in paths
if sys.platform == "win32":
    # Set UTF-8 mode for Python 3.7+
    if hasattr(sys, "set_int_max_str_digits"):
        os.environ["PYTHONUTF8"] = "1"
    # Set console encoding
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

import anyio

from pg_mcp.server import mcp


def setup_emergency_logging() -> None:
    """Setup emergency logging before main logging is configured."""
    import logging

    # Create logs directory if it doesn't exist
    log_dir = Path.cwd()
    log_file = log_dir / "mcp_startup.log"

    # Setup basic logging to file
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8", mode="w"),
            logging.StreamHandler(sys.stderr),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Emergency logging initialized, writing to {log_file}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Current directory: {Path.cwd()}")
    logger.info(f"PYTHONPATH: {sys.path}")

    return logger


def main() -> None:
    """Main entry point for the PostgreSQL MCP Server.

    This function starts the FastMCP server using stdio transport,
    enabling communication with MCP clients.

    The server lifecycle is managed through the lifespan context manager,
    which handles:
    - Configuration loading
    - Database connection pool creation
    - Schema cache initialization
    - Service component setup
    - Graceful shutdown

    Example:
        Run the server:
        >>> python -m pg_mcp

        Run with environment variables:
        >>> DATABASE_HOST=localhost DATABASE_NAME=mydb python -m pg_mcp
    """
    logger = None
    try:
        # Setup emergency logging first
        logger = setup_emergency_logging()
        logger.info("Starting PostgreSQL MCP Server...")

        # Run the server
        anyio.run(mcp.run_stdio_async)

    except Exception as e:
        error_msg = f"Fatal error during server startup: {e}\n{traceback.format_exc()}"

        # Try to log to file
        if logger:
            logger.error(error_msg)

        # Always write to stderr
        print(error_msg, file=sys.stderr)

        # Write to emergency log file
        try:
            with open("mcp_error.log", "w", encoding="utf-8") as f:
                f.write(error_msg)
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
