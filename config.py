"""تنظیمات پروژه. همه مقادیر حساس فقط از فایل .env خوانده می‌شوند."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


# توکن ربات (از @BotFather در روبیکا) - فقط از .env
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

# شناسه (GUID) مدیران مجاز، با کاما جدا شوند. مثال: u0AAAA,u0BBBB
ADMIN_IDS: set[str] = {
    item.strip() for item in os.getenv("ADMIN_IDS", "").split(",") if item.strip()
}

# مسیر فایل دیتابیس SQLite
_db = os.getenv("DB_PATH", "antilink.db").strip() or "antilink.db"
DB_PATH: str = str(Path(_db) if Path(_db).is_absolute() else BASE_DIR / _db)

# وضعیت پیش‌فرض ضدلینک برای گروه‌هایی که هنوز تنظیم نشده‌اند
DEFAULT_ENABLED: bool = _env_bool("DEFAULT_ENABLED", True)

# اگر روشن باشد، پیام مدیران (ADMIN_IDS) حتی با لینک حذف نمی‌شود
EXEMPT_ADMINS: bool = _env_bool("EXEMPT_ADMINS", True)

# تشخیص آدرس‌های بدون http/www مثل example.com یا rubika.ir/xxx
BLOCK_BARE_DOMAINS: bool = _env_bool("BLOCK_BARE_DOMAINS", True)

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"

WARNING_TEXT = "⚠️ ارسال لینک در این گروه مجاز نیست."
PERMISSION_TEXT = (
    "⚠️ نتوانستم پیام دارای لینک را حذف کنم.\n"
    "لطفاً ربات را مدیر گروه کنید و دسترسی «حذف پیام» را به آن بدهید."
)


def validate() -> None:
    """قبل از اجرا فراخوانی می‌شود؛ در صورت نبود توکن برنامه را با پیام واضح می‌بندد."""
    if not BOT_TOKEN:
        raise SystemExit(
            "خطا: BOT_TOKEN پیدا نشد.\n"
            "فایل .env.example را به .env کپی کنید و توکن ربات را در آن بنویسید."
        )
    if not ADMIN_IDS:
        print(
            "هشدار: ADMIN_IDS خالی است؛ هیچ‌کس نمی‌تواند ربات را روشن/خاموش کند.\n"
            "در یک چت با ربات بنویسید «شناسه من» و شناسه را در .env قرار دهید."
        )
