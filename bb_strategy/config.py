"""Configuration for the Bollinger Band strategy pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    """Central configuration loaded from environment variables."""

    OANDA_API_KEY: str = field(default_factory=lambda: os.getenv("OANDA_API_KEY", ""))
    OANDA_ACCOUNT_ID: str = field(default_factory=lambda: os.getenv("OANDA_ACCOUNT_ID", ""))
    OANDA_ENV: str = field(default_factory=lambda: os.getenv("OANDA_ENV", "practice"))

    TELEGRAM_BOT_TOKEN: Optional[str] = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN"))
    TELEGRAM_CHAT_ID: Optional[str] = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID"))

    PAIRS: list[str] = field(
        default_factory=lambda: ["EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]
    )
    TIMEFRAMES: list[str] = field(default_factory=lambda: ["M15", "H1"])

    DATA_DIR: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "data"
    )

    @property
    def api_url(self) -> str:
        """Return the correct Oanda API base URL based on environment."""
        if self.OANDA_ENV == "live":
            return "https://api-fxtrade.oanda.com"
        return "https://api-fxpractice.oanda.com"

    def validate(self) -> None:
        """Raise if required credentials are missing."""
        if not self.OANDA_API_KEY:
            raise ValueError("OANDA_API_KEY is not set. Check your .env file.")
        if not self.OANDA_ACCOUNT_ID:
            raise ValueError("OANDA_ACCOUNT_ID is not set. Check your .env file.")
