"""Production database export module.

This module handles exporting data from the production PostgreSQL database
using pg_dump and creating a SQL dump file for anonymization.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def export_database(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    output_file: str,
    verbose: bool = False,
) -> bool:
    """Export PostgreSQL database to SQL dump file.

    Uses pg_dump to create a complete database dump including schema and data.
    The dump is saved to the specified output file.

    Args:
        host: PostgreSQL server hostname
        port: PostgreSQL server port
        database: Database name to export
        user: Database user for authentication
        password: Database password for authentication
        output_file: Path where SQL dump will be saved
        verbose: Enable verbose output

    Returns:
        True if export succeeded, False otherwise

    Raises:
        FileNotFoundError: If pg_dump is not found in PATH
        RuntimeError: If pg_dump command fails
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Construct pg_dump command
    cmd = [
        "pg_dump",
        "-h", host,
        "-p", str(port),
        "-U", user,
        "-d", database,
        "--no-password",
        "--create",  # Include CREATE DATABASE statement
        "--verbose" if verbose else "-q",  # Quiet by default
        "-f", str(output_path),
    ]

    # Set environment variable for password to avoid prompt
    env_vars = os.environ.copy()
    env_vars["PGPASSWORD"] = password

    try:
        if verbose:
            print(f"Starting pg_dump export to {output_path}")

        # Run pg_dump
        result = subprocess.run(
            cmd,
            env=env_vars,
            check=False,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            error_msg = result.stderr or f"pg_dump failed with code {result.returncode}"
            raise RuntimeError(f"pg_dump export failed: {error_msg}")

        if verbose:
            print(f"Export completed successfully: {output_path}")
            print(f"File size: {output_path.stat().st_size} bytes")

        return True

    except FileNotFoundError:
        raise FileNotFoundError(
            "pg_dump not found. Please install PostgreSQL client tools."
        )


def export_database_with_filtering(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    output_file: str,
    tables: Optional[list[str]] = None,
    exclude_tables: Optional[list[str]] = None,
) -> bool:
    """Export specific tables from PostgreSQL database.

    Allows selective export by including or excluding tables.

    Args:
        host: PostgreSQL server hostname
        port: PostgreSQL server port
        database: Database name to export
        user: Database user for authentication
        password: Database password for authentication
        output_file: Path where SQL dump will be saved
        tables: List of table names to include (if None, exports all)
        exclude_tables: List of table names to exclude

    Returns:
        True if export succeeded, False otherwise

    Raises:
        FileNotFoundError: If pg_dump is not found in PATH
        RuntimeError: If pg_dump command fails
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build command
    cmd = [
        "pg_dump",
        "-h", host,
        "-p", str(port),
        "-U", user,
        "-d", database,
        "--no-password",
        "-q",
        "-f", str(output_path),
    ]

    # Add table filters
    if tables:
        for table in tables:
            cmd.extend(["-t", table])
    elif exclude_tables:
        for table in exclude_tables:
            cmd.extend(["-T", table])

    # Set password environment variable
    import os
    env_vars = os.environ.copy()
    env_vars["PGPASSWORD"] = password

    try:
        result = subprocess.run(
            cmd,
            env=env_vars,
            check=False,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            error_msg = result.stderr or f"pg_dump failed with code {result.returncode}"
            raise RuntimeError(f"pg_dump export failed: {error_msg}")

        return True

    except FileNotFoundError:
        raise FileNotFoundError(
            "pg_dump not found. Please install PostgreSQL client tools."
        )


if __name__ == "__main__":
    import os as _os
    import argparse

    parser = argparse.ArgumentParser(description="Export production database")
    parser.add_argument("--host", required=True, help="Database host")
    parser.add_argument("--port", type=int, default=5432, help="Database port")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--user", required=True, help="Database user")
    parser.add_argument("--password", required=True, help="Database password")
    parser.add_argument("--output", required=True, help="Output SQL file path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        success = export_database(
            host=args.host,
            port=args.port,
            database=args.database,
            user=args.user,
            password=args.password,
            output_file=args.output,
            verbose=args.verbose,
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
