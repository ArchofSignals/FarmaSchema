"""
database.py
------------
Very small SQLite helper for one job: letting a farmer bookmark schemes so
they can find them again later.

We deliberately do NOT ask for name, phone number, Aadhaar, or any other
personal identifier (see the SECURITY / PRIVACY section of the project
brief). Instead, the frontend generates a random "client_id" the first time
someone visits (stored only in their browser's localStorage) and sends it
with bookmark requests. This lets bookmarks be private to that browser
without collecting any personal information.
"""

import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "data", "farmaschema.db")


def get_connection():
    """Open a connection to the SQLite database file."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Create the bookmarks table if it does not already exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            scheme_id TEXT NOT NULL,
            scheme_name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(client_id, scheme_id)
        )
    """)
    conn.commit()
    conn.close()


def add_bookmark(client_id, scheme_id, scheme_name):
    """Save a bookmark. Does nothing if it already exists (no duplicates)."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO bookmarks (client_id, scheme_id, scheme_name) VALUES (?, ?, ?)",
        (client_id, scheme_id, scheme_name),
    )
    conn.commit()
    conn.close()


def remove_bookmark(client_id, scheme_id):
    """Delete a bookmark for a given client and scheme."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM bookmarks WHERE client_id = ? AND scheme_id = ?",
        (client_id, scheme_id),
    )
    conn.commit()
    conn.close()


def get_bookmarks(client_id):
    """Return all bookmarks saved by a given client, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT scheme_id, scheme_name, created_at FROM bookmarks WHERE client_id = ? ORDER BY created_at DESC",
        (client_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
