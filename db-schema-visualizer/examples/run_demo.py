"""
Demo script – shows all three usage patterns:

1. CLI-style: generate PNG, SVG, and HTML from sample.db
2. Library API: use extract_schema() directly
3. Advanced: collapse M:N junction tables into direct edges

Run with:
    python examples/run_demo.py
"""

from __future__ import annotations

import os
import sys

# Ensure the project root is on the path when running without install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from examples.create_sample_db import DB_PATH, create_sample_db

DB_URL = f"sqlite:///{DB_PATH}"
OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)


def demo_library_api() -> None:
    """Demonstrate using db_schema_visualizer as a Python library."""
    print("\n=== Library API demo ===")
    from db_schema_visualizer import extract_schema, render_schema

    schema = extract_schema(DB_URL)
    print(f"Extracted schema: {schema}")
    for table in schema.tables:
        j = " [junction]" if table.is_junction else ""
        print(f"  {table.qualified_name}{j}: {len(table.columns)} columns, "
              f"{len(table.foreign_keys)} FKs")

    print("\nRelationships:")
    for rel in schema.relationships:
        print(f"  {rel}")


def demo_html_output() -> None:
    """Generate the interactive HTML diagram."""
    print("\n=== HTML output demo ===")
    from db_schema_visualizer import render_schema

    path = render_schema(
        DB_URL,
        output=os.path.join(OUT_DIR, "sample_erd"),
        fmt="html",
        title="Sample E-Commerce Schema",
    )
    print(f"HTML diagram → {path}")
    print("Open in your browser to interact (drag nodes, zoom, search).")


def demo_collapsed_m2n() -> None:
    """Generate HTML with M:N junctions collapsed to direct edges."""
    print("\n=== Collapsed M:N demo ===")
    from db_schema_visualizer import render_schema

    path = render_schema(
        DB_URL,
        output=os.path.join(OUT_DIR, "sample_collapsed"),
        fmt="html",
        title="Sample Schema (M:N Collapsed)",
        collapse_many_to_many=True,
    )
    print(f"Collapsed M:N diagram → {path}")


def demo_svg_output() -> None:
    """Generate a static SVG (requires Graphviz binary)."""
    print("\n=== SVG output demo ===")
    try:
        from db_schema_visualizer import render_schema

        path = render_schema(
            DB_URL,
            output=os.path.join(OUT_DIR, "sample_erd"),
            fmt="svg",
        )
        print(f"SVG diagram → {path}")
    except RuntimeError as exc:
        print(f"Skipped (Graphviz not installed): {exc}")


def demo_dot_source() -> None:
    """Print the DOT source for the schema."""
    print("\n=== DOT source demo ===")
    from db_schema_visualizer import extract_schema
    from db_schema_visualizer.graph.builder import GraphBuilder
    from db_schema_visualizer.graph.layout import graph_to_dot

    schema = extract_schema(DB_URL)
    graph = GraphBuilder().build(schema)
    dot = graph_to_dot(graph)
    print(dot[:800], "...[truncated]")


if __name__ == "__main__":
    print("Creating sample database…")
    create_sample_db()

    demo_library_api()
    demo_html_output()
    demo_collapsed_m2n()
    demo_svg_output()
    demo_dot_source()

    print("\n✓ Demo complete.  Output files are in:", OUT_DIR)
