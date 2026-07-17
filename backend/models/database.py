import sqlite3
import os

SCHEMA = """
CREATE TABLE IF NOT EXISTS scenarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    bbox        TEXT,           -- JSON [south, west, north, east]
    graph_data  TEXT,           -- JSON serialised node/edge data
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def get_db(app):
    db_path = app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(app):
    db_path = app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"[DB] Initialised at {db_path}")
