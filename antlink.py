"""تشخیص لینک و تفسیر دستورهای فارسی (بدون وابستگی به Rubka)."""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

import config

# کاراکترهای نامرئی که برای فرار از تشخیص وسط لینک گذاشته می‌شوند (نیم‌فاصله، ZWSP، ...)
_INVISIBLE = dict.fromkeys(
    map(ord, "\u200b\u200c\u200d\u200e\u200f\u2060\ufeff\u202a\u202b\u202c\u202d\u202e"),
    None,
)

# http:// ، https:// و www. (حتی اگر بدون فاصله به متن چسبیده باشند)
_SCHEME_RE = re.compile(r"(?:https?://|www\.)\S", re.IGNORECASE)

# دامنه بدون پیشوند، مثل example.com یا rubika.ir/join (ایمیل‌ها را لینک حساب نمی‌کند)
_TLDS = (
    "com|net|org|ir|io|me|co|info|xyz|ly|gl|app|dev|link|site|online|top|tv|cc|ru|biz|store|shop"
)
_DOMAIN_RE = re.compile(
    r"(?<![A-Za-z0-9@._-])"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"(?:" + _TLDS + r")"
    r"(?![A-Za-z0-9-])",
    re.IGNORECASE,
)

# دستورها بعد از حذف فاصله‌ها مقایسه می‌شوند
_COMMANDS = {
    "ضدلینکروشن": "on",
    "ضدلینکخاموش": "off",
    "وضعیتضدلینک": "status",
    "شناسهمن": "myid",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return text.translate(_INVISIBLE)


def _has_link_entity(data: Any, depth: int = 0) -> bool:
    """لینک‌های مخفی پشت متن (hyperlink) را از metadata پیام پیدا می‌کند (در حد توان)."""
    if depth > 6:
        return False
    if isinstance(data, dict):
        meta = data.get("metadata")
        if isinstance(meta, dict):
            for part in meta.get("meta_data_parts") or []:
                if isinstance(part, dict) and (
                    part.get("type") == "Link" or part.get("link_url")
                ):
                    return True
        return any(
            _has_link_entity(v, depth + 1)
            for v in data.values()
            if isinstance(v, (dict, list))
        )
    if isinstance(data, list):
        return any(
            _has_link_entity(v, depth + 1) for v in data if isinstance(v, (dict, list))
        )
    return False


def contains_link(text: Optional[str], raw_data: Any = None) -> bool:
    """آیا پیام شامل لینک است؟"""
    if text:
        clean = normalize(text)
        if _SCHEME_RE.search(clean):
            return True
        if config.BLOCK_BARE_DOMAINS and _DOMAIN_RE.search(clean):
            return True
    return _has_link_entity(raw_data)


def parse_command(text: Optional[str]) -> Optional[str]:
    """خروجی: on / off / status / myid یا None اگر دستور نبود."""
    if not text:
        return None
    t = normalize(text).replace("ي", "ی").replace("ك", "ک")
    t = re.sub(r"\s+", "", t).strip(".!؟?،")
    return _COMMANDS.get(t)
