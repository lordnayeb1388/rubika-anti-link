"""ربات ضدلینک روبیکا (کتابخانه Rubka)."""
import logging
import sys
import time

from rubka import Robot, Message

import antlink
import config
import database

log = logging.getLogger("antilink")

WARNING_COOLDOWN = 5          # ثانیه؛ جلوگیری از اسپم پیام هشدار
PERMISSION_NOTICE_COOLDOWN = 600  # ثانیه؛ هشدار نبود دسترسی حذف

_last_warning = {}
_last_permission_notice = {}
_group_cache = {}


def _retry(func, *args, attempts=3, delay=1.5, **kwargs):
    """چند بار تلاش مجدد برای خطاهای شبکه/قطع و وصل."""
    last = None
    for i in range(attempts):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last = exc
            log.warning("خطا در تماس با API (تلاش %d از %d): %s", i + 1, attempts, exc)
            if i < attempts - 1:
                time.sleep(delay)
    raise last


def _api_ok(resp):
    if isinstance(resp, dict):
        status = resp.get("status")
        return status is None or str(status).upper() == "OK"
    return resp is not False


def send_text(bot, chat_id, text):
    try:
        _retry(bot.send_message, chat_id=chat_id, text=text)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("ارسال پیام ناموفق بود: %s", exc)
        return False


def delete_message(bot, chat_id, message_id):
    try:
        resp = _retry(bot.delete_message, chat_id, message_id)
    except Exception as exc:  # noqa: BLE001
        log.error("حذف پیام ناموفق بود: %s", exc)
        return False
    if not _api_ok(resp):
        log.error("API حذف پیام را نپذیرفت: %s", resp)
        return False
    return True


def is_group(bot, chat_id):
    """شناسه گروه‌ها در روبیکا با g0 شروع می‌شود؛ در موارد نامشخص از get_chat کمک می‌گیریم."""
    cached = _group_cache.get(chat_id)
    if cached is not None:
        return cached
    if chat_id.startswith("g0"):
        result = True
    elif chat_id.startswith(("u0", "b0", "c0")):
        result = False
    else:
        try:
            info = _retry(bot.get_chat, chat_id)
            chat = (info.get("data") or {}).get("chat") or {}
            result = str(chat.get("chat_type", "")).lower() == "group"
        except Exception as exc:  # noqa: BLE001
            log.error("تشخیص نوع چت ممکن نشد: %s", exc)
            return False
    _group_cache[chat_id] = result
    return result


def run_admin_command(bot, chat_id, command):
    try:
        if command == "on":
            database.set_enabled(chat_id, True)
            send_text(bot, chat_id, "✅ ضدلینک برای این گروه روشن شد.")
        elif command == "off":
            database.set_enabled(chat_id, False)
            send_text(bot, chat_id, "🔓 ضدلینک برای این گروه خاموش شد.")
        elif command == "status":
            state = "روشن ✅" if database.is_enabled(chat_id) else "خاموش ❌"
            send_text(bot, chat_id, f"وضعیت ضدلینک: {state}")
    except Exception as exc:  # noqa: BLE001
        log.exception("خطا در ذخیره تنظیمات: %s", exc)
        send_text(bot, chat_id, "⚠️ خطا در ذخیره تنظیمات. دوباره تلاش کنید.")


def handle_link(bot, chat_id, message_id):
    now = time.monotonic()
    if delete_message(bot, chat_id, message_id):
        if now - _last_warning.get(chat_id, -1e9) >= WARNING_COOLDOWN:
            _last_warning[chat_id] = now
            send_text(bot, chat_id, config.WARNING_TEXT)
    elif now - _last_permission_notice.get(chat_id, -1e9) >= PERMISSION_NOTICE_COOLDOWN:
        # حذف فقط با دسترسی لازم ممکن است؛ در غیر این صورت مدیر را مطلع می‌کنیم
        _last_permission_notice[chat_id] = now
        send_text(bot, chat_id, config.PERMISSION_TEXT)


def handle_message(bot, message):
    chat_id = str(message.chat_id)
    sender_id = str(message.sender_id)
    text = getattr(message, "text", None)
    raw = getattr(message, "raw_data", None)
    command = antlink.parse_command(text)

    if command == "myid":
        send_text(bot, chat_id, f"🆔 شناسه شما:\n{sender_id}")
        return

    if not is_group(bot, chat_id):
        if command and sender_id in config.ADMIN_IDS:
            send_text(bot, chat_id, "این دستور فقط داخل گروه کار می‌کند.")
        return

    if command:
        # فقط مدیران مجاز؛ برای دیگران بی‌پاسخ می‌ماند
        if sender_id in config.ADMIN_IDS:
            run_admin_command(bot, chat_id, command)
        return

    if not database.is_enabled(chat_id):
        return
    if config.EXEMPT_ADMINS and sender_id in config.ADMIN_IDS:
        return
    if antlink.contains_link(text, raw):
        handle_link(bot, chat_id, str(message.message_id))


def build_bot():
    bot = Robot(token=config.BOT_TOKEN)

    @bot.on_message()
    def on_message(bot: Robot, message: Message):
        try:
            handle_message(bot, message)
        except Exception:  # noqa: BLE001
            log.exception("خطا در پردازش پیام")

    return bot


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    config.validate()
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    database.init_db()
    bot = build_bot()

    delay = 5
    try:
        while True:
            started = time.monotonic()
            try:
                log.info("ربات در حال اجراست... (برای توقف Ctrl+C)")
                bot.run()
                log.warning("اجرای ربات پایان یافت؛ تلاش برای اتصال مجدد...")
            except Exception:  # noqa: BLE001
                log.exception("اتصال قطع شد یا خطا رخ داد؛ تلاش مجدد...")
            if time.monotonic() - started > 60:
                delay = 5
            time.sleep(delay)
            delay = min(delay * 2, 60)
    except KeyboardInterrupt:
        log.info("ربات متوقف شد.")


if __name__ == "__main__":
    main()
