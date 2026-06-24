"""SQLAlchemy-based metadata extractor.

Uses ``sqlalchemy.inspect()`` (the Inspector API) to introspect any
database supported by SQLAlchemy without writing raw SQL.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Union

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect as sa_inspect

from db_schema_visualizer.extractor.base import AbstractExtractor
from db_schema_visualizer.model.schema import (
    Column,
    DatabaseSchema,
    Relationship,
    Table,
)

logger = logging.getLogger(__name__)


class SqlAlchemyExtractor(AbstractExtractor):
    """Extracts schema metadata using the SQLAlchemy Inspector API.

    Supports PostgreSQL, MySQL/MariaDB, SQLite, and SQL Server – any
    dialect that SQLAlchemy can handle.

    Example::

        from sqlalchemy import create_engine
        from db_schema_visualizer.extractor import SqlAlchemyExtractor

        engine = create_engine("sqlite:///mydb.db")
        extractor = SqlAlchemyExtractor(engine)
        schema = extractor.extract()
    """

    def __init__(self, engine_or_url: Union[Engine, str]) -> None:
        """Initialise the extractor.

        Args:
            engine_or_url: Either a pre-built SQLAlchemy :class:`Engine`
                or a connection URL string (e.g.
                ``"postgresql://user:pw@host/db"``).
        """
        if isinstance(engine_or_url, str):
            try:
                self._engine: Engine = create_engine(engine_or_url)
                logger.debug("Created engine from URL: %s", engine_or_url)
            except Exception as exc:
                raise ConnectionError(
                    f"Failed to create SQLAlchemy engine from URL: {exc}"
                ) from exc
        else:
            self._engine = engine_or_url

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        schemas: Optional[List[str]] = None,
        tables: Optional[List[str]] = None,
        include_many_to_many: bool = True,
    ) -> DatabaseSchema:
        """Extract schema metadata from the connected database.

        Args:
            schemas: Restrict extraction to these schema names.
            tables: Restrict extraction to these table names.
            include_many_to_many: Detect and annotate junction tables.

        Returns:
            Populated :class:`DatabaseSchema`.

        Raises:
            ConnectionError: If the database cannot be reached.
            RuntimeError: If extraction fails for an unexpected reason.
        """
        try:
            inspector = sa_inspect(self._engine)
        except SQLAlchemyError as exc:
            raise ConnectionError(
                f"Cannot connect to database: {exc}"
            ) from exc

        # Determine which schemas to introspect
        target_schemas = self._resolve_schemas(inspector, schemas)
        logger.info("Introspecting schemas: %s", target_schemas)

        db_name = self._get_db_name()
        all_tables: List[Table] = []

        for schema in target_schemas:
            schema_tables = self._extract_schema(
                inspector, schema, tables_filter=tables
            )
            all_tables.extend(schema_tables)

        if not all_tables:
            logger.warning("No tables found after applying filters.")

        db_schema = DatabaseSchema(tables=all_tables, name=db_name)

        if include_many_to_many:
            self._detect_junction_tables(db_schema)

        logger.info(
            "Extraction complete: %d tables, %d relationships",
            len(db_schema.tables),
            len(db_schema.relationships),
        )
        return db_schema

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_db_name(self) -> str:
        """Return the database name from the engine URL."""
        url = self._engine.url
        # url.database may be a path for SQLite
        db = url.database or ""
        return db.split("/")[-1].split("\\")[-1] or "database"

    def _resolve_schemas(
        self,
        inspector,
        requested: Optional[List[str]],
    ) -> List[Optional[str]]:
        """Return the list of schemas to introspect.

        For most databases SQLAlchemy reports schema names; SQLite
        does not support schemas so we use ``None`` as a sentinel.
        """
        try:
            available = inspector.get_schema_names()
        except Exception:
            # SQLite and some drivers don't support get_schema_names()
            available = []

        # Filter out internal/system schemas
        system_schemas = {"information_schema", "pg_catalog", "sys", "performance_schema"}
        available = [s for s in available if s not in system_schemas]

        if requested:
            # Use only schemas that actually exist in the DB
            valid = [s for s in requested if s in available]
            if not valid:
                logger.warning(
                    "None of the requested schemas %s exist. Available: %s",
                    requested,
                    available,
                )
            return valid or requested  # fall back to requested to surface error

        # Default: introspect the default schema (None) for SQLite,
        # or all non-system schemas for other databases.
        if not available:
            return [None]
        return available

    def _extract_schema(
        self,
        inspector,
        schema: Optional[str],
        tables_filter: Optional[List[str]],
    ) -> List[Table]:
        """Extract all tables from a single schema.

        Args:
            inspector: SQLAlchemy Inspector instance.
            schema: Schema name, or ``None`` for the default schema.
            tables_filter: Optional whitelist of table names.

        Returns:
            List of :class:`Table` objects.
        """
        try:
            table_names = inspector.get_table_names(schema=schema)
        except SQLAlchemyError as exc:
            logger.error("Failed to list tables for schema %s: %s", schema, exc)
            return []

        if tables_filter:
            table_names = [t for t in table_names if t in tables_filter]

        tables: List[Table] = []
        for tname in table_names:
            table = self._extract_table(inspector, tname, schema)
            if table is not None:
                tables.append(table)

        return tables

    def _extract_table(
        self,
        inspector,
        table_name: str,
        schema: Optional[str],
    ) -> Optional[Table]:
        """Extract metadata for a single table.

        Args:
            inspector: SQLAlchemy Inspector.
            table_name: Unqualified table name.
            schema: Schema the table belongs to.

        Returns:
            Populated :class:`Table` or ``None`` on error.
        """
        try:
            raw_cols = inspector.get_columns(table_name, schema=schema)
            pk_info = inspector.get_pk_constraint(table_name, schema=schema)
            fk_list = inspector.get_foreign_keys(table_name, schema=schema)

            # Table-level comment (not all drivers support this)
            try:
                tbl_comment = inspector.get_table_comment(table_name, schema=schema)
                comment_text = tbl_comment.get("text")
            except Exception:
                comment_text = None

        except SQLAlchemyError as exc:
            logger.error("Failed to extract table %s: %s", table_name, exc)
            return None

        pk_cols: List[str] = pk_info.get("constrained_columns", []) if pk_info else []

        columns: List[Column] = []
        for raw in raw_cols:
            col_name = raw["name"]
            # data_type may be a SQLAlchemy type object; stringify it
            data_type = str(raw.get("type", "UNKNOWN"))
            nullable = bool(raw.get("nullable", True))
            default = raw.get("default")
            if default is not None:
                default = str(default)
            col_comment = raw.get("comment")

            columns.append(
                Column(
                    name=col_name,
                    data_type=data_type,
                    nullable=nullable,
                    default=default,
                    is_primary_key=col_name in pk_cols,
                    comment=col_comment,
                )
            )

        # Build outgoing FK relationships
        relationships: List[Relationship] = []
        for fk in fk_list:
            referred_table = fk.get("referred_table", "")
            # referred_schema may differ from current schema
            referred_schema = fk.get("referred_schema") or schema

            # Normalise: use just the table name for the target
            # (qualified name resolution happens in the builder)
            rel = Relationship(
                source_table=table_name,
                target_table=referred_table,
                source_columns=list(fk.get("constrained_columns", [])),
                target_columns=list(fk.get("referred_columns", [])),
                constraint_name=fk.get("name"),
            )
            relationships.append(rel)

        return Table(
            name=table_name,
            schema=schema,
            columns=columns,
            primary_key=pk_cols,
            foreign_keys=relationships,
            comment=comment_text,
        )

    @staticmethod
    def _detect_junction_tables(db_schema: DatabaseSchema) -> None:
        """Mark tables that act as many-to-many junction tables.

        A table is classified as a junction table when **all** of the
        following conditions hold:

        1. It has exactly two foreign keys.
        2. The columns that make up those two foreign keys collectively
           form the entire primary key of the table (i.e. there are no
           extra PK columns beyond the FK columns).

        When a junction table is detected:
        - ``table.is_junction`` is set to ``True``.
        - The two FK relationships on the junction table are each
          annotated with ``is_many_to_many = True``.

        This detection is intentionally conservative (matches the PRD
        constraint: "exactly two FKs that form the primary key").
        """
        for table in db_schema.tables:
            if len(table.foreign_keys) != 2:
                continue

            fk1, fk2 = table.foreign_keys
            fk_cols = set(fk1.source_columns + fk2.source_columns)
            pk_cols = set(table.primary_key)

            # Junction: all PK columns are FK columns and vice-versa
            if fk_cols and pk_cols and fk_cols == pk_cols:
                table.is_junction = True
                fk1.is_many_to_many = True
                fk2.is_many_to_many = True
                logger.debug("Detected junction table: %s", table.name)
