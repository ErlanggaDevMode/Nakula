"""
Layout helpers for converting a graph dict to DOT source.

This module is responsible only for *layout computation* (turning the
abstract graph into a DOT string).  Actual rendering is done by the
renderer layer.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from db_schema_visualizer import config
from db_schema_visualizer.graph.builder import GraphDict

logger = logging.getLogger(__name__)


def graph_to_dot(graph: GraphDict, direction: str = "LR") -> str:
    """Convert a :class:`GraphDict` to a DOT language string.

    The generated DOT uses HTML-like labels so that each table node
    renders as a proper table with coloured header and column rows.

    Args:
        graph: Abstract graph dict produced by :class:`GraphBuilder`.
        direction: Rank direction – ``"LR"`` (left-right, default) or
            ``"TB"`` (top-bottom).

    Returns:
        A DOT-language string ready to pass to Graphviz.
    """
    lines: List[str] = []
    lines.append(f'digraph "{graph["name"]}" {{')
    lines.append(f'    rankdir={direction};')
    lines.append(f'    splines={config.GRAPH_SPLINES};')
    lines.append(f'    nodesep={config.GRAPH_NODESEP};')
    lines.append(f'    ranksep={config.GRAPH_RANKSEP};')
    lines.append('    node [shape=none, margin=0, fontname="Helvetica", fontsize=10];')
    lines.append('    edge [fontname="Helvetica", fontsize=8, color="#555555", '
                 'fontcolor="#333333"];')
    lines.append("")

    for node in graph["nodes"]:
        lines.append(_node_to_dot(node))

    lines.append("")

    for edge in graph["edges"]:
        lines.append(_edge_to_dot(edge))

    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _node_to_dot(node: Dict[str, Any]) -> str:
    """Render a single node as a DOT HTML-label record."""
    schema = node.get("schema")
    is_junction = node.get("is_junction", False)

    header_color = (
        config.JUNCTION_HEADER_COLOR
        if is_junction
        else config.get_header_color(schema)
    )
    border_style = ' style="dashed"' if is_junction else ""
    pk_set = set(node.get("primary_key", []))
    # Build the FK column set from edges (not available here, so we rely on column metadata)

    # HTML-like label (Graphviz supports a subset of HTML inside <>)
    rows: List[str] = []

    # Header row
    rows.append(
        f'<TR><TD BGCOLOR="{header_color}" ALIGN="LEFT" '
        f'COLSPAN="2"><FONT COLOR="{config.HEADER_FONT_COLOR}" '
        f'POINT-SIZE="11"><B>{_esc(node["label"])}</B></FONT></TD></TR>'
    )

    # Column rows
    for col in node["columns"]:
        cname = col["name"]
        ctype = col["data_type"]
        icon = ""
        bold_open = bold_close = ""
        if col["is_primary_key"]:
            icon = "🔑 "
            bold_open, bold_close = "<B>", "</B>"

        row = (
            f'<TR><TD BGCOLOR="{config.COLUMN_BG_COLOR}" ALIGN="LEFT" PORT="{_esc(cname)}">'
            f'{bold_open}{icon}{_esc(cname)}{bold_close}</TD>'
            f'<TD BGCOLOR="{config.COLUMN_BG_COLOR}" ALIGN="LEFT">'
            f'<FONT COLOR="#666666">{_esc(ctype)}</FONT></TD></TR>'
        )
        rows.append(row)

    table_html = (
        f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4"{border_style}>'
        + "".join(rows)
        + "</TABLE>>"
    )

    safe_id = _dot_id(node["id"])
    return f'    {safe_id} [label={table_html}];'


def _edge_to_dot(edge: Dict[str, Any]) -> str:
    """Render a single edge as a DOT arrow statement."""
    src = _dot_id(edge["source"])
    tgt = _dot_id(edge["target"])

    attrs: List[str] = []

    if edge.get("is_many_to_many"):
        attrs += [
            f'style="{config.MANY_TO_MANY_STYLE}"',
            'arrowhead="crow"',
            'arrowtail="crow"',
            'dir="both"',
        ]
    else:
        attrs += [
            f'arrowhead="{config.EDGE_ARROWHEAD}"',
            f'arrowtail="{config.EDGE_ARROWTAIL}"',
            'dir="forward"',
        ]

    label = edge.get("label", "")
    if label:
        attrs.append(f'label="{_esc(label)}"')

    attr_str = ", ".join(attrs)
    return f'    {src} -> {tgt} [{attr_str}];'


def _esc(text: str) -> str:
    """Escape characters that would break HTML-label DOT strings."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _dot_id(name: str) -> str:
    """Return a safe DOT node identifier (quoted string)."""
    return f'"{name}"'
