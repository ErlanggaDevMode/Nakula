"""
DB Schema Visualizer
====================

A Python tool that reads relational database metadata via SQLAlchemy and
generates Entity-Relationship Diagrams (ERDs) as static images (PNG/SVG/PDF)
or interactive standalone HTML files.

Public API::

    from sqlalchemy import create_engine
    from db_schema_visualizer import extract_schema, render_schema

    engine = create_engine("sqlite:///mydb.db")

    # Get the schema model
    schema = extract_schema(engine)

    # Render directly
    render_schema(engine, output="diagram", fmt="html")
"""

from __future__ import annotations

from typing import List, Optional, Union

from db_schema_visualizer.config import VERSION

__version__ = VERSION
__author__ = "DB Schema Visualizer Contributors"


# ---------------------------------------------------------------------------
# Convenience public API
# ---------------------------------------------------------------------------

def extract_schema(
    engine_or_url,
    schemas: Optional[List[str]] = None,
    tables: Optional[List[str]] = None,
    include_many_to_many: bool = True,
):
    """Extract database schema metadata and return a :class:`DatabaseSchema`.

    This is the primary library entry point.

    Args:
        engine_or_url: SQLAlchemy :class:`Engine` or connection URL string.
        schemas: Optional list of schema names to include.
        tables: Optional list of table names to include.
        include_many_to_many: Whether to detect junction tables.

    Returns:
        :class:`~db_schema_visualizer.model.schema.DatabaseSchema`

    Example::

        from db_schema_visualizer import extract_schema
        schema = extract_schema("sqlite:///mydb.db")
        for table in schema.tables:
            print(table.name, [c.name for c in table.columns])
    """
    from db_schema_visualizer.extractor.sqlalchemy_extractor import SqlAlchemyExtractor

    extractor = SqlAlchemyExtractor(engine_or_url)
    return extractor.extract(
        schemas=schemas,
        tables=tables,
        include_many_to_many=include_many_to_many,
    )


def render_schema(
    engine_or_url,
    output: str,
    fmt: str = "png",
    schemas: Optional[List[str]] = None,
    tables: Optional[List[str]] = None,
    include_many_to_many: bool = True,
    collapse_many_to_many: bool = False,
    direction: str = "LR",
    title: Optional[str] = None,
) -> str:
    """High-level convenience function: extract + build + render in one call.

    Args:
        engine_or_url: SQLAlchemy Engine or URL.
        output: Output file path (extension appended if missing).
        fmt: ``"png"``, ``"svg"``, ``"pdf"``, or ``"html"``.
        schemas: Schema filter (``None`` = all).
        tables: Table filter (``None`` = all).
        include_many_to_many: Detect junction tables.
        collapse_many_to_many: Replace junction nodes with direct M:N edges.
        direction: Layout direction ``"LR"`` or ``"TB"``.
        title: Custom title for HTML output.

    Returns:
        Path of the written output file.

    Example::

        from db_schema_visualizer import render_schema
        path = render_schema("sqlite:///mydb.db", "erd", fmt="html")
        print(f"Diagram at: {path}")
    """
    from db_schema_visualizer.graph.builder import GraphBuilder
    from db_schema_visualizer.renderer.graphviz_renderer import GraphvizRenderer
    from db_schema_visualizer.renderer.html_renderer import HtmlRenderer

    db_schema = extract_schema(
        engine_or_url,
        schemas=schemas,
        tables=tables,
        include_many_to_many=include_many_to_many,
    )

    builder = GraphBuilder(collapse_many_to_many=collapse_many_to_many)
    graph = builder.build(db_schema)

    fmt_lower = fmt.lower()
    if fmt_lower == "html":
        page_title = title or f"{db_schema.name or 'Schema'} – DB Schema Visualizer"
        renderer = HtmlRenderer(title=page_title)
    else:
        renderer = GraphvizRenderer(fmt=fmt_lower, direction=direction)  # type: ignore[arg-type]

    return renderer.render(graph, output)


__all__ = [
    "__version__",
    "extract_schema",
    "render_schema",
]
