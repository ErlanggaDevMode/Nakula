"""
CLI entry point for DB Schema Visualizer.

Usage examples::

    # Minimal – just the DB URL, outputs erd.png
    dbviz extract -d sqlite:///mydb.db

    # Output format inferred from extension
    dbviz extract -d sqlite:///mydb.db -o diagram.html
    dbviz extract -d sqlite:///mydb.db -o diagram.svg

    # PostgreSQL, public schema only
    dbviz extract -d postgresql://user:pw@host/mydb -o erd.html --schema public

    # Show DOT source
    dbviz dot -d sqlite:///mydb.db
"""

from __future__ import annotations

import logging
import sys
from typing import Optional, Tuple

import click

from db_schema_visualizer import config
from db_schema_visualizer.extractor.sqlalchemy_extractor import SqlAlchemyExtractor
from db_schema_visualizer.graph.builder import GraphBuilder
from db_schema_visualizer.graph.layout import graph_to_dot
from db_schema_visualizer.renderer.graphviz_renderer import GraphvizRenderer
from db_schema_visualizer.renderer.html_renderer import HtmlRenderer
from db_schema_visualizer.utils.filters import filter_tables

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=config.VERSION, prog_name=config.APP_NAME)
def cli() -> None:
    """DB Schema Visualizer – generate ERDs from relational databases."""


# ---------------------------------------------------------------------------
# extract command
# ---------------------------------------------------------------------------

@cli.command("extract")
@click.option(
    "-d", "--db",
    required=True,
    metavar="URL",
    help="SQLAlchemy database URL.  Examples:\n\n"
         "  sqlite:///path/to/db.db\n\n"
         "  postgresql://user:pw@host/dbname\n\n"
         "  mysql+pymysql://user:pw@host/dbname",
)
@click.option(
    "-o", "--output",
    default="erd",
    show_default=True,
    metavar="PATH",
    help="Output file path. Format is inferred from the extension "
         "(e.g. diagram.html → HTML, diagram.svg → SVG). "
         "Use -f to override.",
)
@click.option(
    "-f", "--format",
    "fmt",
    type=click.Choice(["png", "svg", "pdf", "html"], case_sensitive=False),
    default=None,
    help="Output format (png/svg/pdf/html). "
         "Inferred from -o extension when omitted; falls back to png.",
)
@click.option(
    "--schema",
    "schemas",
    multiple=True,
    metavar="SCHEMA",
    help="Restrict extraction to this schema (repeatable).  "
         "Omit to include all schemas.",
)
@click.option(
    "--tables",
    "tables",
    multiple=True,
    metavar="TABLE",
    help="Include only these table names (repeatable, supports * wildcards).",
)
@click.option(
    "--exclude-tables",
    "exclude_tables",
    multiple=True,
    metavar="PATTERN",
    help="Exclude tables matching this pattern (repeatable, supports * wildcards).",
)
@click.option(
    "--no-many-to-many",
    "no_m2m",
    is_flag=True,
    default=False,
    help="Disable detection and collapsing of many-to-many junction tables.",
)
@click.option(
    "--collapse-m2n",
    "collapse_m2n",
    is_flag=True,
    default=False,
    help="When M:N junction tables are detected, replace them with a single "
         "direct edge between the two referenced tables.",
)
@click.option(
    "--direction",
    type=click.Choice(["LR", "TB"], case_sensitive=True),
    default="LR",
    show_default=True,
    help="Graph layout direction: LR (left→right) or TB (top→bottom).",
)
@click.option(
    "--title",
    default=None,
    metavar="TEXT",
    help="Custom title for the HTML diagram (HTML format only).",
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Enable debug logging.")
def extract(
    db: str,
    output: str,
    fmt: Optional[str],
    schemas: Tuple[str, ...],
    tables: Tuple[str, ...],
    exclude_tables: Tuple[str, ...],
    no_m2m: bool,
    collapse_m2n: bool,
    direction: str,
    title: Optional[str],
    verbose: bool,
) -> None:
    """Extract schema metadata and generate an ERD diagram."""
    _setup_logging(verbose)
    logger = logging.getLogger(__name__)

    # Infer format from output extension when -f is not given
    _ext_to_fmt = {"png": "png", "svg": "svg", "pdf": "pdf", "html": "html"}
    if fmt is None:
        ext = output.rsplit(".", 1)[-1].lower() if "." in output else ""
        fmt = _ext_to_fmt.get(ext, "png")  # default to png

    # -- 1. Extract ----------------------------------------------------------
    click.echo(f"Connecting to database…")
    try:
        extractor = SqlAlchemyExtractor(db)
        db_schema = extractor.extract(
            schemas=list(schemas) or None,
            tables=list(tables) or None,
            include_many_to_many=not no_m2m,
        )
    except ConnectionError as exc:
        click.secho(f"Connection error: {exc}", fg="red", err=True)
        sys.exit(1)
    except Exception as exc:
        click.secho(f"Extraction failed: {exc}", fg="red", err=True)
        logger.exception("Unexpected extraction error")
        sys.exit(1)

    click.echo(
        f"Extracted {len(db_schema.tables)} tables, "
        f"{len(db_schema.relationships)} relationships."
    )

    if not db_schema.tables:
        click.secho("No tables found – nothing to render.", fg="yellow")
        sys.exit(0)

    # -- 2. Filter -----------------------------------------------------------
    if exclude_tables:
        db_schema = filter_tables(
            db_schema,
            exclude_tables=list(exclude_tables),
        )
        click.echo(f"After filtering: {len(db_schema.tables)} tables.")

    # -- 3. Build graph ------------------------------------------------------
    builder = GraphBuilder(collapse_many_to_many=collapse_m2n)
    graph = builder.build(db_schema)

    # -- 4. Render -----------------------------------------------------------
    fmt_lower = fmt.lower()
    try:
        if fmt_lower == "html":
            page_title = title or f"{db_schema.name or 'Schema'} – DB Schema Visualizer"
            renderer = HtmlRenderer(title=page_title)
        else:
            renderer = GraphvizRenderer(fmt=fmt_lower, direction=direction)  # type: ignore[arg-type]

        result_path = renderer.render(graph, output)
        click.secho(f"✓ Diagram saved to: {result_path}", fg="green")

    except RuntimeError as exc:
        click.secho(f"Render error: {exc}", fg="red", err=True)
        sys.exit(1)
    except Exception as exc:
        click.secho(f"Unexpected render error: {exc}", fg="red", err=True)
        logger.exception("Unexpected render error")
        sys.exit(1)


# ---------------------------------------------------------------------------
# dot command – print DOT source to stdout
# ---------------------------------------------------------------------------

@cli.command("dot")
@click.option("-d", "--db", required=True, metavar="URL", help="SQLAlchemy database URL.")
@click.option(
    "--schema", "schemas", multiple=True, metavar="SCHEMA",
    help="Restrict to this schema (repeatable).",
)
@click.option(
    "--tables", "tables", multiple=True, metavar="TABLE",
    help="Include only these tables (repeatable).",
)
@click.option(
    "--no-many-to-many", "no_m2m", is_flag=True, default=False,
    help="Disable M:N detection.",
)
@click.option(
    "--direction", type=click.Choice(["LR", "TB"]), default="LR",
    help="Graph direction.",
)
@click.option("-v", "--verbose", is_flag=True, default=False)
def dot_command(
    db: str,
    schemas: Tuple[str, ...],
    tables: Tuple[str, ...],
    no_m2m: bool,
    direction: str,
    verbose: bool,
) -> None:
    """Print the Graphviz DOT source to stdout without rendering."""
    _setup_logging(verbose)
    try:
        extractor = SqlAlchemyExtractor(db)
        db_schema = extractor.extract(
            schemas=list(schemas) or None,
            tables=list(tables) or None,
            include_many_to_many=not no_m2m,
        )
    except ConnectionError as exc:
        click.secho(f"Connection error: {exc}", fg="red", err=True)
        sys.exit(1)

    graph = GraphBuilder().build(db_schema)
    click.echo(graph_to_dot(graph, direction=direction))


# ---------------------------------------------------------------------------
# list-tables command
# ---------------------------------------------------------------------------

@cli.command("list-tables")
@click.option("-d", "--db", required=True, metavar="URL", help="SQLAlchemy database URL.")
@click.option("--schema", "schemas", multiple=True, metavar="SCHEMA")
@click.option("-v", "--verbose", is_flag=True, default=False)
def list_tables(db: str, schemas: Tuple[str, ...], verbose: bool) -> None:
    """List all tables in the database."""
    _setup_logging(verbose)
    try:
        extractor = SqlAlchemyExtractor(db)
        db_schema = extractor.extract(schemas=list(schemas) or None)
    except ConnectionError as exc:
        click.secho(f"Connection error: {exc}", fg="red", err=True)
        sys.exit(1)

    for table in sorted(db_schema.tables, key=lambda t: t.qualified_name):
        m2n_flag = " [junction]" if table.is_junction else ""
        click.echo(f"  {table.qualified_name}{m2n_flag}")

    click.echo(f"\nTotal: {len(db_schema.tables)} tables.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Registered CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
