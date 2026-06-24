"""Tests for SqlAlchemyExtractor."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from db_schema_visualizer.extractor.sqlalchemy_extractor import SqlAlchemyExtractor
from db_schema_visualizer.model.schema import DatabaseSchema


class TestExtractorBasic:
    """Basic extraction correctness."""

    def test_returns_database_schema(self, sample_schema: DatabaseSchema) -> None:
        assert isinstance(sample_schema, DatabaseSchema)

    def test_correct_table_count(self, sample_schema: DatabaseSchema) -> None:
        table_names = {t.name for t in sample_schema.tables}
        expected = {"users", "products", "orders", "tags", "product_tags"}
        assert expected.issubset(table_names), (
            f"Missing tables: {expected - table_names}"
        )

    def test_users_columns(self, sample_schema: DatabaseSchema) -> None:
        users = sample_schema.get_table("users")
        assert users is not None
        col_names = {c.name for c in users.columns}
        assert {"id", "username", "email"}.issubset(col_names)

    def test_primary_key_detected(self, sample_schema: DatabaseSchema) -> None:
        users = sample_schema.get_table("users")
        assert "id" in users.primary_key

    def test_pk_column_flagged(self, sample_schema: DatabaseSchema) -> None:
        users = sample_schema.get_table("users")
        id_col = users.get_column("id")
        assert id_col is not None
        assert id_col.is_primary_key is True

    def test_non_pk_column_not_flagged(self, sample_schema: DatabaseSchema) -> None:
        users = sample_schema.get_table("users")
        email_col = users.get_column("email")
        assert email_col is not None
        assert email_col.is_primary_key is False

    def test_foreign_key_on_orders(self, sample_schema: DatabaseSchema) -> None:
        orders = sample_schema.get_table("orders")
        assert orders is not None
        fk_targets = {rel.target_table for rel in orders.foreign_keys}
        assert "users" in fk_targets

    def test_relationships_flattened(self, sample_schema: DatabaseSchema) -> None:
        rels = sample_schema.relationships
        assert len(rels) > 0

    def test_column_nullable_attribute(self, sample_schema: DatabaseSchema) -> None:
        orders = sample_schema.get_table("orders")
        user_id_col = orders.get_column("user_id")
        assert user_id_col is not None
        assert user_id_col.nullable is False


class TestJunctionDetection:
    """Many-to-many junction table detection."""

    def test_product_tags_is_junction(self, sample_schema: DatabaseSchema) -> None:
        pt = sample_schema.get_table("product_tags")
        assert pt is not None
        assert pt.is_junction is True, (
            "product_tags should be detected as a junction table "
            f"(pk={pt.primary_key}, fks={pt.foreign_keys})"
        )

    def test_orders_is_not_junction(self, sample_schema: DatabaseSchema) -> None:
        orders = sample_schema.get_table("orders")
        # orders has only one FK and extra columns → not a junction
        assert orders.is_junction is False

    def test_junction_fks_annotated(self, sample_schema: DatabaseSchema) -> None:
        pt = sample_schema.get_table("product_tags")
        assert all(rel.is_many_to_many for rel in pt.foreign_keys)


class TestExtractorFilters:
    """Table and schema filters."""

    def test_filter_by_table_name(self, sqlite_engine) -> None:
        extractor = SqlAlchemyExtractor(sqlite_engine)
        schema = extractor.extract(tables=["users", "orders"])
        names = {t.name for t in schema.tables}
        assert names == {"users", "orders"}

    def test_empty_filter_returns_nothing(self, sqlite_engine) -> None:
        extractor = SqlAlchemyExtractor(sqlite_engine)
        schema = extractor.extract(tables=["nonexistent_table"])
        assert len(schema.tables) == 0

    def test_no_many_to_many_flag(self, sqlite_engine) -> None:
        extractor = SqlAlchemyExtractor(sqlite_engine)
        schema = extractor.extract(include_many_to_many=False)
        pt = schema.get_table("product_tags")
        if pt:
            assert pt.is_junction is False


class TestExtractorErrorHandling:
    """Error handling for bad inputs."""

    def test_bad_url_raises_connection_error(self) -> None:
        with pytest.raises((ConnectionError, Exception)):
            extractor = SqlAlchemyExtractor("postgresql://bad:bad@localhost:9999/nope")
            extractor.extract()

    def test_accepts_url_string(self) -> None:
        extractor = SqlAlchemyExtractor("sqlite:///:memory:")
        schema = extractor.extract()
        assert isinstance(schema, DatabaseSchema)
