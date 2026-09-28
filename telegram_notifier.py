"""
Telegram notifier — sends accepted trading signals to a Telegram group.

This module is intentionally separate from the strategy engine so the
WaveRider/BB Squeeze/MACD logic is unchanged.

Configure:
  TELEGRAM_BOT_TOKEN=<your current BotFather token>
  TELEGRAM_CHAT_ID=-5559692993
  TELEGRAM_ENABLED=true
"""
import json
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-5559692993").strip()


def _escape_html(value) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def send_signal(signal, *, risk_reason: str = "allowed") -> bool:
    """Send a signal to Telegram without changing trading behavior.

    Errors are swallowed after logging, so Telegram outages can never block
    or modify the trading strategy/execution path.
    """
    if not TELEGRAM_ENABLED:
        return False

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram notifier disabled: token/chat ID is missing")
        return False

    direction = str(getattr(signal, "direction", "")).lower()
    emoji = "🟢" if direction == "long" else "🔴"

    pair = _escape_html(getattr(signal, "pair", "UNKNOWN"))
    direction_text = _escape_html(direction.upper())
    source = _escape_html(getattr(signal, "source", "unknown"))
    entry = getattr(signal, "entry_price", None)
    sl = getattr(signal, "sl_price", None)
    tp1 = getattr(signal, "tp1_price", None)
    tp2 = getattr(signal, "tp2_price", None)
    tp3 = getattr(signal, "tp3_price", None)
    confidence = getattr(signal, "confidence", None)
    ai_verdict = getattr(signal, "ai_verdict", None)
    ai_confidence = getattr(signal, "ai_confidence", None)
    ensemble_score = getattr(signal, "ensemble_score", None)

    def fmt(value):
        if value is None:
            return "—"
        try:
            return f"{float(value):.8g}"
        except (TypeError, ValueError):
            return _escape_html(value)

    lines = [
        f"{emoji} <b>{pair} {direction_text}</b>",
        "",
        f"<b>Entry:</b> {fmt(entry)}",
        f"<b>SL:</b> {fmt(sl)}",
        f"<b>TP1:</b> {fmt(tp1)}",
        f"<b>TP2:</b> {fmt(tp2)}",
        f"<b>TP3:</b> {fmt(tp3)}",
        "",
        f"<b>Strategy:</b> {source}",
        f"<b>RSI/confidence:</b> {fmt(confidence)}",
    ]

    if ai_verdict is not None:
        lines.append(f"<b>AI verdict:</b> {_escape_html(ai_verdict)}")
    if ai_confidence is not None:
        lines.append(f"<b>AI confidence:</b> {fmt(ai_confidence)}")
    if ensemble_score is not None:
        lines.append(f"<b>Ensemble:</b> {fmt(ensemble_score)}")

    lines.extend([
        "",
        "⚠️ Signal passed the existing strategy/risk path.",
        "Mode: paper trading unless your deployment changes the executor.",
    ])

    message = "\n".join(lines)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    try:
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            logger.error("Telegram API rejected message: %s", result)
            return False
        logger.info("Telegram signal sent for %s %s", pair, direction_text)
        return True
    except Exception as exc:
        # Never let Telegram failure alter the trading logic.
        logger.error("Telegram send failed: %s", exc)
        return False
