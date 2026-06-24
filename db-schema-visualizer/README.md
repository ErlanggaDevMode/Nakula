# DB Schema Visualizer

Generate Entity-Relationship Diagrams (ERDs) from any relational database supported by SQLAlchemy — as static images (PNG/SVG/PDF) or an interactive, self-contained HTML file.

```bash
dbviz extract -d sqlite:///mydb.db -o erd.html
```

---

## Features

- **Multi-database** — PostgreSQL, MySQL, SQLite, SQL Server via SQLAlchemy
- **Automatic extraction** — tables, columns (type, nullable, default), primary keys, foreign keys
- **M:N detection** — identifies junction tables; optionally collapses them to direct edges
- **Static output** — PNG, SVG, PDF via Graphviz
- **Interactive HTML** — drag nodes, zoom, pan, search tables — single self-contained file, no server needed
- **Crow's foot notation** on FK edges
- **Schema header colours** — distinct colour per database schema
- **Format inference** — output format detected from file extension, no `-f` flag needed
- **Library API** — importable as a Python module

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
pip install db-schema-visualizer[postgres]   # PostgreSQL  (psycopg2-binary)
pip install db-schema-visualizer[mysql]      # MySQL/MariaDB (pymysql)
pip install db-schema-visualizer[mssql]      # SQL Server  (pyodbc)
```

### Graphviz binary (PNG/SVG/PDF only)

HTML output works out of the box. For static image output, install the Graphviz system package:

```bash
# macOS
brew install graphviz

# Ubuntu / Debian
sudo apt-get install graphviz

# Windows (Chocolatey)
choco install graphviz
```

---

## Quick Start

```bash
# 1. Create the sample database
python examples/create_sample_db.py

# 2. Interactive HTML diagram
dbviz extract -d sqlite:///examples/sample.db -o erd.html

# 3. Open in your browser
start erd.html       # Windows
open  erd.html       # macOS
xdg-open erd.html    # Linux
```

---

## CLI Reference

### `dbviz extract`

The main command. Only `-d` is required.

```
Usage: dbviz extract [OPTIONS]

Options:
  -d, --db URL                SQLAlchemy connection URL  [required]
  -o, --output PATH           Output file path  [default: erd]
                              Format is inferred from the extension:
                                erd.html → HTML
                                erd.svg  → SVG
                                erd.png  → PNG  (default when no extension)
  -f, --format [png|svg|pdf|html]
                              Override the inferred format explicitly
  --schema SCHEMA             Restrict to this schema (repeatable)
  --tables TABLE              Include only these tables (repeatable, * wildcards ok)
  --exclude-tables PATTERN    Exclude tables matching pattern (repeatable, * wildcards ok)
  --no-many-to-many           Disable M:N junction table detection
  --collapse-m2n              Replace junction tables with a direct M:N edge
  --direction [LR|TB]         Layout direction: LR = left→right, TB = top→bottom  [default: LR]
  --title TEXT                Custom page title (HTML output only)
  -v, --verbose               Enable debug logging
  --help                      Show this message and exit.
```

### `dbviz dot`

Print the raw Graphviz DOT source to stdout. Useful for debugging or piping to other tools.

```bash
dbviz dot -d sqlite:///mydb.db

# Pipe directly to the dot binary
dbviz dot -d sqlite:///mydb.db | dot -Tsvg -o out.svg
```

Options: `-d`, `--schema`, `--tables`, `--no-many-to-many`, `--direction`, `-v`

### `dbviz list-tables`

List every table the extractor can see, with junction-table annotations.

```bash
dbviz list-tables -d postgresql://user:pw@localhost/mydb
```

Options: `-d`, `--schema`, `-v`

---

## Examples

```bash
# Minimal — just the URL, outputs erd.png
dbviz extract -d sqlite:///mydb.db

# Format inferred from extension, no -f needed
dbviz extract -d sqlite:///mydb.db -o erd.html
dbviz extract -d sqlite:///mydb.db -o erd.svg
dbviz extract -d sqlite:///mydb.db -o erd.pdf

# PostgreSQL, public schema only
dbviz extract -d postgresql://alice:secret@db.host/myapp -o schema.html --schema public

# Collapse M:N junction tables into direct edges
dbviz extract -d sqlite:///mydb.db -o erd.html --collapse-m2n

# Include only specific tables
dbviz extract -d sqlite:///mydb.db -o erd.html --tables users --tables orders --tables products

# Exclude migration/scaffolding tables (wildcards supported)
dbviz extract -d sqlite:///mydb.db -o erd.html --exclude-tables "alembic_*" --exclude-tables "django_*"

# Top-to-bottom layout
dbviz extract -d sqlite:///mydb.db -o erd.svg --direction TB

# Override format explicitly (output has no extension)
dbviz extract -d sqlite:///mydb.db -o /tmp/report -f html
```

---

## Library API

```python
from db_schema_visualizer import extract_schema, render_schema

# Extract the schema model
schema = extract_schema("sqlite:///mydb.db")
for table in schema.tables:
    print(table.name, [c.name for c in table.columns])

# Render in one call — fmt inferred from output extension
path = render_schema("sqlite:///mydb.db", output="erd.html")
print(f"Diagram at: {path}")

# With options
path = render_schema(
    "sqlite:///mydb.db",
    output="erd.html",
    title="My Schema",
    collapse_many_to_many=True,
    schemas=["public"],
)
```

Fine-grained control using the individual layers:

```python
from sqlalchemy import create_engine
from db_schema_visualizer.extractor import SqlAlchemyExtractor
from db_schema_visualizer.graph.builder import GraphBuilder
from db_schema_visualizer.renderer import HtmlRenderer, GraphvizRenderer

engine = create_engine("postgresql://user:pw@host/db")

# Extract
db_schema = SqlAlchemyExtractor(engine).extract(
    schemas=["public"],
    include_many_to_many=True,
)

# Build graph (collapse M:N junctions to direct edges)
graph = GraphBuilder(collapse_many_to_many=True).build(db_schema)

# Render HTML
HtmlRenderer(title="Production DB").render(graph, "prod_erd.html")

# Or render SVG
GraphvizRenderer(fmt="svg").render(graph, "prod_erd.svg")
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

Tests requiring a Graphviz binary are automatically skipped when it is not installed.

---

## Project Structure

```
db-schema-visualizer/
├── db_schema_visualizer/
│   ├── __init__.py              # extract_schema(), render_schema()
│   ├── cli.py                   # Click CLI  (dbviz)
│   ├── config.py                # colours, fonts, layout constants
│   ├── model/schema.py          # Table, Column, Relationship, DatabaseSchema
│   ├── extractor/
│   │   ├── base.py              # AbstractExtractor
│   │   └── sqlalchemy_extractor.py
│   ├── graph/
│   │   ├── builder.py           # schema → graph dict
│   │   └── layout.py            # graph dict → DOT source
│   ├── renderer/
│   │   ├── graphviz_renderer.py # PNG / SVG / PDF
│   │   ├── html_renderer.py     # interactive HTML
│   │   └── templates/interactive.html
│   └── utils/filters.py         # table / schema filtering
├── tests/                       # pytest suite (56 tests)
├── examples/
│   ├── create_sample_db.py      # generates examples/sample.db
│   └── run_demo.py              # end-to-end demo
└── docs/
```

---

## License

MIT — see [LICENSE](LICENSE).
