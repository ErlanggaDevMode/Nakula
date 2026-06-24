# DB Schema Visualizer

Generate Entity-Relationship Diagrams (ERDs) from any relational database supported by SQLAlchemy — in static (PNG/SVG/PDF) or interactive (HTML) formats.

```
dbviz extract -d sqlite:///mydb.db -o diagram -f html
```

---

## Features

- **Multi-database**: PostgreSQL, MySQL, SQLite, SQL Server via SQLAlchemy
- **Automatic extraction**: tables, columns (type, nullable, default), primary keys, foreign keys
- **M:N detection**: identifies junction tables; optionally collapses them to direct edges
- **Static output**: PNG, SVG, PDF via Graphviz
- **Interactive HTML**: drag nodes, zoom, pan, search — single self-contained file
- **Crow's foot notation** on FK edges
- **Schema header colours** per database schema
- **Library API**: importable as a Python module

---

## Installation

### From source

```bash
git clone https://github.com/example/db-schema-visualizer
cd db-schema-visualizer
pip install -e .
```

### From PyPI (once published)

```bash
pip install db-schema-visualizer
```

### Optional database drivers

```bash
pip install db-schema-visualizer[postgres]   # psycopg2-binary
pip install db-schema-visualizer[mysql]      # pymysql
pip install db-schema-visualizer[mssql]      # pyodbc
```

### Graphviz binary (for PNG/SVG/PDF output)

The `graphviz` Python package bundles binaries on most platforms. If you get
`ExecutableNotFound`, install the system package:

```bash
# macOS
brew install graphviz

# Ubuntu / Debian
sudo apt-get install graphviz

# Windows (via Chocolatey)
choco install graphviz
```

---

## Quick Start (3 steps)

```bash
# 1. Create the sample database
python examples/create_sample_db.py

# 2. Generate an interactive HTML diagram
dbviz extract -d sqlite:///examples/sample.db -o erd -f html

# 3. Open in browser
start erd.html        # Windows
open  erd.html        # macOS
xdg-open erd.html     # Linux
```

---

## CLI Reference

### `dbviz extract`

```
Usage: dbviz extract [OPTIONS]

  Extract schema metadata and generate an ERD diagram.

Options:
  -d, --db URL               SQLAlchemy connection URL  [required]
  -o, --output PATH          Output file path           [required]
  -f, --format [png|svg|pdf|html]
                             Output format              [default: png]
  --schema SCHEMA            Restrict to schema (repeatable)
  --tables TABLE             Include only these tables (repeatable, * wildcards)
  --exclude-tables PATTERN   Exclude tables matching pattern (repeatable)
  --no-many-to-many          Disable M:N junction detection
  --collapse-m2n             Replace junction tables with direct M:N edges
  --direction [LR|TB]        Graph direction: LR or TB  [default: LR]
  --title TEXT               Custom title for HTML output
  -v, --verbose              Enable debug logging
  --help                     Show this message and exit.
```

### `dbviz dot`

Print the DOT source to stdout (useful for debugging or piping to `dot`):

```bash
dbviz dot -d sqlite:///examples/sample.db | dot -Tsvg -o out.svg
```

### `dbviz list-tables`

List all discovered tables:

```bash
dbviz list-tables -d postgresql://user:pw@localhost/mydb
```

---

## Example Commands

```bash
# SQLite → HTML (interactive, with M:N collapsed)
dbviz extract -d sqlite:///mydb.db -o erd -f html --collapse-m2n

# PostgreSQL → SVG, public schema only
dbviz extract \
  -d postgresql://alice:secret@db.host/myapp \
  -o docs/schema.svg \
  -f svg \
  --schema public

# MySQL → PNG, filter specific tables
dbviz extract \
  -d mysql+pymysql://user:pw@host/shop \
  -o shop_erd.png \
  -f png \
  --tables users --tables orders --tables products

# Exclude migration/system tables
dbviz extract \
  -d sqlite:///mydb.db \
  -o erd -f html \
  --exclude-tables "alembic_*" \
  --exclude-tables "django_*"

# Top-to-bottom layout
dbviz extract -d sqlite:///mydb.db -o erd -f svg --direction TB
```

---

## Library API

```python
from db_schema_visualizer import extract_schema, render_schema

# --- Extract only ---
schema = extract_schema("sqlite:///mydb.db")
for table in schema.tables:
    print(table.name, [c.name for c in table.columns])

# --- Render in one call ---
path = render_schema(
    "sqlite:///mydb.db",
    output="erd",
    fmt="html",
    title="My Schema",
)
print(f"Diagram at: {path}")

# --- Fine-grained control ---
from sqlalchemy import create_engine
from db_schema_visualizer.extractor import SqlAlchemyExtractor
from db_schema_visualizer.graph.builder import GraphBuilder
from db_schema_visualizer.renderer import HtmlRenderer

engine = create_engine("postgresql://user:pw@host/db")
extractor = SqlAlchemyExtractor(engine)
db_schema = extractor.extract(schemas=["public"], include_many_to_many=True)

graph = GraphBuilder(collapse_many_to_many=True).build(db_schema)
renderer = HtmlRenderer(title="Production DB")
renderer.render(graph, "prod_erd.html")
```

---

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# With coverage report
pytest --cov=db_schema_visualizer --cov-report=term-missing
```

> **Note**: Tests that require a Graphviz binary are automatically skipped
> when the binary is not installed.

---

## Project Structure

```
db-schema-visualizer/
├── db_schema_visualizer/
│   ├── __init__.py            # extract_schema(), render_schema()
│   ├── cli.py                 # Click CLI (dbviz)
│   ├── config.py              # colours, fonts, constants
│   ├── model/schema.py        # Table, Column, Relationship, DatabaseSchema
│   ├── extractor/             # SQLAlchemy Inspector-based extractor
│   ├── graph/                 # GraphBuilder + DOT layout
│   ├── renderer/
│   │   ├── graphviz_renderer.py
│   │   ├── html_renderer.py
│   │   └── templates/interactive.html
│   └── utils/filters.py
├── tests/
├── examples/
│   ├── create_sample_db.py    # generates examples/sample.db
│   └── run_demo.py            # end-to-end demo
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE).
