"""Tests for GraphvizRenderer and HtmlRenderer."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from db_schema_visualizer.graph.builder import GraphBuilder
from db_schema_visualizer.model.schema import DatabaseSchema
from db_schema_visualizer.renderer.graphviz_renderer import GraphvizRenderer
from db_schema_visualizer.renderer.html_renderer import HtmlRenderer


@pytest.fixture
def sample_graph(sample_schema: DatabaseSchema):
    builder = GraphBuilder()
    return builder.build(sample_schema)


# ---------------------------------------------------------------------------
# GraphvizRenderer
# ---------------------------------------------------------------------------

class TestGraphvizRenderer:
    def test_get_dot_source_returns_string(self, sample_graph) -> None:
        renderer = GraphvizRenderer(fmt="svg")
        dot = renderer.get_dot_source(sample_graph)
        assert isinstance(dot, str)
        assert "digraph" in dot

    def test_render_svg(self, sample_graph) -> None:
        renderer = GraphvizRenderer(fmt="svg")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "test_diagram")
            try:
                path = renderer.render(sample_graph, out)
                assert os.path.exists(path), f"Expected file at {path}"
                assert path.endswith(".svg")
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                assert "<svg" in content
            except RuntimeError as exc:
                # Graphviz binary might not be installed in CI
                pytest.skip(f"Graphviz binary not available: {exc}")

    def test_render_png(self, sample_graph) -> None:
        renderer = GraphvizRenderer(fmt="png")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "test_diagram")
            try:
                path = renderer.render(sample_graph, out)
                assert os.path.exists(path)
                assert path.endswith(".png")
            except RuntimeError:
                pytest.skip("Graphviz binary not available")

    def test_render_creates_output_directory(self, sample_graph) -> None:
        renderer = GraphvizRenderer(fmt="svg")
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "sub", "nested", "diagram")
            try:
                renderer.render(sample_graph, nested)
                out_dir = os.path.join(tmpdir, "sub", "nested")
                assert os.path.exists(out_dir)
            except RuntimeError:
                pytest.skip("Graphviz binary not available")

    def test_extension_not_duplicated(self, sample_graph) -> None:
        renderer = GraphvizRenderer(fmt="svg")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "diagram.svg")  # already has extension
            try:
                path = renderer.render(sample_graph, out)
                # Should not produce diagram.svg.svg
                assert not path.endswith(".svg.svg")
            except RuntimeError:
                pytest.skip("Graphviz binary not available")


# ---------------------------------------------------------------------------
# HtmlRenderer
# ---------------------------------------------------------------------------

class TestHtmlRenderer:
    def test_render_creates_html_file(self, sample_graph) -> None:
        renderer = HtmlRenderer(title="Test Diagram")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "diagram")
            path = renderer.render(sample_graph, out)
            assert os.path.exists(path)
            assert path.endswith(".html")

    def test_html_contains_title(self, sample_graph) -> None:
        renderer = HtmlRenderer(title="My ERD Title")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.render(sample_graph, os.path.join(tmpdir, "d"))
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "My ERD Title" in content

    def test_html_contains_d3_cdn(self, sample_graph) -> None:
        renderer = HtmlRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.render(sample_graph, os.path.join(tmpdir, "d"))
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "d3js.org" in content

    def test_html_contains_graph_json(self, sample_graph) -> None:
        renderer = HtmlRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.render(sample_graph, os.path.join(tmpdir, "d"))
            with open(path, encoding="utf-8") as f:
                content = f.read()
            # The JSON should contain our table names
            assert "users" in content
            assert "orders" in content

    def test_html_extension_appended(self, sample_graph) -> None:
        renderer = HtmlRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "no_ext")
            path = renderer.render(sample_graph, out)
            assert path.endswith(".html")

    def test_html_extension_not_duplicated(self, sample_graph) -> None:
        renderer = HtmlRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "diagram.html")
            path = renderer.render(sample_graph, out)
            assert not path.endswith(".html.html")

    def test_html_is_valid_utf8(self, sample_graph) -> None:
        renderer = HtmlRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.render(sample_graph, os.path.join(tmpdir, "d"))
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert len(content) > 100  # sanity check

    def test_html_enrich_adds_header_color(self, sample_graph) -> None:
        enriched = HtmlRenderer._enrich_graph(sample_graph)
        for node in enriched["nodes"]:
            assert "header_color" in node
            assert node["header_color"].startswith("#")
