"""
Global configuration constants for DB Schema Visualizer.

All colours, fonts, and layout defaults live here so they can be
overridden in one place without touching rendering code.
"""

from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------

VERSION = "0.1.0"
APP_NAME = "dbviz"

# ---------------------------------------------------------------------------
# Graphviz / DOT layout settings
# ---------------------------------------------------------------------------

GRAPH_DIRECTION = "LR"          # left-to-right; use "TB" for top-to-bottom
GRAPH_RANKDIR = GRAPH_DIRECTION
GRAPH_SPLINES = "ortho"         # "ortho" | "polyline" | "curved" | "line"
GRAPH_NODESEP = "0.5"           # horizontal gap between nodes (inches)
GRAPH_RANKSEP = "1.0"           # vertical gap between ranks

# ---------------------------------------------------------------------------
# Node / table styling
# ---------------------------------------------------------------------------

TABLE_FONT = "Helvetica"
TABLE_FONTSIZE = "10"

# Header background colour per schema name.  The key ``"default"`` is used
# when no schema-specific colour is found.
SCHEMA_HEADER_COLORS: Dict[str, str] = {
    "default":             "#4A90D9",   # blue
    "public":              "#4A90D9",
    "auth":                "#E67E22",   # orange
    "admin":               "#8E44AD",   # purple
    "reporting":           "#27AE60",   # green
    "dbo":                 "#2980B9",   # SQL Server default
}

HEADER_FONT_COLOR = "#FFFFFF"           # white text on coloured header
COLUMN_BG_COLOR   = "#F8F9FA"           # light grey cell background
PK_ICON           = "🔑"               # prefix for primary-key columns
FK_ICON           = "🔗"               # prefix for foreign-key columns

# ---------------------------------------------------------------------------
# Edge styling
# ---------------------------------------------------------------------------

EDGE_COLOR           = "#555555"
EDGE_FONT_COLOR      = "#333333"
EDGE_FONTSIZE        = "8"
MANY_TO_MANY_STYLE   = "dashed"        # style for collapsed M:N edges
EDGE_ARROWHEAD       = "crow"          # crow's-foot notation
EDGE_ARROWTAIL       = "none"

# ---------------------------------------------------------------------------
# Junction table styling
# ---------------------------------------------------------------------------

JUNCTION_HEADER_COLOR = "#95A5A6"       # grey – visually distinct
JUNCTION_STYLE        = "dashed"        # dashed border on junction nodes

# ---------------------------------------------------------------------------
# HTML / D3 renderer defaults
# ---------------------------------------------------------------------------

HTML_TITLE            = "DB Schema Visualizer"
D3_CDN_URL            = "https://d3js.org/d3.v7.min.js"
NODE_WIDTH            = 220             # pixels
NODE_MIN_HEIGHT       = 30             # pixels per row

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

SYSTEM_SCHEMAS = frozenset(
    {"information_schema", "pg_catalog", "pg_toast", "sys", "performance_schema"}
)

SYSTEM_TABLE_PREFIXES = ("pg_", "sql_", "sqlite_")


def get_header_color(schema: str | None) -> str:
    """Return the header background colour for a given schema name.

    Falls back to the ``"default"`` colour when no schema-specific
    mapping exists.
    """
    if schema and schema in SCHEMA_HEADER_COLORS:
        return SCHEMA_HEADER_COLORS[schema]
    return SCHEMA_HEADER_COLORS["default"]
