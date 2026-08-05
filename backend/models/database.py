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

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'planner' CHECK(role IN ('admin', 'planner')),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS traffic_profiles (
    highway_type TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL   -- JSON array of 24 floats, hourly baseline congestion
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
