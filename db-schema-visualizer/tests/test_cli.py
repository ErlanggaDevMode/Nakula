"""Tests for the Click CLI."""

from __future__ import annotations

import os
import tempfile

import pytest
from click.testing import CliRunner

from db_schema_visualizer.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sqlite_url(tmp_path):
    """Create a temporary SQLite file DB and return its URL."""
    from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    meta = MetaData()
    Table("authors", meta, Column("id", Integer, primary_key=True), Column("name", String(100)))
    Table(
        "books",
        meta,
        Column("id", Integer, primary_key=True),
        Column("author_id", Integer, ForeignKey("authors.id")),
        Column("title", String(200)),
    )
    meta.create_all(engine)
    engine.dispose()
    return f"sqlite:///{db_path}"


class TestExtractCommandHtml:
    def test_extract_html_basic(self, runner, sqlite_url, tmp_path) -> None:
        out = str(tmp_path / "erd")
        result = runner.invoke(cli, ["extract", "-d", sqlite_url, "-o", out, "-f", "html"])
        assert result.exit_code == 0, result.output
        assert os.path.exists(out + ".html")

    def test_extract_html_contains_table_names(self, runner, sqlite_url, tmp_path) -> None:
        out = str(tmp_path / "erd")
        runner.invoke(cli, ["extract", "-d", sqlite_url, "-o", out, "-f", "html"])
        with open(out + ".html", encoding="utf-8") as f:
            content = f.read()
        assert "authors" in content
        assert "books" in content

    def test_extract_with_table_filter(self, runner, sqlite_url, tmp_path) -> None:
        out = str(tmp_path / "erd")
        result = runner.invoke(
            cli,
            ["extract", "-d", sqlite_url, "-o", out, "-f", "html", "--tables", "authors"],
        )
        assert result.exit_code == 0, result.output
        with open(out + ".html", encoding="utf-8") as f:
            content = f.read()
        assert "authors" in content
        # books should not appear in the JSON data
        # (it may appear in surrounding text, so we check the node data)
        # A simple proxy: if filtered correctly, "books" won't be a node label
        import json, re
        m = re.search(r"const GRAPH_DATA = ({.*?});", content, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            node_ids = {n["id"] for n in data["nodes"]}
            assert "books" not in node_ids

    def test_extract_no_many_to_many_flag(self, runner, sqlite_url, tmp_path) -> None:
        out = str(tmp_path / "erd")
        result = runner.invoke(
            cli,
            ["extract", "-d", sqlite_url, "-o", out, "-f", "html", "--no-many-to-many"],
        )
        assert result.exit_code == 0, result.output


class TestExtractCommandStatic:
    def test_extract_svg(self, runner, sqlite_url, tmp_path) -> None:
        out = str(tmp_path / "erd")
        result = runner.invoke(cli, ["extract", "-d", sqlite_url, "-o", out, "-f", "svg"])
        if result.exit_code != 0 and "Graphviz" in result.output:
            pytest.skip("Graphviz binary not available")
        assert result.exit_code == 0, result.output

    def test_extract_png(self, runner, sqlite_url, tmp_path) -> None:
        out = str(tmp_path / "erd")
        result = runner.invoke(cli, ["extract", "-d", sqlite_url, "-o", out, "-f", "png"])
        if result.exit_code != 0 and "Graphviz" in result.output:
            pytest.skip("Graphviz binary not available")
        assert result.exit_code == 0, result.output


class TestDotCommand:
    def test_dot_outputs_digraph(self, runner, sqlite_url) -> None:
        result = runner.invoke(cli, ["dot", "-d", sqlite_url])
        assert result.exit_code == 0, result.output
        assert "digraph" in result.output

    def test_dot_contains_table_names(self, runner, sqlite_url) -> None:
        result = runner.invoke(cli, ["dot", "-d", sqlite_url])
        assert "authors" in result.output
        assert "books" in result.output


class TestListTablesCommand:
    def test_list_tables(self, runner, sqlite_url) -> None:
        result = runner.invoke(cli, ["list-tables", "-d", sqlite_url])
        assert result.exit_code == 0, result.output
        assert "authors" in result.output
        assert "books" in result.output

    def test_list_tables_shows_total(self, runner, sqlite_url) -> None:
        result = runner.invoke(cli, ["list-tables", "-d", sqlite_url])
        assert "Total:" in result.output


class TestVersionCommand:
    def test_version(self, runner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestErrorHandling:
    def test_bad_db_url_exits_with_error(self, runner, tmp_path) -> None:
        out = str(tmp_path / "erd")
        result = runner.invoke(
            cli,
            ["extract", "-d", "postgresql://bad:bad@localhost:19999/nope",
             "-o", out, "-f", "html"],
        )
        # Should exit non-zero
        assert result.exit_code != 0
