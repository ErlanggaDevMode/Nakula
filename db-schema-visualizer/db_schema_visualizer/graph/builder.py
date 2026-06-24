"""
Graph builder – converts a DatabaseSchema into an abstract node/edge dict
that is database-agnostic and renderer-agnostic.

The output is a plain Python dict so it can be consumed by any renderer
without coupling to NetworkX or Graphviz data structures.

Structure of the returned graph dict::

    {
        "name": str,
        "nodes": [
            {
                "id": str,           # unique node identifier (table name)
                "label": str,        # display name
                "schema": str|None,
                "columns": [...],    # list of column dicts
                "primary_key": [...],
                "is_junction": bool,
            },
            ...
        ],
        "edges": [
            {
                "source": str,       # source node id
                "target": str,       # target node id
                "source_columns": [...],
                "target_columns": [...],
                "constraint_name": str|None,
                "is_many_to_many": bool,
                "label": str,
            },
            ...
        ],
    }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from db_schema_visualizer.model.schema import DatabaseSchema, Relationship, Table

logger = logging.getLogger(__name__)

# Type alias for the graph dict
GraphDict = Dict[str, Any]


class GraphBuilder:
    """Transforms a :class:`DatabaseSchema` into an abstract graph dict.

    Optionally collapses junction tables into direct many-to-many edges
    when ``collapse_many_to_many`` is ``True``.

    Example::

        builder = GraphBuilder(collapse_many_to_many=True)
        graph = builder.build(db_schema)
    """

    def __init__(self, collapse_many_to_many: bool = False) -> None:
        """Initialise the builder.

        Args:
            collapse_many_to_many: When ``True`` and a junction table is
                detected, replace the two FK edges with a single
                many-to-many edge between the two referenced tables,
                and omit the junction table node from the graph.
        """
        self.collapse_many_to_many = collapse_many_to_many

    def build(self, db_schema: DatabaseSchema) -> GraphDict:
        """Build and return the graph dict.

        Args:
            db_schema: Populated schema from the extractor.

        Returns:
            A ``GraphDict`` containing ``nodes`` and ``edges`` lists.
        """
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # Tables to skip when collapsing M:N
        skipped_tables: set = set()

        if self.collapse_many_to_many:
            skipped_tables, extra_edges = self._build_many_to_many_edges(db_schema)
            edges.extend(extra_edges)

        for table in db_schema.tables:
            if table.name in skipped_tables:
                continue
            nodes.append(self._table_to_node(table))

            for rel in table.foreign_keys:
                # Skip FK edges that belong to a collapsed junction table
                if table.name in skipped_tables:
                    continue
                # Skip the individual FK edges of a M:N junction when collapsing
                if self.collapse_many_to_many and rel.is_many_to_many:
                    continue
                edges.append(self._rel_to_edge(rel))

        graph: GraphDict = {
            "name": db_schema.name or "schema",
            "nodes": nodes,
            "edges": edges,
        }

        logger.debug(
            "Built graph: %d nodes, %d edges", len(nodes), len(edges)
        )
        return graph

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _table_to_node(table: Table) -> Dict[str, Any]:
        """Convert a :class:`Table` into a node dict."""
        columns = [
            {
                "name": col.name,
                "data_type": col.data_type,
                "nullable": col.nullable,
                "default": col.default,
                "is_primary_key": col.is_primary_key,
                "comment": col.comment,
            }
            for col in table.columns
        ]
        return {
            "id": table.name,
            "label": table.name,
            "schema": table.schema,
            "qualified_name": table.qualified_name,
            "columns": columns,
            "primary_key": table.primary_key,
            "is_junction": table.is_junction,
            "comment": table.comment,
        }

    @staticmethod
    def _rel_to_edge(rel: Relationship) -> Dict[str, Any]:
        """Convert a :class:`Relationship` into an edge dict."""
        return {
            "source": rel.source_table,
            "target": rel.target_table,
            "source_columns": rel.source_columns,
            "target_columns": rel.target_columns,
            "constraint_name": rel.constraint_name,
            "is_many_to_many": rel.is_many_to_many,
            "label": rel.label,
        }

    @staticmethod
    def _build_many_to_many_edges(
        db_schema: DatabaseSchema,
    ) -> tuple[set, List[Dict[str, Any]]]:
        """Detect junction tables and build collapsed M:N edges.

        Returns:
            A tuple of (set of junction table names to skip, list of
            new M:N edge dicts to add to the graph).
        """
        skipped: set = set()
        new_edges: List[Dict[str, Any]] = []

        for table in db_schema.tables:
            if not table.is_junction:
                continue

            fk1, fk2 = table.foreign_keys[0], table.foreign_keys[1]
            new_edges.append(
                {
                    "source": fk1.target_table,
                    "target": fk2.target_table,
                    "source_columns": [],
                    "target_columns": [],
                    "constraint_name": None,
                    "is_many_to_many": True,
                    # Label shows the junction table name for traceability
                    "label": f"M:N via {table.name}",
                }
            )
            skipped.add(table.name)
            logger.debug(
                "Collapsed junction table %s → %s ↔ %s",
                table.name,
                fk1.target_table,
                fk2.target_table,
            )

        return skipped, new_edges
