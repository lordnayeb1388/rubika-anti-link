"""ذخیره تنظیمات هر گروه در SQLite (مستقل برای هر گروه)."""
from __future__ import annotations

import logging
import sqlite3
import threading
import time

import config

log = logging.getLogger("antilink.db")

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_cache: dict[str, bool] = {}


def init_db() -> None:
    """ساخت اتصال و جدول در صورت نبودن."""
    global _conn
    with _lock:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=10)
        _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id TEXT PRIMARY KEY,
                antilink_enabled INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        _conn.commit()
    log.info("دیتابیس آماده است: %s", config.DB_PATH)


def is_enabled(chat_id: str) -> bool:
    """آیا ضدلینک برای این گروه روشن است؟ (اگر تنظیمی نبود، مقدار پیش‌فرض)"""
    with _lock:
        if chat_id in _cache:
            return _cache[chat_id]
        if _conn is None:
            return config.DEFAULT_ENABLED
        row = _conn.execute(
            "SELECT antilink_enabled FROM group_settings WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        value = bool(row[0]) if row else config.DEFAULT_ENABLED
        _cache[chat_id] = value
        return value


def set_enabled(chat_id: str, enabled: bool) -> None:
    """روشن/خاموش کردن ضدلینک برای یک گروه."""
    with _lock:
        if _conn is None:
            raise RuntimeError("دیتابیس مقداردهی نشده است.")
        _conn.execute(
            "INSERT OR REPLACE INTO group_settings (chat_id, antilink_enabled, updated_at) "
            "VALUES (?, ?, ?)",
            (chat_id, int(enabled), int(time.time())),
        )
        _conn.commit()
        _cache[chat_id] = enabled
