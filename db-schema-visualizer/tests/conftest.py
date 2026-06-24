"""
Shared pytest fixtures.

The in-memory SQLite database created here represents a small e-commerce
schema with four tables:

    users ──< orders ──< order_items >── products
                                (junction via order_items, but not a pure
                                 M:N junction here since it has extra cols)

    tags ──< product_tags >── products   ← pure M:N junction
"""

from __future__ import annotations

import pytest
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine

from db_schema_visualizer.extractor.sqlalchemy_extractor import SqlAlchemyExtractor
from db_schema_visualizer.model.schema import DatabaseSchema


@pytest.fixture(scope="session")
def sqlite_engine() -> Engine:
    """In-memory SQLite engine with a small sample schema."""
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()

    Table(
        "users",
        meta,
        Column("id", Integer, primary_key=True),
        Column("username", String(80), nullable=False),
        Column("email", String(120), nullable=False),
        Column("created_at", String(30)),
    )

    Table(
        "products",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", String(200), nullable=False),
        Column("description", Text),
        Column("price", String(20)),
    )

    Table(
        "orders",
        meta,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("status", String(30), nullable=False),
        Column("total", String(20)),
    )

    # Pure M:N junction: (product_id, tag_id) is the composite PK and
    # both columns are FKs → detected as a junction table.
    Table(
        "tags",
        meta,
        Column("id", Integer, primary_key=True),
        Column("name", String(50), nullable=False),
    )

    Table(
        "product_tags",
        meta,
        Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
        Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    )

    meta.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def sample_schema(sqlite_engine: Engine) -> DatabaseSchema:
    """Extracted DatabaseSchema from the in-memory SQLite DB."""
    extractor = SqlAlchemyExtractor(sqlite_engine)
    return extractor.extract(include_many_to_many=True)
