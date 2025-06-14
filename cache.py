import sqlite3
import json
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "cache.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT NOT NULL,
                media_type TEXT NOT NULL,
                result_json TEXT NOT NULL,
                cached_at INTEGER NOT NULL,
                PRIMARY KEY (query, media_type)
            )
        """)
    conn.close()

def get_cached_result(query, media_type):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT result_json FROM search_cache WHERE query = ? AND media_type = ?",
        (query, media_type),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        print(f"[CACHE] HIT: '{query}' ({media_type})", flush=True)
        return json.loads(row[0])
    else:
        print(f"[CACHE] MISS: '{query}' ({media_type})", flush=True)
        return None

def save_cached_result(query, media_type, data):
    conn = sqlite3.connect(DB_FILE)
    with conn:
        conn.execute(
            """
            INSERT INTO search_cache (query, media_type, result_json, cached_at)
            VALUES (?, ?, ?, strftime('%s','now'))
            ON CONFLICT(query, media_type) DO UPDATE SET
              result_json=excluded.result_json,
              cached_at=strftime('%s','now')
            """,
            (query, media_type, json.dumps(data)),
        )
    conn.close()
