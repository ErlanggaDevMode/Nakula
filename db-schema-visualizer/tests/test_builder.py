"""Tests for GraphBuilder."""

from __future__ import annotations

import pytest

from db_schema_visualizer.graph.builder import GraphBuilder
from db_schema_visualizer.graph.layout import graph_to_dot
from db_schema_visualizer.model.schema import DatabaseSchema


class TestGraphBuilderBasic:
    """Basic graph construction."""

    def test_nodes_created_for_each_table(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        node_ids = {n["id"] for n in graph["nodes"]}
        table_names = {t.name for t in sample_schema.tables}
        assert table_names == node_ids

    def test_edges_created_for_fks(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        assert len(graph["edges"]) > 0

    def test_orders_to_users_edge_present(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        edges = {(e["source"], e["target"]) for e in graph["edges"]}
        assert ("orders", "users") in edges

    def test_graph_has_name(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        assert "name" in graph
        assert isinstance(graph["name"], str)

    def test_node_has_expected_keys(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        node = graph["nodes"][0]
        for key in ("id", "label", "schema", "columns", "primary_key", "is_junction"):
            assert key in node, f"Missing key '{key}' in node"

    def test_edge_has_expected_keys(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        edge = graph["edges"][0]
        for key in ("source", "target", "source_columns", "target_columns", "is_many_to_many"):
            assert key in edge, f"Missing key '{key}' in edge"

    def test_columns_in_node(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        users_node = next(n for n in graph["nodes"] if n["id"] == "users")
        col_names = {c["name"] for c in users_node["columns"]}
        assert "id" in col_names
        assert "username" in col_names


class TestCollapseM2N:
    """Many-to-many collapse behaviour."""

    def test_junction_node_removed_when_collapsed(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder(collapse_many_to_many=True)
        graph = builder.build(sample_schema)
        node_ids = {n["id"] for n in graph["nodes"]}
        assert "product_tags" not in node_ids, (
            "Junction table should be removed when collapse_many_to_many=True"
        )

    def test_m2n_edge_added_when_collapsed(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder(collapse_many_to_many=True)
        graph = builder.build(sample_schema)
        m2n_edges = [e for e in graph["edges"] if e["is_many_to_many"]]
        assert len(m2n_edges) > 0, "Expected at least one M:N edge"

    def test_junction_node_present_without_collapse(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder(collapse_many_to_many=False)
        graph = builder.build(sample_schema)
        node_ids = {n["id"] for n in graph["nodes"]}
        assert "product_tags" in node_ids


class TestDotOutput:
    """DOT language generation."""

    def test_dot_is_string(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        dot = graph_to_dot(graph)
        assert isinstance(dot, str)
        assert len(dot) > 0

    def test_dot_contains_digraph(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        dot = graph_to_dot(graph)
        assert "digraph" in dot

    def test_dot_contains_table_names(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        dot = graph_to_dot(graph)
        assert "users" in dot
        assert "orders" in dot

    def test_dot_direction_tb(self, sample_schema: DatabaseSchema) -> None:
        builder = GraphBuilder()
        graph = builder.build(sample_schema)
        dot = graph_to_dot(graph, direction="TB")
        assert "rankdir=TB" in dot
