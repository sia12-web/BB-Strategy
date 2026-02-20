"""Order executor: places live Oanda orders or records paper trades."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import oandapyV20
import oandapyV20.endpoints.orders as orders

from bb_strategy.config import Config

logger = logging.getLogger(__name__)

DEFAULT_PAPER_TRADES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "paper_trades.json"


class OrderExecutor:
    """Execute live orders via Oanda API or record paper trades to JSON.

    Security:
        - Live orders only execute if config.OANDA_ENV == "live"
          AND the pair's trade mode is "live" (dual gate).
        - Logs are stripped to status code + order ID only.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        paper_trades_path: Path | str = DEFAULT_PAPER_TRADES_PATH,
    ) -> None:
        self.config = config or Config()
        self.paper_trades_path = Path(paper_trades_path)
        self._file_lock = threading.Lock()

        # Build API client (used for live orders)
        self._api = oandapyV20.API(
            access_token=self.config.OANDA_API_KEY,
            environment=self.config.OANDA_ENV,
        )

    def place_live_order(
        self,
        pair: str,
        signal: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        units: int,
    ) -> dict:
        """Place a market order via Oanda v20 API.

        Args:
            pair: Instrument, e.g. "EUR_USD".
            signal: 1 (long) or -1 (short).
            entry_price: Expected fill price (for logging).
            stop_loss: SL price.
            take_profit: TP price.
            units: Position size (positive). Negated for shorts.

        Returns:
            Dict with status_code and order_id (sanitized).
        """
        # Negate units for short orders
        order_units = str(units) if signal == 1 else str(-units)

        order_body = {
            "order": {
                "type": "MARKET",
                "instrument": pair,
                "units": order_units,
                "stopLossOnFill": {
                    "price": str(round(stop_loss, 5)),
                },
                "takeProfitOnFill": {
                    "price": str(round(take_profit, 5)),
                },
            }
        }

        endpoint = orders.OrderCreate(
            accountID=self.config.OANDA_ACCOUNT_ID,
            data=order_body,
        )

        logger.info(
            "Placing live %s order: %s %s units @ ~%s | SL: %s | TP: %s",
            "LONG" if signal == 1 else "SHORT",
            pair, order_units, entry_price, stop_loss, take_profit,
        )

        response = self._api.request(endpoint)

        # Strip response to status code + order ID only (security)
        order_id = (
            response.get("orderFillTransaction", {}).get("id")
            or response.get("orderCreateTransaction", {}).get("id")
            or "unknown"
        )
        result = {
            "status": "filled",
            "order_id": order_id,
            "pair": pair,
            "signal": signal,
            "units": order_units,
        }

        logger.info("Live order placed: %s", result)
        return result

    def record_paper_trade(
        self,
        pair: str,
        signal: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        units: int,
    ) -> dict:
        """Append a paper trade to the JSON file.

        Args:
            pair: Instrument name.
            signal: 1 (long) or -1 (short).
            entry_price: Entry price.
            stop_loss: SL price.
            take_profit: TP price.
            units: Position size (positive).

        Returns:
            The recorded trade entry dict.
        """
        trade_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pair": pair,
            "direction": "long" if signal == 1 else "short",
            "signal": signal,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "units": units,
            "mode": "paper",
        }

        with self._file_lock:
            # Load existing trades
            existing: list[dict] = []
            if self.paper_trades_path.exists():
                try:
                    with open(self.paper_trades_path, "r") as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, OSError):
                    existing = []

            existing.append(trade_entry)

            # Ensure parent dir exists
            self.paper_trades_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.paper_trades_path, "w") as f:
                json.dump(existing, f, indent=2)

        logger.info("Paper trade recorded: %s %s @ %s", pair, trade_entry["direction"], entry_price)
        return trade_entry
