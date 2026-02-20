"""Telegram notification module for signal alerts and system errors."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications to a Telegram chat via Bot API."""

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        signal_log_path: Optional[Path] = None,
    ) -> None:
        self.token = token
        self.chat_id = chat_id
        self.signal_log_path = signal_log_path
        self.enabled = bool(token and chat_id)

        if self.enabled:
            logger.info("Telegram notifier ENABLED (token: tg:***, chat_id: %s)", self.chat_id)
        else:
            logger.info("Telegram notifier DISABLED (missing token or chat_id)")

    def _send(self, text: str) -> None:
        """Helper to post message to Telegram API."""
        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            # Security: Ensure url starts with https
            if not url.startswith("https://"):
                raise ValueError("Insecure Telegram API URL")

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            # Non-blocking: log error but don't crash
            logger.error("Failed to send Telegram notification: %s", e)
            if self.signal_log_path:
                self._log_failure(str(e))

    def _log_failure(self, error: str) -> None:
        """Append Telegram failure to signal_log.jsonl."""
        try:
            self.signal_log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "telegram_failure",
                "error": error,
            }
            with open(self.signal_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            logger.debug("Could not write telegram failure to signal_log", exc_info=True)

    def send_signal(self, pair: str, direction: str, entry: float, sl: float, tp: float, mode: str) -> None:
        """Send formatted signal alert."""
        icon = "🟢" if direction.lower() == "long" else "🔴"
        title = f"{icon} <b>{pair} {direction.upper()}</b>"
        
        msg = (
            f"{title}\n"
            f"📈 Entry: {entry:.5f}\n"
            f"🛡 SL: {sl:.5f}\n"
            f"🎯 TP: {tp:.5f}\n"
            f"📋 Mode: {mode.upper()}"
        )
        self._send(msg)

    def send_startup(self, validated_pairs: list[str], mode: str = "PAPER") -> None:
        """Send startup notification."""
        pairs_str = ", ".join(validated_pairs) if validated_pairs else "None"
        msg = (
            f"🚀 <b>BB Strategy Started</b>\n"
            f"Validated pairs: {pairs_str}\n"
            f"Mode: {mode.upper()}"
        )
        self._send(msg)

    def send_error(self, message: str) -> None:
        """Send urgent error notification."""
        msg = f"⚠️ <b>BB Strategy Error</b>\n{message}"
        self._send(msg)
