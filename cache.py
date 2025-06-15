import sqlite3
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
import threading

DB_FILE = os.path.join(os.path.dirname(__file__), "cache.db")

# Thread pool for background revalidation
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache_revalidate")
_lock = threading.Lock()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    with conn:
        # Original search cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT NOT NULL,
                media_type TEXT NOT NULL,
                result_json TEXT NOT NULL,
                cached_at INTEGER NOT NULL,
                PRIMARY KEY (query, media_type)
            )
        """)
        
        # General cache table for movie details, images, actors, etc.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS general_cache (
                cache_key TEXT NOT NULL PRIMARY KEY,
                cache_type TEXT NOT NULL,
                result_json TEXT NOT NULL,
                cached_at INTEGER NOT NULL
            )
        """)
        
        # Stale-while-revalidate cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                data TEXT,
                timestamp INTEGER
            )
        """)
    conn.close()

def get_cached_result(query, media_type):
    """Get cached search result (backward compatibility)"""
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
    """Save cached search result (backward compatibility)"""
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

def get_cached_data(cache_key, cache_type):
    """Get cached data for any type (movie details, images, actors, etc.)"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT result_json FROM general_cache WHERE cache_key = ? AND cache_type = ?",
        (cache_key, cache_type),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        print(f"[CACHE] HIT: '{cache_key}' ({cache_type})", flush=True)
        return json.loads(row[0])
    else:
        print(f"[CACHE] MISS: '{cache_key}' ({cache_type})", flush=True)
        return None

def save_cached_data(cache_key, cache_type, data):
    """Save cached data for any type (movie details, images, actors, etc.)"""
    conn = sqlite3.connect(DB_FILE)
    with conn:
        conn.execute(
            """
            INSERT INTO general_cache (cache_key, cache_type, result_json, cached_at)
            VALUES (?, ?, ?, strftime('%s','now'))
            ON CONFLICT(cache_key) DO UPDATE SET
              cache_type=excluded.cache_type,
              result_json=excluded.result_json,
              cached_at=strftime('%s','now')
            """,
            (cache_key, cache_type, json.dumps(data)),
        )
    conn.close()
    print(f"[CACHE] SAVED: '{cache_key}' ({cache_type})", flush=True)

def get_stale_cache(key):
    """Get cached data for stale-while-revalidate pattern"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT data, timestamp FROM cache WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0]), row[1]
    return None, None

def save_stale_cache(key, data):
    """Save data to stale-while-revalidate cache"""
    current_time = int(time.time())
    
    with _lock:  # Prevent race conditions
        conn = sqlite3.connect(DB_FILE)
        with conn:
            conn.execute(
                """
                INSERT INTO cache (key, data, timestamp)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                  data=excluded.data,
                  timestamp=excluded.timestamp
                """,
                (key, json.dumps(data), current_time),
            )
        conn.close()
    
    print(f"[SWR CACHE] SAVED: '{key}' at {current_time}", flush=True)

def is_cache_fresh(timestamp, ttl_seconds):
    """Check if cache is still fresh based on TTL"""
    if timestamp is None:
        return False
    current_time = int(time.time())
    return (current_time - timestamp) < ttl_seconds

def revalidate_in_background(key, fetch_function):
    """Revalidate cache in background thread"""
    def _revalidate():
        try:
            print(f"[SWR CACHE] Background revalidation started for '{key}'", flush=True)
            new_data = fetch_function()
            if new_data:
                save_stale_cache(key, new_data)
                print(f"[SWR CACHE] Background revalidation completed for '{key}'", flush=True)
        except Exception as e:
            print(f"[SWR CACHE] Background revalidation failed for '{key}': {e}", flush=True)
    
    _executor.submit(_revalidate)

def get_with_stale_while_revalidate(key, ttl_seconds, fetch_function):
    """
    Implement stale-while-revalidate caching pattern
    
    Args:
        key: Cache key
        ttl_seconds: Time to live in seconds
        fetch_function: Function to fetch fresh data (should return JSON-serializable data)
    
    Returns:
        Tuple of (data, is_from_cache)
    """
    cached_data, timestamp = get_stale_cache(key)
    
    if cached_data is None:
        # No cache exists, fetch fresh data
        print(f"[SWR CACHE] MISS: '{key}' - fetching fresh data", flush=True)
        fresh_data = fetch_function()
        if fresh_data:
            save_stale_cache(key, fresh_data)
        return fresh_data, False
    
    if is_cache_fresh(timestamp, ttl_seconds):
        # Cache is fresh, return it
        print(f"[SWR CACHE] HIT (fresh): '{key}'", flush=True)
        return cached_data, True
    else:
        # Cache is stale, return it but trigger background revalidation
        print(f"[SWR CACHE] HIT (stale): '{key}' - triggering background revalidation", flush=True)
        revalidate_in_background(key, fetch_function)
        return cached_data, True
