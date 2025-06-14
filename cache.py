import sqlite3
import json
import time
import os

CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "cache.db")
CACHE_EXPIRATION_SECONDS = 60 * 60  # 1 hour

def get_db():
    return sqlite3.connect(CACHE_DB_PATH)

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT NOT NULL,
                media_type TEXT NOT NULL,
                result_json TEXT NOT NULL,
                cached_at INTEGER NOT NULL,
                UNIQUE(query, media_type)
            )
        ''')

def get_cached_result(query, media_type):
    key = query.lower().strip()
    with get_db() as conn:
        row = conn.execute('''
            SELECT result_json, cached_at FROM search_cache
            WHERE query = ? AND media_type = ?
        ''', (key, media_type)).fetchone()

        if row:
            result_json, cached_at = row
            if time.time() - cached_at < CACHE_EXPIRATION_SECONDS:
                return json.loads(result_json)
    return None

def save_cached_result(query, media_type, data):
    key = query.lower().strip()
    with get_db() as conn:
        conn.execute('''
            INSERT INTO search_cache (query, media_type, result_json, cached_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(query, media_type)
            DO UPDATE SET result_json=excluded.result_json,
                          cached_at=excluded.cached_at
        ''', (key, media_type, json.dumps(data), int(time.time())))
