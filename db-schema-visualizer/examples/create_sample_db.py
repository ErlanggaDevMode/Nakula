"""
Script to create a sample SQLite database at examples/sample.db.

Schema overview:
  users ──< orders ──< order_items >── products
  tags  ──< product_tags >── products   (pure M:N junction)

Run with:
    python examples/create_sample_db.py
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "sample.db")


def create_sample_db(path: str = DB_PATH) -> None:
    """Create the sample database with 5 tables and some seed data."""
    if os.path.exists(path):
        os.remove(path)

    conn = sqlite3.connect(path)
    cur = conn.cursor()

    # ------------------------------------------------------------------ tables
    cur.executescript(
        """
        CREATE TABLE users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    NOT NULL UNIQUE,
            email      TEXT    NOT NULL UNIQUE,
            created_at TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT,
            price       REAL    NOT NULL DEFAULT 0.0,
            stock       INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE orders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            status     TEXT    NOT NULL DEFAULT 'pending',
            created_at TEXT    DEFAULT (datetime('now')),
            total      REAL    DEFAULT 0.0
        );

        CREATE TABLE order_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity   INTEGER NOT NULL DEFAULT 1,
            unit_price REAL    NOT NULL
        );

        CREATE TABLE tags (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        -- Pure M:N junction: composite PK = (product_id, tag_id)
        CREATE TABLE product_tags (
            product_id INTEGER NOT NULL REFERENCES products(id),
            tag_id     INTEGER NOT NULL REFERENCES tags(id),
            PRIMARY KEY (product_id, tag_id)
        );
        """
    )

    # ------------------------------------------------------------------ seed data
    cur.executescript(
        """
        INSERT INTO users (username, email) VALUES
            ('alice',   'alice@example.com'),
            ('bob',     'bob@example.com'),
            ('charlie', 'charlie@example.com');

        INSERT INTO products (name, price, stock) VALUES
            ('Laptop',      999.99, 10),
            ('Mouse',        19.99, 50),
            ('Keyboard',     49.99, 30),
            ('Monitor',     299.99,  8);

        INSERT INTO orders (user_id, status, total) VALUES
            (1, 'completed', 1019.98),
            (1, 'pending',     49.99),
            (2, 'completed',   19.99);

        INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
            (1, 1, 1, 999.99),
            (1, 2, 1,  19.99),
            (2, 3, 1,  49.99),
            (3, 2, 1,  19.99);

        INSERT INTO tags (name) VALUES
            ('electronics'), ('computing'), ('peripherals'), ('display');

        INSERT INTO product_tags (product_id, tag_id) VALUES
            (1, 1), (1, 2),
            (2, 1), (2, 3),
            (3, 1), (3, 3),
            (4, 1), (4, 4);
        """
    )

    conn.commit()
    conn.close()
    print(f"Sample database created at: {path}")


if __name__ == "__main__":
    create_sample_db()
