"""
Utility functions for filtering tables and schemas.

These are pure functions – they receive a list of tables and return a
filtered list, with no side-effects.
"""

from __future__ import annotations

import fnmatch
import logging
from typing import List, Optional, Set

from db_schema_visualizer.config import SYSTEM_SCHEMAS, SYSTEM_TABLE_PREFIXES
from db_schema_visualizer.model.schema import DatabaseSchema, Table

logger = logging.getLogger(__name__)


def filter_tables(
    db_schema: DatabaseSchema,
    include_schemas: Optional[List[str]] = None,
    include_tables: Optional[List[str]] = None,
    exclude_tables: Optional[List[str]] = None,
    exclude_system: bool = True,
) -> DatabaseSchema:
    """Return a new :class:`DatabaseSchema` with filtered tables.

    Filtering logic (applied in order):
    1. Remove system schemas if ``exclude_system`` is True.
    2. Keep only tables whose schema is in ``include_schemas``
       (when provided).
    3. Keep only tables whose name matches any pattern in
       ``include_tables`` (supports ``*`` wildcards).
    4. Remove tables whose name matches any pattern in
       ``exclude_tables``.

    The returned ``DatabaseSchema`` is a shallow copy – the ``Table``
    objects themselves are shared references.

    Args:
        db_schema: The source schema to filter.
        include_schemas: Whitelist of schema names.
        include_tables: Whitelist of table name patterns.
        exclude_tables: Blacklist of table name patterns.
        exclude_system: Strip tables belonging to system schemas.

    Returns:
        A new :class:`DatabaseSchema` containing only the matching tables.
    """
    tables = list(db_schema.tables)

    if exclude_system:
        tables = _remove_system_tables(tables)

    if include_schemas:
        schemas_set: Set[str] = set(include_schemas)
        tables = [t for t in tables if (t.schema or "") in schemas_set or t.schema in schemas_set]

    if include_tables:
        tables = [
            t for t in tables
            if any(fnmatch.fnmatch(t.name, pattern) for pattern in include_tables)
        ]

    if exclude_tables:
        tables = [
            t for t in tables
            if not any(fnmatch.fnmatch(t.name, pattern) for pattern in exclude_tables)
        ]

    logger.debug(
        "filter_tables: %d → %d tables after filtering",
        len(db_schema.tables),
        len(tables),
    )

    return DatabaseSchema(tables=tables, name=db_schema.name)


def _remove_system_tables(tables: List[Table]) -> List[Table]:
    """Remove tables that belong to known system schemas or have system prefixes."""
    result: List[Table] = []
    for table in tables:
        schema = (table.schema or "").lower()
        if schema in {s.lower() for s in SYSTEM_SCHEMAS}:
            logger.debug("Skipping system-schema table: %s", table.qualified_name)
            continue
        if any(table.name.lower().startswith(p) for p in SYSTEM_TABLE_PREFIXES):
            logger.debug("Skipping system-prefix table: %s", table.name)
            continue
        result.append(table)
    return result


def find_isolated_tables(db_schema: DatabaseSchema) -> List[Table]:
    """Return tables that have no FK relationships (incoming or outgoing).

    Useful for identifying orphan tables that might be unintentionally
    disconnected from the rest of the schema.

    Args:
        db_schema: The schema to analyse.

    Returns:
        List of tables with no relationships.
    """
    connected: Set[str] = set()
    for rel in db_schema.relationships:
        connected.add(rel.source_table)
        connected.add(rel.target_table)
    return [t for t in db_schema.tables if t.name not in connected]
