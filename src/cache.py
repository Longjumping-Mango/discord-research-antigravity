"""
Discord Research Tool — SQLite Cache with Freshness Logic
Stores messages, channels, guilds and search results locally.
Checks for new messages before returning cached data.
"""

import hashlib
import json
import os
import sqlite3
import time
from typing import Optional

# Cache database location (next to the scripts)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discord_cache.db")

# TTL in seconds
TTL_GUILDS = 3600        # 1 hour
TTL_CHANNELS = 3600      # 1 hour
TTL_SEARCH = 900         # 15 min
TTL_MESSAGES = 0         # Always check for new (freshness logic)


def _get_db() -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    _create_tables(db)
    return db


def _create_tables(db: sqlite3.Connection):
    """Create cache tables if they don't exist."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS guilds (
            id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            fetched_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS channels (
            guild_id TEXT NOT NULL,
            data_json TEXT NOT NULL,
            fetched_at REAL NOT NULL,
            PRIMARY KEY (guild_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            timestamp TEXT,
            data_json TEXT NOT NULL,
            fetched_at REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id);
        CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id, id);

        CREATE TABLE IF NOT EXISTS channel_meta (
            channel_id TEXT PRIMARY KEY,
            latest_cached_id TEXT,
            message_count INTEGER DEFAULT 0,
            last_fetched_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS search_cache (
            query_hash TEXT PRIMARY KEY,
            guild_id TEXT,
            channel_id TEXT,
            results_json TEXT NOT NULL,
            fetched_at REAL NOT NULL
        );
    """)
    db.commit()


# ── Guild cache ──

def get_cached_guilds() -> Optional[list[dict]]:
    """Get cached guild list if still fresh."""
    db = _get_db()
    try:
        rows = db.execute("SELECT data_json, fetched_at FROM guilds LIMIT 1").fetchone()
        if rows and (time.time() - rows["fetched_at"]) < TTL_GUILDS:
            return json.loads(rows["data_json"])
        return None
    finally:
        db.close()


def cache_guilds(guilds: list[dict]):
    """Cache guild list."""
    db = _get_db()
    try:
        data = json.dumps(guilds, ensure_ascii=False)
        db.execute(
            "INSERT OR REPLACE INTO guilds (id, data_json, fetched_at) VALUES (?, ?, ?)",
            ("all", data, time.time())
        )
        db.commit()
    finally:
        db.close()


# ── Channel cache ──

def get_cached_channels(guild_id: str) -> Optional[list[dict]]:
    """Get cached channel list if still fresh."""
    db = _get_db()
    try:
        row = db.execute(
            "SELECT data_json, fetched_at FROM channels WHERE guild_id = ?", (guild_id,)
        ).fetchone()
        if row and (time.time() - row["fetched_at"]) < TTL_CHANNELS:
            return json.loads(row["data_json"])
        return None
    finally:
        db.close()


def cache_channels(guild_id: str, channels: list[dict]):
    """Cache channel list."""
    db = _get_db()
    try:
        data = json.dumps(channels, ensure_ascii=False)
        db.execute(
            "INSERT OR REPLACE INTO channels (guild_id, data_json, fetched_at) VALUES (?, ?, ?)",
            (guild_id, data, time.time())
        )
        db.commit()
    finally:
        db.close()


# ── Message cache with freshness ──

def get_cached_messages(channel_id: str, limit: int) -> tuple[list[dict], Optional[str]]:
    """
    Get cached messages for a channel.
    Returns (messages, latest_cached_id).
    latest_cached_id is used to check for new messages.
    """
    db = _get_db()
    try:
        # Get channel meta
        meta = db.execute(
            "SELECT latest_cached_id, message_count FROM channel_meta WHERE channel_id = ?",
            (channel_id,)
        ).fetchone()

        if not meta:
            return [], None

        latest_cached_id = meta["latest_cached_id"]

        # Get cached messages (newest first by ID, then reverse for chronological)
        rows = db.execute(
            "SELECT data_json FROM messages WHERE channel_id = ? ORDER BY id DESC LIMIT ?",
            (channel_id, limit)
        ).fetchall()

        messages = [json.loads(row["data_json"]) for row in rows]
        messages.reverse()  # Chronological order

        return messages, latest_cached_id
    finally:
        db.close()


def cache_messages(channel_id: str, messages: list[dict]):
    """Cache messages and update channel meta."""
    if not messages:
        return

    db = _get_db()
    try:
        for msg in messages:
            msg_id = msg.get("id")
            if not msg_id:
                continue
            db.execute(
                "INSERT OR REPLACE INTO messages (id, channel_id, timestamp, data_json, fetched_at) VALUES (?, ?, ?, ?, ?)",
                (msg_id, channel_id, msg.get("timestamp", ""), json.dumps(msg, ensure_ascii=False), time.time())
            )

        # Update channel meta with the latest message ID
        latest_id = max(messages, key=lambda m: int(m.get("id", "0"))).get("id")
        msg_count = db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE channel_id = ?", (channel_id,)
        ).fetchone()["cnt"]

        db.execute(
            "INSERT OR REPLACE INTO channel_meta (channel_id, latest_cached_id, message_count, last_fetched_at) VALUES (?, ?, ?, ?)",
            (channel_id, latest_id, msg_count, time.time())
        )
        db.commit()
    finally:
        db.close()


# ── Search cache ──

def _search_hash(guild_id: str, channel_id: str, query: str, **filters) -> str:
    """Generate a hash for a search query."""
    key = f"{guild_id}:{channel_id}:{query}:{json.dumps(filters, sort_keys=True)}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def get_cached_search(guild_id: str = "", channel_id: str = "",
                      query: str = "", **filters) -> Optional[list[dict]]:
    """Get cached search results if still fresh."""
    qhash = _search_hash(guild_id, channel_id, query, **filters)
    db = _get_db()
    try:
        row = db.execute(
            "SELECT results_json, fetched_at FROM search_cache WHERE query_hash = ?",
            (qhash,)
        ).fetchone()
        if row and (time.time() - row["fetched_at"]) < TTL_SEARCH:
            return json.loads(row["results_json"])
        return None
    finally:
        db.close()


def cache_search(guild_id: str = "", channel_id: str = "",
                 query: str = "", results: list[dict] = None, **filters):
    """Cache search results."""
    if results is None:
        return
    qhash = _search_hash(guild_id, channel_id, query, **filters)
    db = _get_db()
    try:
        db.execute(
            "INSERT OR REPLACE INTO search_cache (query_hash, guild_id, channel_id, results_json, fetched_at) VALUES (?, ?, ?, ?, ?)",
            (qhash, guild_id, channel_id, json.dumps(results, ensure_ascii=False), time.time())
        )
        db.commit()
    finally:
        db.close()


# ── Cache stats ──

def get_cache_stats() -> dict:
    """Get cache statistics."""
    if not os.path.exists(DB_PATH):
        return {"exists": False}

    db = _get_db()
    try:
        msg_count = db.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()["cnt"]
        channel_count = db.execute("SELECT COUNT(*) as cnt FROM channel_meta").fetchone()["cnt"]
        search_count = db.execute("SELECT COUNT(*) as cnt FROM search_cache").fetchone()["cnt"]
        db_size = os.path.getsize(DB_PATH)

        return {
            "exists": True,
            "messages_cached": msg_count,
            "channels_tracked": channel_count,
            "search_queries_cached": search_count,
            "db_size_bytes": db_size,
        }
    finally:
        db.close()
