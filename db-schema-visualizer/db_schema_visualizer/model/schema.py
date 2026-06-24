"""
Data model classes for representing database schema metadata.

These classes are the core internal representation used throughout the tool.
They are intentionally database-agnostic – the extractor layer populates them,
and the graph/renderer layers consume them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Column:
    """Represents a single column in a database table.

    Attributes:
        name: Column name as it appears in the database.
        data_type: String representation of the column's data type.
        nullable: Whether the column accepts NULL values.
        default: Default value expression, if any.
        is_primary_key: True if this column is (part of) the primary key.
        comment: Optional column-level comment/description from the DB.
    """

    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    is_primary_key: bool = False
    comment: Optional[str] = None

    def __repr__(self) -> str:
        pk = " PK" if self.is_primary_key else ""
        return f"Column({self.name}: {self.data_type}{pk})"


@dataclass
class Relationship:
    """Represents a foreign-key relationship between two tables.

    Attributes:
        source_table: Name of the table that holds the FK column(s).
        target_table: Name of the referenced (parent) table.
        source_columns: FK column name(s) on the source side.
        target_columns: Referenced column name(s) on the target side.
        constraint_name: Name of the FK constraint (may be None for implicit).
        is_many_to_many: Resolved flag – True when this edge was produced
            by collapsing a junction table into a direct M:N edge.
    """

    source_table: str
    target_table: str
    source_columns: List[str] = field(default_factory=list)
    target_columns: List[str] = field(default_factory=list)
    constraint_name: Optional[str] = None
    is_many_to_many: bool = False

    @property
    def label(self) -> str:
        """Human-readable label suitable for diagram edges."""
        cols = ", ".join(self.source_columns)
        return f"{cols}" if cols else ""

    def __repr__(self) -> str:
        return (
            f"Relationship({self.source_table} → {self.target_table} "
            f"[{', '.join(self.source_columns)}])"
        )


@dataclass
class Table:
    """Represents a single database table (or view excluded by spec).

    Attributes:
        name: Table name.
        schema: Schema/namespace the table belongs to (e.g. ``public``).
        columns: Ordered list of columns.
        primary_key: List of column names that form the primary key.
        foreign_keys: Outgoing FK relationships from this table.
        is_junction: True when detected as a many-to-many junction table.
        comment: Optional table-level comment from the DB.
    """

    name: str
    schema: Optional[str] = None
    columns: List[Column] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    foreign_keys: List[Relationship] = field(default_factory=list)
    is_junction: bool = False
    comment: Optional[str] = None

    @property
    def qualified_name(self) -> str:
        """Return schema-qualified name, e.g. ``public.users``."""
        if self.schema:
            return f"{self.schema}.{self.name}"
        return self.name

    def get_column(self, name: str) -> Optional[Column]:
        """Look up a column by name (case-insensitive)."""
        name_lower = name.lower()
        for col in self.columns:
            if col.name.lower() == name_lower:
                return col
        return None

    def __repr__(self) -> str:
        return f"Table({self.qualified_name}, {len(self.columns)} cols)"


@dataclass
class DatabaseSchema:
    """Top-level container for a complete database schema snapshot.

    Attributes:
        tables: All tables extracted from the database.
        name: Optional logical name for the schema snapshot (e.g. DB name).
        relationships: All FK relationships across all tables (flattened).
    """

    tables: List[Table] = field(default_factory=list)
    name: Optional[str] = None

    @property
    def relationships(self) -> List[Relationship]:
        """Aggregate all FK relationships from every table."""
        rels: List[Relationship] = []
        for table in self.tables:
            rels.extend(table.foreign_keys)
        return rels

    def get_table(self, name: str, schema: Optional[str] = None) -> Optional[Table]:
        """Find a table by name and optional schema."""
        for table in self.tables:
            if table.name == name:
                if schema is None or table.schema == schema:
                    return table
        return None

    def table_names(self) -> List[str]:
        """Return a list of unqualified table names."""
        return [t.name for t in self.tables]

    def __repr__(self) -> str:
        return f"DatabaseSchema({self.name or 'unnamed'}, {len(self.tables)} tables)"
